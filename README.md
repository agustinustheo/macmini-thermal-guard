# Mac Mini 2010 thermal guard

Published evidence is anonymized; see [PRIVACY.md](PRIVACY.md) for scope,
authorship exceptions, and handling of private diagnostic records.

**Operating status, 2026-09-26: running and enabled at boot, by explicit operator choice.** The existing controller was re-enabled unchanged and its
automatic startup was verified after a reboot. The maximum firmware fan request
remains unexplained; resuming the workaround does not resolve the safety gaps
identified by the [thermal audit](evidence/thermal-audit-20260925T1705Z/REPORT.md).
See the [post-reboot check](evidence/POST-REBOOT-CHECK-20260926.md) for current
measurements and the distinction between operating status and diagnostic clearance.

A conservative **software workaround**, developed on a 2010 Mac mini
(`Macmini4,1`, Linux). It does not establish or repair the underlying fault.
Full-speed fan operation was reported before Linux started. Software temperature
readings and zero SMC fault flags cannot exclude hardware or sensing faults.


## Current measurements and preserved research

See [research/REFERENCE.md](research/REFERENCE.md) for normal idle evidence,
temperature references, the current calculated curve, all sensor triggers,
local observations, and eight dated source records preserved for offline use.

See [the temperature-only control and spoken-warning proposal](research/TEMPERATURE-POLICY-PROPOSAL.md)
for follow-up manufacturer research, whole-system monitoring considerations,
and alert delivery findings. Its temperature-based fan policy is now implemented as described below. Spoken
alerts were dropped by operator choice; no audio feature was installed.

## What was established

- Automatic mode was on, minimum 1800 RPM, maximum and target 5500 RPM.
- The actual fan tracked that 5500 RPM request.
- `SBF` (bad-sensor flags), `MSSF` (bad-fan flags), and the inspected SMC
  thermal-request/history flags were zero. This is not a clean bill of health.
- In a supervised 30-second 5000 RPM test, actual speed settled at 4981–5021
  RPM. PSU-channel readings remained 55.0–55.75 C. Automatic control was
  restored afterward. The trial produced an audible improvement.
- Therefore, the fan and Linux control path respond. The reason the SMC
  selects 5500 RPM in automatic mode remains unknown. Do not conclude that
  the fan motor, PSU, or temperature sensor needs replacement from these data.
- Subsequent 60-second probes settled around 4500 and then 4300 RPM, with
  PSU readings 55–56 C. One early 4500 RPM probe correctly rolled back on
  an overly strict CPU-rise rule; that rule was adjusted to distinguish
  normal CPU fluctuations from slower peripheral-temperature changes.

## Current controller

`guard.py control --min-rpm 3000` runs under `macmini-thermal-guard.service`.
The installed idle floor is **3000 RPM**. Fan speed depends on temperatures
across the machine; CPU utilization is neither sampled nor used as a trigger.

- Configurable manual floor: **3000–4300 RPM**, with up to **5500 RPM** cooling.
- Requires 21 named SMC channels, both independent CPU core readings, and the
  independent GPU reading. Each sensor contributes its own cooling request;
  **the largest request wins**. Cooler components cannot cancel a hotter
  component's request. This compares demand relative to each sensor's curve,
  not raw temperatures across unrelated components.
- The existing conservative thermal curves are unchanged:

  | Sensor | Start increasing above floor | Full 5500 RPM request |
  | --- | ---: | ---: |
  | Highest CPU core/diode | 45 C | 55 C |
  | Independent GPU | 48 C | 56 C |
  | PSU-labelled Tp0C | 56 C | 58 C |
  | Memory-labelled TM0P/TM0p | 46 C | 48 C |
  | Drive-proximity TH0P/TH0p | 38 C | 40 C |
  | Every other required SMC channel | LIMITS minus 4 C | LIMITS minus 2 C |

  Requests interpolate linearly between the endpoints and round upward to
  25 RPM. These are precautionary custom intervention settings, **not verified
  component damage limits or Apple's original fan curve**. Proximity sensors
  do not necessarily measure a component's hottest internal point.
- Full cooling stays in manual mode while the controller is healthy. Even
  100% CPU activity does not trigger automatic handoff; actual temperatures
  can still request maximum cooling.
- Startup stays automatic. Quiet-mode entry requires 30 continuous seconds
  with CPU below 50 C, GPU below 52 C, and every SMC channel at least 4 C below
  its cutoff. PSU must therefore be no higher than 56 C. The workaround takes
  over only if firmware still requests at least 5300 RPM and actual speed is
  at least 5200 RPM. Otherwise it leaves firmware control alone.
- Status and journal entries identify the sensor(s) driving the thermal request
  (`CPU`, `GPU`, an SMC channel ID, or `idle floor`). During gradual slowdown,
  the current target may remain above that request.
- Unknown constant `*G` channels are retained in logs but not assumed to be
  physical-temperature readings. Monitoring them as real 70–90 C sensors
  without a model-specific interpretation would give misleading results.
- Checks required sensors and fault flags every approximately 1 second.
- Lowers the target by at most 50 RPM per second, but increases it immediately
  when needed. Checks command readback and actual RPM against the manual target.
- Rejects missing/implausible readings, unexpected model/fan limits,
  loss of control ownership, unexpected target changes, or inadequate fan
  RPM. It cannot reliably detect every plausible-but-wrong sensor reading.
- An independent systemd watchdog detects an unresponsive process within
  approximately 8 seconds; stop timeout is 3 seconds. `ExecStopPost` requests
  5500 RPM then restores automatic mode. A `finally` handler does the same
  on normal termination or exceptions. No automatic restart after a fault.
- Starts automatically with Linux, waiting up to 30 seconds for sensor drivers.
  Starts in automatic mode and first verifies continuously cool temperatures.
- Stops before system sleep through a conflict with `sleep.target`.
  It does not automatically resume after sleep.
- No network access or third-party Python dependencies.

**Limits:** This cannot prevent a short circuit, detect hidden liquid residue,
repair electronics, or guarantee thermal safety during kernel/SMC/hardware
failure. Quietness is not evidence of a repaired machine. Avoid heavy loads
and unattended operation pending physical assessment. Do not lower the
installed idle floor without another supervised validation. The CLI defaults
to the original 4300 RPM unless the service explicitly supplies --min-rpm.

## Commands

Read temperatures without changing settings:

```sh
python3 guard.py snapshot
```

Service status and recent readings:

```sh
systemctl status macmini-thermal-guard --no-pager
journalctl -u macmini-thermal-guard -n 20 --no-pager
```

Stop the workaround and restore factory automatic control:

```sh
sudo systemctl stop macmini-thermal-guard
```

Start it manually if stopped after a fault or sleep:

```sh
sudo systemctl start macmini-thermal-guard
```

**Enabled at boot**, as requested. It initially leaves firmware control on,
then switches to quiet mode after qualifying for 30 seconds. Before Linux
and its sensor drivers load, the SMC still owns the fan; the software cannot
quiet the firmware startup screen. It stays stopped after a hardware fault
or sleep until explicitly started or the machine boots again.

Disable startup and return to automatic control:

```sh
sudo systemctl disable --now macmini-thermal-guard
```

Emergency restoration independent of the service:

```sh
sudo python3 /usr/local/lib/macmini-thermal-guard/guard.py restore
```

Source resides here. The running copy is root-owned at
`/usr/local/lib/macmini-thermal-guard/guard.py`; the unit is at
`/etc/systemd/system/macmini-thermal-guard.service`. Editing this source alone
does not change the installed controller.

## Validation

```sh
pnpm run build
systemd-analyze verify macmini-thermal-guard.service
```

Build compiles Python and runs simulation tests for missing/invalid/hot
sensors, excessive temperature rise, fan stall, fault-before-write rejection,
unsafe execution rejection, control curves, and rollback on errors. Tests
never write real fan settings.

Hardware checks performed:

1. Independent runtime timeout restored automatic mode.
2. Bounded 5000, 4500 and 4300 RPM probes succeeded and restored automatic mode.
3. A deliberately frozen controller process exercised the actual systemd
   watchdog and its independent restoration path.
4. Simulated component-temperature changes verify cooldown, recovery, and
   rollback on sensor failure. No heat stress test was used on uncertain hardware.

Historical initial-controller 180.6-second observation: service stayed active; settled fan samples
were 4292–4324 RPM, CPU 36–45 C, GPU 46–48 C, PSU 55–56 C. Measured service
overhead was 0.83% of total two-core CPU capacity and 7.33 MiB RAM. Total
electrical power was not measured. `pnpm run build` passed 29 simulation tests.
The boot-enable symlink and systemd unit were verified without rebooting.
Raw observations and summaries are in `evidence/`.

## References

- Linux 6.14 `applesmc` driver, fan target/manual semantics:
  https://github.com/torvalds/linux/blob/v6.14/drivers/hwmon/applesmc.c
- SMC key reference (reverse-engineered; meanings can vary by model):
  https://floe.github.io/smc_util/
- `mbpfan` monitors only CPU temperatures. That is insufficient coverage for
  this experiment involving a desktop PSU/GPU and uncertain hardware state:
  https://github.com/linux-on-mac/mbpfan/blob/master/README.md

## Historical lower idle revision (superseded, 2026-09-25)

The original 4300 RPM floor was a conservative experiment setting, not the
model's normal idle speed. The revised curve uses independent CPU/GPU
temperatures and every required SMC sensor, with a small predictive boost
for moderate CPU load. The 50% CPU handoff, thermal handoffs, ownership
checks, fault checks, watchdog and independent automatic restoration remain.

- A 201.8-second trial with a 3500 RPM floor observed PSU 55.0–55.75 C.
- A 232.1-second trial with a 3000 RPM floor reached 2990 RPM and observed
  PSU 55.0–55.75 C. These short observations do not establish long-term safety.
- **3500 RPM** was selected after an acoustic evaluation
  for that revision of the boot-enabled service. The current floor is 3000 RPM.
- No temperature cutoff was raised. Manual fan stall detection now permits
  the tested lower range, while the requested-RPM tracking check remains.
- 36 simulation tests pass, including lower-floor recovery, moderate-load
  increases, temperature overrides and restoration after sensor failures.

Observations: `evidence/idle-floor-3500.jsonl`, `evidence/idle-floor-3000.jsonl`.
Previous source and service: `evidence/before-lower-idle/`.

## Historical stepped CPU revision (superseded by temperature-only control)

A revision introduced a 3000 RPM idle floor and a higher CPU handoff because
ordinary interactive activity repeatedly crossed the original 50% threshold. That revision
used these rising-load steps, with approximately five
seconds of aggregate CPU smoothing:

| Aggregate CPU use | Load-based request |
| --- | --- |
| Below 35% | 3000 RPM |
| 35% to below 50% | 3500 RPM |
| 50% to below 70% | 3900 RPM |
| 70% to below 75% | 4300 RPM |
| 75% to below 80% | 4800 RPM |
| 80% or higher | Restore firmware automatic control |

These are load-based minimum requests; temperature curves can demand more.
For example, the 4300 RPM step releases only when CPU falls below 65%. Downward
fan changes remain limited to 50 RPM per second, while increases are immediate.
Automatic mode reenters manual only after 30 seconds below 65% CPU with cool
temperatures. CPU 55 C, GPU 56 C and PSU 58 C now demand maximum MANUAL cooling below
80% CPU. No temperature trigger was raised; only the mode at maximum speed
changed. The other thermal triggers, SMC fault checks, fan tracking and the
systemd watchdog remain. Sensor/controller failures still restore automatic
mode because a failed controller cannot safely maintain manual cooling. These
thresholds are precautionary software settings, not manufacturer limits.

44 simulation tests passed. Observations are in
`evidence/load-steps-observation.jsonl`; build output is in
`evidence/load-steps-build.log`. The prior implementation is backed up in
`evidence/before-load-steps/`. This remains a workaround for an unresolved
firmware/hardware cooling request, not proof that the machine is repaired.

## Evidence for RPM selection

Normal idle on Macmini4,1 is around 1800 RPM: Ubuntu's model-specific
measurements show 1796–1804 RPM with a minimum of 1800 RPM:
https://help.ubuntu.com/community/Macmini4-1/Maverick

Apple describes temperature-dependent fan behavior, including the effect of
ambient temperature. There is no verified universal CPU-percentage/RPM table:
https://support.apple.com/en-ie/101576

A firsthand 2010 report recorded 1800 RPM during a short full-CPU test at 73 C,
and later 2200–2400 RPM at 82 C. This is an observation, not a recommended
temperature or an Apple specification:
https://forums.macrumors.com/threads/fan-speed-on-2-4ghz-mac-mini-2010-never-changes.943010/

Our 3000 RPM floor and temperature curves are deliberately conservative custom
settings. They do not reproduce Apple's curve or establish an optimal RPM.
The higher floor is retained because the original full-speed request remains
unexplained; the available short idle trials do not justify assuming the
factory 1800 RPM baseline is adequate for this machine's current condition.
