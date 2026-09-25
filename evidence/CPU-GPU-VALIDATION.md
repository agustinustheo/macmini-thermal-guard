# CPU/GPU curve deployment and observation

The revised CPU/GPU endpoint curves are installed. Source and installed copy
have identical SHA-256:
`14ac7c9f34600f5e2a68db625882bb233e2956da0685677b21ca386e6ff8c5b4`.
The service is active and enabled at boot. No reboot, stress test, deliberate
critical temperature, shutdown, or fault injection was performed on hardware.

## Checks completed

- `pnpm run build`: 62 simulation tests passed.
- `systemd-analyze verify macmini-thermal-guard.service`: passed.
- Required temperature readings remained available to the observation tool.
- Journal for this service invocation recorded one start, 58 control records,
  and 59 fault-flag samples, all zero. No quiet-mode entry or fault restoration
  was recorded during the observation.
- All critical shutdown settings and the PSU runtime curve remain unchanged.

## Hardware observation

[Raw relative-time readings](cpu-gpu-profile-observation.jsonl) and
[machine-readable summary](cpu-gpu-profile-summary.json) cover 606.05 seconds,
121 snapshots at approximately five-second intervals.

| Measurement | Observed range |
| --- | ---: |
| Highest CPU core/diode | 39.5–59 C |
| Independent GPU | 49–59 C |
| PSU-labelled Tp0C | 57.5–59.25 C |
| Actual fan speed | 5476–5527 RPM |
| Fan target | 5500 RPM throughout |

**The service stayed in automatic mode for the entire observation.** Early
CPU/GPU activity and later PSU fluctuations above the unchanged 58 C entry
ceiling prevented thirty continuous qualifying seconds. In particular, a
58.25 C PSU reading resets that timer even when the CPU/GPU are cool.

The final logged sample was CPU 40 C, GPU 49 C, PSU 58 C, actual fan 5492 RPM.
The new curve calculated a 3000 RPM request driven by the PSU, but that was
not applied because entry qualification had not completed. A calculated
request is not a measured fan speed.

This validates installation and continued guarded automatic operation. It
**does not validate the revised lower-airflow profile on hardware** or prove
thermal equilibrium at its lower fan speeds. A subsequent supervised manual
operation observation is still needed when normal startup qualification
succeeds. The startup check was not bypassed to obtain a quieter result.

No conclusion about long-term safety, acoustic improvement, repaired hardware,
or optimal RPM follows from this observation. The unresolved firmware maximum
request remains a limitation of this software workaround.
