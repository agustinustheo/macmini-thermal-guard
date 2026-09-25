# Macmini4,1 thermal-management diagnostic report

Audit record: 2026-09-26. Direct Linux measurements;
no reboot, disassembly, sensor fault clearing, firmware flashing or reduced-fan
probe during this audit. This is suitable for sharing with a repairer or another
assistant. It supersedes earlier claims that normal temperatures alone justify
using the workaround.

**Conclusion: no exposed temperature sensor or tachometer was demonstrated to
have failed, but the reason for maximum automatic fan speed remains unexplained.
A hardware/SMC fail-safe has NOT been excluded. Reduced-speed override is NOT
cleared under the audit's diagnostic safety requirement.**

## 1. Exact hardware

- Model identifier: `Macmini4,1`, Mid-2010 Mac mini.
- Logic board identifier: `Mac-F2208EC8`.
- CPU: Intel Core 2 Duo P8600, 2.40 GHz, 2 cores / 2 threads.
- GPU: NVIDIA MCP89 / GeForce 320M, PCI ID `10de:08a4`, driver `nouveau`.
- `lm-sensors` was already installed; no packages were installed.

## 2. Thermal modules and hwmon devices

Loaded modules include `applesmc`, `coretemp`, and `nouveau`. Kernel reports
CPU thermal monitoring TM2 enabled. The three hwmon devices are:

| Class path | Driver | Actual sensor directory |
| --- | --- | --- |
| hwmon0 | coretemp | /sys/devices/platform/coretemp.0/hwmon/hwmon0 |
| hwmon1 | applesmc | /sys/devices/platform/applesmc.768 |
| hwmon2 | nouveau | /sys/devices/pci0000:00/0000:00:17.0/0000:05:00.0/hwmon/hwmon2 |

The Apple driver uses a legacy layout: hwmon1 has no direct `name` file or
sensor attributes; its `device` link leads to them. This is not intermittent
sensor disappearance. A naive `find` that does not follow class symlinks or the
legacy device path misses these attributes.

## 3. Every exposed temperature and repeated measurements

Four-minute observation: **241.594 seconds, 119 samples**, approximately
2 seconds apart. Table values are the last sample, not
universal normal-temperature specifications. Raw input/label/limit fields remain in a private archive; relative sample times
are preserved in `repeated-readings.jsonl`.

| Driver / label | Last C | Observed range C | Response |
| --- | ---: | ---: | --- |
| applesmc/TA0P | 24.5 | 24.5–25 | Changed during observation |
| applesmc/TC0D | 35.75 | 34.75–40.5 | Changed during observation |
| applesmc/TC0G | 70 | 70–70 | Constant; interpretation unresolved |
| applesmc/TC0H | 34.25 | 33.5–35.25 | Changed during observation |
| applesmc/TC0P | 32.75 | 32.75–33.5 | Changed during observation |
| applesmc/TC0p | 33 | 32–33.5 | Changed during observation |
| applesmc/TCPG | 73 | 73–73 | Constant; interpretation unresolved |
| applesmc/TH0G | 60 | 60–60 | Constant; interpretation unresolved |
| applesmc/TH0P | 24.25 | 24–24.75 | Changed during observation |
| applesmc/TH0p | 24.25 | 24–24.75 | Changed during observation |
| applesmc/TM0G | 75 | 75–75 | Constant; interpretation unresolved |
| applesmc/TM0P | 34.5 | 34.5–35.5 | Changed during observation |
| applesmc/TM0p | 34.5 | 34.5–35.5 | Changed during observation |
| applesmc/TN0D | 37 | 36–37.75 | Changed during observation |
| applesmc/TN0G | 67 | 67–67 | Constant; interpretation unresolved |
| applesmc/TN0P | 31.25 | 31.25–32 | Changed during observation |
| applesmc/TN0p | 31 | 31–31.75 | Changed during observation |
| applesmc/TN1D | 45 | 45–46 | Changed during observation |
| applesmc/TN1E | 45 | 45–46 | Changed during observation |
| applesmc/TN1F | 46.75 | 46.75–48 | Changed during observation |
| applesmc/TN1G | 90 | 90–90 | Constant; interpretation unresolved |
| applesmc/TN1S | 46.75 | 46.75–48 | Changed during observation |
| applesmc/TNPG | 70 | 70–70 | Constant; interpretation unresolved |
| applesmc/TO0P | 27.25 | 27–27.75 | Changed during observation |
| applesmc/TO0p | 27.25 | 27–27.75 | Changed during observation |
| applesmc/TW0P | 32.75 | 32.75–33.25 | Changed during observation |
| applesmc/Tm0P | 29 | 29–29.75 | Changed during observation |
| applesmc/Tp0C | 54.75 | 54.5–55.75 | Changed during observation |
| coretemp/Core 0 | 35 | 34–43 | Changed during observation |
| coretemp/Core 1 | 35 | 34–43 | Changed during observation |
| nouveau/temp1_input | 45 | 45–46 | Changed during observation |

These are 28 SMC entries, 2 CPU cores and 1 GPU input. Not every SMC label is an
independent physical sensor: some are processed/raw counterparts or unexplained
constants. Memory and drive-proximity readings do not measure every chip or
internal disk hotspot. The seven constant G-suffixed values match another
Macmini4,1 diagnostic dump, but their exact model-specific meaning is not proven.
They must not simply be called seven overheating components or seven broken
sensors. [Comparable original diagnostic dump](https://github.com/crystalidea/macs-fan-control/issues/214)

A bounded 30-second single worker used 60% duty on one thread (roughly 30% of
whole-machine CPU capacity), at reduced scheduling priority. It had read-error,
fan/automatic-mode and conservative temperature abort conditions. CPU activity
averaged 19.09% before, 31.70% during, and 20.72% afterward; the machine was not
otherwise idle. Core readings were 34–43 C before, 34–40 C during, 34–43 C after.
The exercise completed without an abort. It did not cause a clear rise above
background peaks; full fan cooling and existing workloads confound attribution.
Sensor values changed over time, but this short test does NOT validate sensor
calibration, every hotspot or long-term cooling capacity. No additional heating
was used to force a more dramatic result.

## 4. Fan current/minimum/maximum and control fields

At the end of the timed observation, direct sysfs values were:

```text
fan1_label  = Exhaust
fan1_input  = 5498 RPM
fan1_min    = 1800 RPM
fan1_max    = 5500 RPM
fan1_output = 5500 RPM
fan1_manual = 0 (automatic)
```

Actual speed varied 5472–5524 RPM across the timed observation. Small excursions
above the nominal target are consistent with regulation/measurement variation;
this is not a tachometer stuck at exactly 5500 or reporting zero. No PWM sysfs
attributes or second fan were exposed. `FNum=1`, `FS! = 0000`.

## 5. Is 5500 actually maximum?

Yes: both `fan1_max` and the SMC `F0Mx` key independently returned 5500 RPM.
`F0Mn` returned 1800. This conclusion comes from this machine, not a model guess.
Another key, `FMAx`, contained 5540.75; its exact model-specific purpose was not
established, and it is not the Linux per-fan maximum attribute.

## 6. Missing, invalid, suspicious or intermittent readings

- All 31 exposed temperature inputs remained readable, with unchanged inventory
  in all 119 samples. No zero, negative, 127/128 C sentinel or missing input was
  found. SMC temp labels all had matching inputs. Nouveau legitimately uses an
  unlabeled temp1 input; no label is required for that device.
- `fan1_safe` consistently returns EINVAL. Enumeration found no `F0Sf` key.
  Linux explicitly describes that optional key as not supported on all models.
  This alone does not indicate a broken thermal sensor.
- Boot says `temp=29 index=28`: enumeration explains the difference. There are
  28 T-prefixed `sp78` keys plus `Tp0c` of type `sp3c`. Linux exposes only `sp78`
  entries here. `Tp0c` was readable as raw hex `21f6`; its physical meaning and
  units are unverified. It was NOT reinterpreted as an extra temperature.
- Extra raw-key reads returned EIO for `FPhz`, `SIS!`, `SIT!`, `SPT!`. These are
  control/override-style keys, not the working temperature/tachometer inputs.
  Their access restrictions or implementation may explain the failures; a
  hardware communication fault cannot be inferred from them alone.
- `MSSF`, `SBF`, `SPHR`, `SPHS` all read zero. This is useful evidence but not a
  complete Apple hardware self-test. In particular, the generic published SBF
  description uses a different size from this machine's 4-byte field.
- Additional uninterpreted state: `SAS! = 0000f0f7`, `SFBR = 04`, `SBFE = 01`,
  `SBFD/SBFF/SBFS = 0`, `SPS! = 0`, `F0Mt = 0`. Generic references describe SAS!
  as ADC override bits, but no validated Macmini4,1 bit mapping/default was
  established. Do not clear it or assert that these values prove a fault.

[Linux driver source](https://github.com/torvalds/linux/blob/v6.14/drivers/hwmon/applesmc.c)
explains the optional fan-safe key and type-filtered temperature inventory.
[SMC key reference](https://floe.github.io/smc_util/) is reverse-engineered and
must not be treated as a complete model-specific diagnosis.

## 7. Kernel and boot journal findings

Before the additional raw-key reads, no applesmc communication/read/timeout
error was present in the filtered current-boot kernel logs. Initialization:

```text
[8.615030] applesmc: key=215 fan=1 temp=29 index=28 acc=0 lux=0 kbd=0
[8.617962] applesmc ... hwmon_device_register() is deprecated ...
```

The deprecation warning is a driver API warning, not a failed sensor.
Additional reads during THIS audit produced these timestamped errors:

```text
[16115.903976] applesmc: FPhz: read data[0] fail
[16335.276538] applesmc: SIS!: read data[0] fail
[16335.532627] applesmc: SIT!: read data[0] fail
[16335.751884] applesmc: SPT!: read data[0] fail
```

Do not misreport them as spontaneous errors preceding the incident. Other boot
messages include ACPI duplicate-MADT/video-method issues and missing Nouveau
`nvaf_fuc084` / `nvaf_fuc084d` firmware with `msvld` initialization failure.
The GPU temperature input still works; no evidence ties those messages to the
fan request. No thermal shutdown or active exposed overtemperature alarm was
found in the reviewed logs. Absence of a Linux log cannot exclude SMC action.

## 8. Behavior before Linux

A loud fan was reported after attempting
the Option/Alt startup-picker test. This was not directly witnessed or measured
by the agent. It supports a below-Linux cause IF Linux was truly not started.
No reboot was performed to repeat the test. Existing Linux logs cannot tell us
actual preboot fan RPM.

## 9. Fan-control processes, packages and services

At audit start, `macmini-thermal-guard` was active, enabled and in manual mode
around 3300 RPM. After reviewing its code, it was stopped using its restoration
path; the fan returned to automatic maximum. Its boot enablement was then
removed so an unexplained SMC request will not be overridden after a restart.
Final state: `inactive`, `disabled`, `Result=success`. Code and unit retained.

No running mbpfan/macfanctld/fancontrol/thinkfan or other named fan daemon was
found. The queried packages mbpfan, macfanctld, fancontrol and thinkfan were not
installed. Searches of conventional system/user services, startup files and
local executables found only this custom unit. These checks do not prove the
absence of every arbitrary past writer; no system-call tracing was installed.

`thermald` is installed/enabled but inactive: it exits on this platform because
RAPL/PowerCap support is missing. It is not actively controlling the fan.
`macmini-fan-probe-4500` is a failed, inactive historical transient unit: its
log shows an earlier intentionally strict CPU-rise abort, followed by automatic
restoration. It is not a second active controller or evidence of a new fan fault.

## 10. How the custom controller works

Reviewed `/usr/local/lib/macmini-thermal-guard/guard.py`, identical to project
source at SHA-256 `64ce0dcd215d06b1f1eef4165c00d00b0f222c81499083992085fc1a474e3805`.
A matching copy is preserved as `controller-reviewed.py`. No controller code
was edited during this audit; pending source changes existed before it began.

- Reads all 28 exposed SMC temperatures, both coretemp inputs and GPU input.
  Uses 21 named SMC channels plus CPU/GPU for thermal control; excludes seven
  constant-looking G channels from cooling decisions while still reading them.
- Uses the Linux applesmc sysfs interface. Writes `fan1_manual=1` and
  `fan1_output` (target). It does not change minimum RPM or PWM. Reads fault
  keys by moving the sysfs key-index selector, then restores the selector;
  it does not write SMC fault-key contents or clear faults.
- Current revision ignores CPU utilization. Range 3000–5500 RPM. Full requests
  occur at CPU 55 C, GPU 56 C, PSU-labelled Tp0C 58 C, memory-labelled TM0P/p
  48 C, or other conservative per-channel endpoints. These are custom settings.
- Validates expected model, 1800/5500 limits, required readings, finite values,
  broad 10–<110 C range, fault flags, ownership, target readback and actual RPM.
  Uses stricter temperature checks before entering manual control.
- It treats 30 seconds of cool readings plus a near-max firmware request as
  permission to override. This is the central policy gap: it cannot establish
  that firmware's request is unnecessary or that every relevant sensor is known.
- Immediate increases; decreases no faster than 50 RPM per loop (~1 second).
  Startup qualification provides delay, but there is no explicit per-temperature
  rise/fall hysteresis band and no runtime rapid-rise alarm.
- Read/write/ownership failures propagate to a `finally` restoration routine.
  That requests hard-coded 5500, sets manual=0, and checks the mode readback.
  It does not guarantee successful cooling if communication itself fails.
- systemd has an 8-second watchdog, 3-second stop timeout and independent
  ExecStopPost restoration. A kernel hang, power loss or failed SMC can defeat
  software restoration. No automatic restart after a fault. Stops for sleep.
- No controlled critical-temperature shutdown, automatic reboot or user alert
  is implemented. Existing processor hardware protection is not a substitute
  for a verified whole-system policy.

The already-existing fan code passes 35 simulation tests and the unit validates.
Tests were rerun during the audit without changing the code. Passing those tests
validates modeled behavior, not hardware safety or the cause of firmware demand.

## 11. Is it safe to activate the override?

**Not established under the audit's diagnostic safety requirement.** It has
several useful safeguards, but explicitly lowers an unexplained firmware request
and has no complete sensor-health diagnosis or critical shutdown. Normal readings
and zero checked fault flags are not sufficient clearance. Read-only logging is
appropriate; the manual reduction mode should remain blocked pending explanation.

## 12. Most likely explanation

A persistent firmware/SMC-level cooling request or unresolved state is the leading
category, given continued maximum speed in automatic mode without the custom
process and the reported preboot behavior. This is NOT proof of a failed sensor,
liquid damage, a defective SMC, or a specific connector. No component was isolated.

Important limitation: the restoration routine itself writes 5500 before handing
back to auto. A subsequent `F0Tg=5500` read alone cannot distinguish an actively
recomputed firmware demand from a retained target/state. A lower-target experiment
was deliberately not performed because it conflicts with the requested safety
boundary. The reported original/preboot behavior adds evidence beyond that read.

## 13. Alternative explanations ranked by evidence

1. Unexplained SMC thermal policy/state, including a fail-safe based on a sensor
   or condition not correctly exposed/interpreted by Linux: compatible, unresolved.
2. Marginal sensor cable/connector or board-level sensing fault:
   possible; no open/intermittent exposed sensor demonstrated.
3. Persisting controller/firmware state or a past software-written setting:
   possible; reset reportedly did not resolve it, and preboot report weakens a
   purely Linux-startup explanation. Additional override fields remain undecoded.
4. Moisture/residue affecting sensing or connections: a possible mechanism,
   but there is no software evidence identifying liquid damage or its location.
5. Partial fan wiring/control fault: possible, but varying plausible tachometer
   readings and earlier successful tracking of several commanded speeds argue
   against a fully disconnected tachometer or completely failed speed control.
6. Genuine sustained overheating in the measured channels: not supported during
   this short full-fan observation; an unmeasured hotspot remains possible.
7. Another currently running conventional fan daemon: none found. A hidden or
   transient writer is not conclusively excluded by process/config inspection.
8. General SMC bus failure: working repeated temperature/tach reads argue against
   it; restricted control-key read failures alone do not establish it.
9. Fan motor stuck mechanically/electronically at maximum: weakened strongly by
   earlier successful lower-speed observations, including at the audit start.

## 14. Targeted physical inspection if troubleshooting continues

Power off and unplug before touching connectors; do not open the internal PSU.
These are inspection candidates, not diagnosed failed parts:

- **Fan lead and logic-board socket underneath the lifted fan:** check seating,
  individual wire retention, corrosion and socket solder attachment. Loss of
  tach feedback can produce zero/erratic RPM; loss of control can prevent speed
  changes. Neither complete failure is demonstrated here.
  [2010 fan connector guide, step 5](https://www.ifixit.com/Guide/Mac+Mini+Mid+2010+Fan+Replacement/3108)
- **Both hard-drive thermal-sensor leads at the logic board:** check the sensor
  at the drive corner and the one associated with its flex cable, including
  attachment to the measured surface. An open lead can cause invalid readings;
  a detached sensor can read plausibly but too cool.
  [2010 drive-sensor connectors, step 13](https://www.ifixit.com/Guide/Mac+mini+Mid+2010+Hard+Drive+Cable+Replacement/3171)
- **Optical-drive thermal-sensor lead and connector:** inspect that specific
  small lead for seating/damage; readable TO0P/p does not prove correct attachment.
  [2010 logic-board guide](https://www.ifixit.com/Guide/Mac+mini+Mid+2010+Logic+Board+Replacement/3115)
- The Apple technician guide also identifies heatsink and PSU sensing as
  possible fast-fan causes and separately replaceable drive sensors. PSU-related
  inspection should be limited to accessible connector/board condition by a
  competent repairer; a Tp0C reading does not verify the whole PSU sensing path.
  [Apple-authored 2010 technician guide, mirrored by iFixit](https://documents.cdn.ifixit.com/TSLAH2b5VilxtjhS.pdf)

There is no evidence supporting buying a fan, PSU or logic board yet. The
technician guide's troubleshooting pages contain some inherited Late-2009
footers despite its Mid-2010 title; the 2010 iFixit guides corroborate the
specific connector locations listed above.

## 15. Required changes before considering manual control again

1. Add a latched diagnostic-only / no-reduction state for unexplained maximum
   firmware demand. Sensor plausibility alone must not automatically clear it.
2. Read actual fan min/max dynamically, validate them against a supported model
   profile, and use the verified max in all normal/fault/restoration paths.
   The current hard-coded model check fails closed but is not dynamic control.
3. Preserve per-component monitoring; verify expected key identities, sensor
   coverage and model-specific fault/override semantics. Check freshness and
   plausible cross-sensor behavior without declaring every stable reading bad.
4. Add true thermal hysteresis or sustained-cooldown logic to manual downshifts;
   retain immediate increases and the independent watchdog.
5. Add explicit component-specific critical-event handling: attempt maximum
   cooling, log/notify, then controlled shutdown where warranted, staying off.
   Do not implement automatic reboot. Do not transplant CPU limits onto RAM/PSU.
6. Verify actual fan/mode after fallback where communication permits. If a write
   fails or a sensor becomes uncertain, keep the fault latched; do not keep
   trying reduced targets or claim fallback succeeded solely from a write call.
7. Treat firmware/manual override as capable of suppressing thermal demand;
   restoring auto is a fallback, not proof that firmware or hardware is healthy.

These are recommendations only. No controller logic was changed in this audit.

## 16. Is reducing the fan currently justified?

**No—not with the required confidence.** The accessible readings show no observed
thermal runaway or failed tachometer, but neither explains the original 5500 RPM
behavior or excludes an SMC fail-safe. Automatic full-speed operation is the
current conservative state, not a certification that the machine is safe to run
unattended. Controller source is preserved; service is stopped and boot-disabled.

## Evidence and reproducibility

- `hardware.txt`: uname, OS, CPU, PCI drivers, modules, sensors, package queries.
- `sysfs-inventory.json`, `applesmc-paths.txt`: raw attributes and actual paths.
- `smc-keys.json`, `extra-status.json`: key names/types and selected raw values.
- `repeated-readings.jsonl`, `summary.json`: relative-time observation and summary.
- `kernel-filtered.txt`: kernel log before extra raw-key queries.
- `kernel-relevant-after.txt`, `applesmc-kernel-final.txt`: distinguish query-induced errors.
- `journal-filtered.txt`, `services.txt`, `service-final.txt`: boot and service state.
- `controller-reviewed.py/.service`: exact audited source and unit.
- `build.log`: 35 passing simulation tests.
- Diagnostic Python scripts are preserved. Only the key-index selector was written
  during raw inspection; sensor values, masks, fault flags and raw SMC data were
  not changed. The selector was restored afterward.

Private raw logs are archived outside the repository. Published sample times
are relative to each record, with location and host identifiers omitted. The absence of a fault during a four-minute
sample cannot exclude intermittent faults outside that interval.
