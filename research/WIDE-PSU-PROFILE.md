# Installed gradual PSU curve

The broader curve proposed in [PSU baseline research](PSU-BASELINE-RESEARCH.md)
is now installed following an explicit operating decision. It replaces the
steep 56–58 C PSU curve. These are custom control settings, not Apple ratings
or a repair of the unexplained firmware maximum-speed request.

| Tp0C, PSU-labelled | PSU-only requested RPM |
| --- | ---: |
| Up to 56 C | 2350 |
| 57 C | 2550 |
| 58 C | 3000 |
| 59 C | 3600 |
| 60 C | 4300 |
| 61 C | 4900 |
| 62 C and above | 5500 |

Requests interpolate linearly between adjacent points and round upward to
25 RPM. For example, 57.25 C requests 2675 RPM, 57.5 C requests 2775,
and 57.75 C requests 2900 rather than the previous 4925. A configured floor
higher than the table request still takes precedence; the installed floor
remains 2350 RPM. The fan limits are checked against this supported model's
reported 1800 minimum and 5500 maximum before control proceeds.

All other component curves remain unchanged. Each component requests cooling
independently and the greatest request wins. A 51 C GPU still requests 3550 RPM;
therefore a PSU request of 2550 is not an overall fan-speed cap. Increases are
immediate; decreases remain limited to 50 RPM per control loop. CPU utilization
is not an input. No temperature readings are averaged away.

PSU full cooling changes from 58 to 62 C. The maximum-cooling status decision
uses the new endpoint too. The 65 C sustained shutdown rule (ten continuous
seconds) and 70 C immediate emergency rule are unchanged. Every other critical
temperature and all sensor validation, fan tracking, fault restoration and
watchdog behavior remain. The numeric margin from full cooling to shutdown
is not proof of an adequate physical safety margin or shutdown completion.

Startup stays automatic until thirty qualifying seconds have elapsed. Its
PSU entry ceiling is now 58 C (previously 57.5 C), with the existing CPU/GPU
and other SMC entry checks. A warm restart above that ceiling may wait for cooldown even though
continuous manual operation can use the wider curve. This permits the table's
3000 RPM point after qualifying; it does not bypass the timer, sensor checks
or other-component entry limits. No reboot is introduced. The service remains
enabled at boot.

The existing probe and startup-validation cutoffs are separate from continuous
manual fan control. In particular, the historical 60 C PSU probe cutoff was
not raised to accommodate the wider runtime curve.

## Verification

`pnpm run build` passes 58 simulation tests. Coverage checks every PSU table
point and intermediate values, monotonic requests, configurable floor handling,
all-component demand selection, the 62 C maximum-cooling path, unchanged
65/70 C shutdown rules, sensor/fan faults, and startup timing. Tests confirm
that 58–61 C no longer trigger the previous PSU maximum-speed behavior.

No synthetic stress, critical temperature or real shutdown is induced. Live
observation records startup, sixty seconds of settling after manual entry,
and fifteen subsequent minutes. See the [validation report](../evidence/WIDE-PSU-VALIDATION.md)
for the completed observation and its limitations. A single observation does
not establish long-term safety or explain the underlying SMC behavior.
