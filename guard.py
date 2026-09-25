#!/usr/bin/env python3
"""Macmini4,1 diagnostics and supervised thermal/load fan workaround.

No direct SMC-port access, fault clearing, firmware changes, or boot installation.
Temperature limits below are conservative experiment cutoffs, not Apple ratings.
"""
import argparse
from collections import deque
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import socket
import sys
import time


# Deliberately exclude undocumented, constant *G channels from live-temperature
# decisions. Preserve them in snapshots. Require every listed physical channel.
LIMITS = {
    'TA0P': 38, 'TC0D': 60, 'TC0H': 50, 'TC0P': 50, 'TC0p': 50,
    'TH0P': 42, 'TH0p': 42, 'TM0P': 50, 'TM0p': 50,
    'TN0D': 55, 'TN0P': 48, 'TN0p': 48,
    'TN1D': 60, 'TN1E': 60, 'TN1F': 60, 'TN1S': 60,
    'TO0P': 42, 'TO0p': 42, 'TW0P': 48, 'Tm0P': 45, 'Tp0C': 60,
}


class Unsafe(RuntimeError):
    pass


class StopRequested(RuntimeError):
    pass


def emit(event, **data):
    print(json.dumps({'event': event, 'time': time.time(), **data}), flush=True)


class Hardware:
    def __init__(self):
        model = Path('/sys/class/dmi/id/product_name').read_text().strip()
        if model != 'Macmini4,1':
            raise Unsafe(f'Unsupported model: {model}')
        matches = list(Path('/sys/devices/platform').glob('applesmc.*/fan1_input'))
        if len(matches) != 1:
            raise Unsafe('Expected one Apple SMC fan')
        self.smc = matches[0].parent
        if (self.smc / 'fan2_input').exists():
            raise Unsafe('Unexpected second fan')
        self.labels = {}
        for f in self.smc.glob('temp*_label'):
            label = f.read_text().strip()
            self.labels[label] = f.with_name(f.name.replace('_label', '_input'))
        self.independent = {}
        for directory in Path('/sys/class/hwmon').glob('hwmon*'):
            try:
                name = (directory / 'name').read_text().strip()
            except FileNotFoundError:
                continue
            if name in ('coretemp', 'nouveau'):
                for f in sorted(directory.glob('temp*_input')):
                    self.independent[f'{name}/{f.name}'] = f
        if sum(k.startswith('coretemp/') for k in self.independent) != 2:
            raise Unsafe('Both independent CPU sensors are required')
        if sum(k.startswith('nouveau/') for k in self.independent) != 1:
            raise Unsafe('Independent GPU sensor is required')

    def read(self, name):
        return int((self.smc / name).read_text().strip())

    def write(self, name, value):
        (self.smc / name).write_text(str(value))

    def snapshot(self):
        return {
            'temps': {k: int(p.read_text()) / 1000 for k, p in self.labels.items()},
            'independent': {k: int(p.read_text()) / 1000 for k, p in self.independent.items()},
            'rpm': self.read('fan1_input'), 'target': self.read('fan1_output'),
            'manual': self.read('fan1_manual'), 'minimum': self.read('fan1_min'),
            'maximum': self.read('fan1_max'),
        }

    def faults(self):
        # Only the Linux driver's read-index selector is written. No SMC key
        # data is changed. Restore selector, and verify the selected key.
        selector = self.smc / 'key_at_index'
        previous = selector.read_text()
        expected = {114: 'MSSF', 144: 'SBF', 171: 'SPHR', 172: 'SPHS'}
        result = {}
        try:
            for index, name in expected.items():
                selector.write_text(str(index))
                if (self.smc / 'key_at_index_name').read_text().strip() != name:
                    raise Unsafe('Unexpected SMC key layout')
                raw = (self.smc / 'key_at_index_data').read_bytes()
                if len(raw) != (1 if name == 'SPHS' else 4):
                    raise Unsafe(f'Unexpected data length: {name}')
                if (self.smc / 'key_at_index_name').read_text().strip() != name:
                    raise Unsafe('Concurrent SMC diagnostic changed read selector')
                result[name] = int.from_bytes(raw, 'big')
        finally:
            selector.write_text(previous)
        return result


def check(snapshot, baseline=None, enforce_cutoffs=True):
    if snapshot['maximum'] != 5500 or snapshot['minimum'] != 1800:
        raise Unsafe('Unexpected fan limits')
    for label, limit in LIMITS.items():
        value = snapshot['temps'].get(label)
        upper = limit if enforce_cutoffs else 110
        if value is None or not math.isfinite(value) or not 10 <= value < upper:
            raise Unsafe(f'{label}: missing/invalid/at cutoff ({value}, cutoff {limit})')
        rise_limit = 12 if label == 'TC0D' else (8 if label in {'TN0D','TN1D','TN1E','TN1F','TN1S'} else 4)
        if baseline and value - baseline['temps'][label] >= rise_limit:
            raise Unsafe(f'{label}: temperature rose from {baseline["temps"][label]} to {value} C (rise cutoff {rise_limit})')
    if len(snapshot['independent']) != 3:
        raise Unsafe('Missing independent sensors')
    for label, value in snapshot['independent'].items():
        if not math.isfinite(value) or not 10 <= value < (60 if enforce_cutoffs else 110):
            raise Unsafe(f'{label}: invalid/at 60 C cutoff ({value})')
        rise_limit = 12 if label.startswith('coretemp/') else 8
        if baseline and value - baseline['independent'][label] >= rise_limit:
            raise Unsafe(f'{label}: excessive temperature rise ({value} C)')
    if not (2750 if snapshot['manual'] else 1500) <= snapshot['rpm'] <= 5800:
        raise Unsafe(f"Fan speed outside experiment range: {snapshot['rpm']}")


def restore():
    # Separate, minimal path: restoring fan control must not depend on sensors.
    paths = list(Path('/sys/devices/platform').glob('applesmc.*/fan1_manual'))
    if len(paths) != 1:
        raise Unsafe('Cannot locate fan for restoration')
    p = paths[0].parent
    errors = []
    for name, value in [('fan1_output', 5500), ('fan1_manual', 0)]:
        try:
            (p / name).write_text(str(value))
        except OSError as exc:
            errors.append(f'{name}: {exc}')
    if (p / 'fan1_manual').read_text().strip() != '0':
        errors.append('Automatic mode readback failed')
    emit('restored', manual=(p / 'fan1_manual').read_text().strip(), errors=errors)
    if errors:
        raise Unsafe('; '.join(errors))


class CpuCooling:
    """Stepped load anticipation with a five-percentage-point release gap."""
    thresholds = (35, 50, 70, 75)
    speeds = (3000, 3500, 3900, 4300, 4800)

    def __init__(self):
        self.step = 0

    def request(self, cpu, minimum):
        if not math.isfinite(cpu) or not 0 <= cpu <= 100:
            raise Unsafe('Invalid CPU utilization')
        while self.step < len(self.thresholds) and cpu >= self.thresholds[self.step]:
            self.step += 1
        while self.step > 0 and cpu < self.thresholds[self.step-1] - 5:
            self.step -= 1
        return max(minimum, self.speeds[self.step])


def desired_rpm(snapshot, cpu=0, minimum=4300, load_rpm=None):
    """Use the strongest temperature/load request; preserve early handoffs.

    The selectable 3000–4300 floor is for supervised idle validation. Reach
    full cooling at the existing handoff thresholds, not at damage limits.
    """
    check(snapshot, enforce_cutoffs=False)
    if not 3000 <= minimum <= 4300 or not math.isfinite(cpu) or not 0 <= cpu <= 100:
        raise Unsafe('Invalid fan floor or CPU utilization')
    margin = min(LIMITS[k] - snapshot['temps'][k] for k in LIMITS)
    cpu_temp = max(snapshot['temps']['TC0D'], *(v for k,v in snapshot['independent'].items() if k.startswith('coretemp/')))
    gpu_temp = max(v for k,v in snapshot['independent'].items() if k.startswith('nouveau/'))
    fraction = max(0, (4-margin)/2, (cpu_temp-45)/10, (gpu_temp-48)/8)
    thermal_request = minimum + min(1, fraction)*(5500-minimum)
    load_request = CpuCooling().request(cpu, minimum) if load_rpm is None else load_rpm
    if not minimum <= load_request <= 5500:
        raise Unsafe('Invalid load cooling request')
    return min(5500, math.ceil(max(thermal_request, load_request)/25)*25)


def notify(message):
    address = os.environ.get('NOTIFY_SOCKET')
    if not address:
        raise Unsafe('systemd notify socket required')
    if address.startswith('@'):
        address = '\0' + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.connect(address)
        connection.sendall(message.encode())


class CpuMeter:
    """Machine-wide busy percentage; guest fields must not be counted twice."""
    def __init__(self):
        self.history = deque([self.counters()], maxlen=6)

    @staticmethod
    def counters():
        fields = Path('/proc/stat').read_text().splitlines()[0].split()
        if fields[0] != 'cpu' or len(fields) < 9:
            raise Unsafe('Invalid aggregate CPU statistics')
        ticks = list(map(int, fields[1:9]))
        return sum(ticks), ticks[3] + ticks[4]

    @staticmethod
    def utilization(before, after):
        total = after[0] - before[0]
        idle = after[1] - before[1]
        if total <= 0 or not 0 <= idle <= total:
            raise Unsafe('Invalid CPU counter delta')
        return 100 * (total-idle) / total

    def sample(self):
        current = self.counters()
        self.history.append(current)
        # Approximately five seconds at the one-second control interval.
        # Compute from ticks over the whole window, not an average of percentages.
        return self.utilization(self.history[0], current)


class Policy:
    def __init__(self):
        self.mode = 'auto'
        self.quiet_since = None
        self.reason = 'Waiting for 30 seconds below 65% CPU and cool temperatures'

    def decide(self, snap, cpu, now):
        check(snap, enforce_cutoffs=False)
        if not math.isfinite(cpu) or not 0 <= cpu <= 100:
            raise Unsafe('Invalid CPU utilization')
        cores = [v for k,v in snap['independent'].items() if k.startswith('coretemp/')]
        cpu_temp = max(*cores, snap['temps']['TC0D'])
        margin = min(LIMITS[k] - snap['temps'][k] for k in LIMITS)
        gpu_temp = max(v for k,v in snap['independent'].items() if k.startswith('nouveau/'))
        hot = cpu_temp >= 55 or gpu_temp >= 56 or margin <= 2
        if cpu >= 80:
            self.mode = 'auto'
            self.quiet_since = None
            self.reason = 'CPU use >=80%'
            return self.mode
        if self.mode == 'manual':
            self.reason = 'Temperature override: maximum manual cooling' if hot else 'Stepped load and temperature curve'
            return self.mode
        cool = cpu < 65 and cpu_temp < 50 and gpu_temp < 52 and margin >= 4
        # Do not override normal automatic cooling if firmware is no longer
        # asking for close to maximum. This workaround is for the 5500 RPM case.
        needs_override = snap['target'] >= 5300 and snap['rpm'] >= 5200
        if cool and needs_override:
            if self.quiet_since is None:
                self.quiet_since = now
            if now - self.quiet_since >= 30:
                self.mode = 'manual'
                self.quiet_since = None
                self.reason = 'Low load and cool for 30 seconds'
        else:
            self.quiet_since = None
            self.reason = 'Automatic speed already below near-maximum' if not needs_override else 'Waiting for cooldown'
        return self.mode


def control(hw, minimum=4300):
    if not 3000 <= minimum <= 4300:
        raise Unsafe('Manual floor must be 3000–4300 RPM')
    if os.geteuid() != 0 or not os.environ.get('INVOCATION_ID'):
        raise Unsafe('Control requires systemd supervision')
    watchdog = int(os.environ.get('WATCHDOG_USEC', '0'))
    if not 1_000_000 <= watchdog <= 10_000_000:
        raise Unsafe('A 1–10 second systemd watchdog is required')
    baseline = hw.snapshot()
    check(baseline, enforce_cutoffs=False)
    if baseline['manual'] != 0:
        raise Unsafe('Existing manual controller detected')
    faults = hw.faults()
    if any(faults.values()):
        raise Unsafe(f'SMC fault/thermal flag set: {faults}')
    def stop(signum, frame):
        raise StopRequested(f'Stopped by signal {signum}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    emit('control_start', faults=faults, idle_floor=minimum, **baseline)
    target = 5500
    last_increase = time.monotonic()
    logged = 0
    mode = 'auto'
    policy = Policy()
    cpu_meter = CpuMeter()
    cpu_cooling = CpuCooling()
    auto_handoff_at = None
    try:
        notify('READY=1\nWATCHDOG=1\nSTATUS=Automatic mode; watching load and temperatures')
        while True:
            time.sleep(1)
            snap = hw.snapshot()
            check(snap, enforce_cutoffs=False)
            cpu = cpu_meter.sample()
            faults = hw.faults()
            if any(faults.values()):
                raise Unsafe(f'SMC fault/thermal flag: {faults}')
            if snap['manual'] != (1 if mode == 'manual' else 0):
                raise Unsafe('Controller ownership lost; refusing to fight SMC/another daemon')
            if mode == 'manual' and abs(snap['target'] - target) > 10:
                raise Unsafe('Fan target changed unexpectedly')
            if mode == 'manual' and time.monotonic() - last_increase > 15 and snap['rpm'] < target - 250:
                raise Unsafe('Fan not keeping up with requested cooling')
            wanted = policy.decide(snap, cpu, time.monotonic())
            if wanted == 'auto' and mode == 'manual':
                restore()
                mode = 'auto'
                auto_handoff_at = time.monotonic()
                emit('handoff', reason=policy.reason, cpu_percent=round(cpu,1), **snap)
            elif wanted == 'manual' and mode == 'auto':
                check(snap)
                hw.write('fan1_manual', 1)
                hw.write('fan1_output', 5500)
                mode = 'manual'
                target = 5500
                last_increase = time.monotonic()
                auto_handoff_at = None
                emit('quiet_mode', reason=policy.reason, cpu_percent=round(cpu,1), **snap)
            if mode == 'manual':
                request = desired_rpm(snap, cpu, minimum, cpu_cooling.request(cpu, minimum))
                # Raise cooling immediately; lower by no more than 50 RPM/sec.
                new_target = max(request, target - 50)
                if new_target > target:
                    last_increase = time.monotonic()
                target = new_target
                hw.write('fan1_output', target)
                if abs(hw.read('fan1_output') - target) > 10:
                    raise Unsafe('Fan command readback mismatch')
            elif auto_handoff_at and time.monotonic() - auto_handoff_at >= 15:
                # A lower automatic target is fine when firmware chooses it.
                # A near-max request without corresponding RPM is not.
                if snap['target'] >= 5300 and snap['rpm'] < snap['target'] - 250:
                    raise Unsafe('Automatic handoff did not deliver requested cooling')
                emit('handoff_verified', **snap)
                auto_handoff_at = None
            notify(f'WATCHDOG=1\nSTATUS={mode}; CPU {cpu:.0f}%; fan {snap["rpm"]} RPM; PSU {snap["temps"]["Tp0C"]} C; floor {minimum} RPM')
            if time.monotonic() - logged >= 10:
                emit('control', mode=mode, reason=policy.reason, cpu_percent=round(cpu,1), requested=target if mode=='manual' else None, faults=faults, **snap)
                logged = time.monotonic()
    finally:
        restore()


def monitor(hw, seconds):
    until = time.monotonic() + seconds
    while True:
        emit('sample', **hw.snapshot())
        if time.monotonic() >= until:
            return
        time.sleep(2)


def probe(hw, seconds, rpm):
    if os.geteuid() != 0 or os.environ.get('MACMINI_SUPERVISED_PROBE') != '1':
        raise Unsafe('Probe requires the supplied systemd supervisor')
    if not os.environ.get('INVOCATION_ID'):
        raise Unsafe('Probe must run under systemd')
    if rpm not in (4300, 4500, 5000) or not 10 <= seconds <= 60:
        raise Unsafe('Only a 10–60 second probe at 4300, 4500 or 5000 RPM is permitted')
    baseline = hw.snapshot()
    check(baseline)
    if baseline['manual'] != 0:
        raise Unsafe('Existing manual controller detected')
    faults = hw.faults()
    emit('preflight', faults=faults, **baseline)
    if any(faults.values()):
        raise Unsafe('SMC fault/thermal flag set; refusing override')
    def stop(signum, frame):
        raise StopRequested(f'Stopped by signal {signum}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    observed = []
    started = time.monotonic()
    try:
        # Enter manual control at maximum first, then make one small reduction.
        hw.write('fan1_manual', 1)
        hw.write('fan1_output', 5500)
        if hw.read('fan1_manual') != 1:
            raise Unsafe('Manual mode was not accepted')
        hw.write('fan1_output', rpm)
        while time.monotonic() - started < seconds:
            snap = hw.snapshot()
            faults = hw.faults()
            emit('probe', elapsed=round(time.monotonic()-started, 2), faults=faults, **snap)
            check(snap, baseline)
            if any(faults.values()):
                raise Unsafe('SMC fault/thermal flag appeared')
            if snap['manual'] != 1 or abs(snap['target'] - rpm) > 10:
                raise Unsafe('SMC rejected/overrode requested control; do not bypass')
            if time.monotonic() - started >= 10:
                observed.append(snap['rpm'])
            time.sleep(1)
        responds = bool(observed) and all(abs(v-rpm) <= 180 for v in observed[-5:])
        emit('result', responds=responds, requested_rpm=rpm, observed_rpm=observed)
    finally:
        restore()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['snapshot', 'monitor', 'probe', 'restore', 'control', 'wait'])
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--rpm', type=int, default=5000)
    parser.add_argument('--min-rpm', type=int, default=4300)
    args = parser.parse_args()
    if args.mode == 'restore':
        restore()
        return
    if args.mode == 'wait':
        deadline = time.monotonic() + 30
        while True:
            try:
                Hardware().snapshot()
                return
            except (OSError, Unsafe):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
    hw = Hardware()
    if args.mode == 'snapshot':
        emit('sample', **hw.snapshot())
    elif args.mode == 'monitor':
        if not 1 <= args.seconds <= 3600:
            parser.error('monitor duration must be 1–3600 seconds')
        monitor(hw, args.seconds)
    else:
        with open('/run/macmini-thermal-guard/control.lock', 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.mode == 'control':
                control(hw, args.min_rpm)
            else:
                probe(hw, args.seconds, args.rpm)


if __name__ == '__main__':
    try:
        main()
    except StopRequested as exc:
        emit('stopped', message=str(exc))
    except Exception as exc:
        emit('error', message=str(exc))
        sys.exit(1)
