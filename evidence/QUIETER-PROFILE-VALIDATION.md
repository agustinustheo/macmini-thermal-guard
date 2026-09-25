# Quieter profile: validation

The installed controller and unit match the tested repository source. The
controller SHA-256 is
`b5a90a78bb0b28ee53696568f1a67e6013597f480937a79d6151fa9a2db97c3b`.

## Changes validated

- Cool floor reduced from 3000 to 2350 RPM. Full-cooling thresholds remain
  unchanged; this is not a constant subtraction from hot-condition fan requests.
- PSU entry allowance is <=57 C for 30 continuous qualifying seconds, while
  full cooling still begins at 58 C and sustained critical shutdown at 65 C.
- Component-specific controlled shutdown is latched after 10 continuous seconds
  at its threshold, or immediately at its higher emergency threshold. It retries
  rejected poweroff requests despite failed fan writes or subsequent lost sensor
  reads. It never reboots or forces an abrupt power cut.
- Sensor/ownership/target checks, watchdog and automatic restoration remain.
  Tachometer checks allow acceleration from the lower floor while retaining the
  15-second target-tracking failure check.

`pnpm run build` passed 51 simulation tests. `systemd-analyze verify` passed.
The build log is `quieter-profile-build.log`. Shutdown calls, sensor faults and
fan faults were simulated; neither overheating nor an actual poweroff was induced.

## Read-only observation after the final installation

Duration: 302.567 seconds, 61 samples, no read errors. No controller restart or
code change occurred during this final observation. Earlier installation trials
included deliberate restarts and are not combined with these measurements.
No artificial stress load was started; ordinary background activity continued.

| Measurement | Observed result |
| --- | --- |
| CPU cores | 38–48 C |
| Independent GPU | 48–50 C |
| PSU-labelled Tp0C | 56.25–57.25 C |
| Memory proximity | 38.25–39.5 C |
| Actual fan, samples after 120 seconds | 3464–4253 RPM; mean 3884 |
| Target, samples after 120 seconds | 3325–4325 RPM |
| Final actual / target | 3886 / 3775 RPM |
| Controller CPU, percentage of total two-core capacity | 0.813% |
| Service at completion | active, enabled at boot, zero automatic restarts |

No critical-temperature or poweroff event was logged during the observation.
The lower floor was not reached because component demand and gradual slowdown
kept the target higher. A 650 RPM floor reduction does not demonstrate a 650 RPM
reduction in actual speed throughout the test. This is not a matched before/after
noise or thermal-capacity experiment, and no sound-level measurement was made.

Raw anonymized samples are in `quieter-profile-observation.json`; aggregate
results are in `quieter-profile-summary.json`. They retain elapsed time rather
than absolute observation timestamps and omit machine/account identifiers.

This short observation does not establish long-term or unattended safety, verify
every sensor's physical attachment, or resolve the original firmware cooling
state. Critical shutdown depends on valid sensing and a functioning OS; it is
not an independent hardware protection circuit.
