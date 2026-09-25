# Gradual PSU table: deployment and validation

The installed controller implements the requested table exactly at its knots:
2350 RPM through 56 C; 2550 at 57 C; 3000 at 58 C; 3600 at 59 C; 4300 at 60 C;
4900 at 61 C; 5500 at 62 C. It interpolates between points, rounds upward to
25 RPM and takes the maximum of all component requests. The configured floor
remains 2350 RPM; CPU/GPU and other component curves are unchanged.

`pnpm run build` passed 58 simulation tests. Tests cover the entire PSU ramp,
interpolation, floor handling, component precedence, startup qualification,
fan/sensor faults, immediate full cooling at 62 C, and the unchanged 65 C
ten-second shutdown / 70 C immediate shutdown. The runtime maximum-cooling
status uses 62 C too; no obsolete 58 C PSU maximum remains in that decision.

Installed and repository controller SHA-256:
`22cd4b972048d45dc92713ec6b5313f2d9aeb9f7fccc3b83f3b1de8c010c333c`.

The service was restarted to load the code and remains enabled at boot.
No synthetic stress load, reboot, sensor fault or real shutdown was induced.

## Initial observation

The first 302.79 seconds (61 samples, `wide-psu-startup-observation.jsonl`)
remained in firmware automatic mode. Direct one-second checks identified
CPU >=50 C, GPU >=52 C and one PSU 57.75 C reading as entry-timer reset causes.
Those startup checks were unchanged in the initial installation. Subsequent CPU/GPU
readings reached their existing full-cooling thresholds while an unrelated
concurrent workload was active. This was not evidence of a failed fan write
or a remaining steep PSU curve.

After cooling, a further 171.5-second observation still failed to qualify
manual entry with the 57.5 C PSU ceiling (`wide-psu-warm-entry-observation.jsonl`).
The read-only observer was stopped before the next installation; the service
remained active until its intentional update restart. The final startup gate
retains thirty continuously qualifying seconds, CPU <50 C, GPU <52 C and the
other SMC margins, but permits PSU <=58 C (the new table's 3000 RPM point).
The existing probe cutoff remains 60 C, full cooling is 62 C and sustained
shutdown is 65 C. Tests cover timer reset at 58.25 C and entry after
fluctuating 57.5–58 C readings for the full thirty seconds.
At 57.75 C the new PSU request is 2900 RPM, but CPU/GPU temperatures can
independently request 5500 and firmware still owns the fan until entry qualifies.

These are software-control tests and short observations, not certification of
the underlying hardware or manufacturer PSU temperature limits. The table is
an explicitly selected operating tradeoff. See [the current profile](../research/WIDE-PSU-PROFILE.md)
and [research](../research/PSU-BASELINE-RESEARCH.md) for the rationale and limits.

## Final observation after the entry adjustment

Total duration 963.22 seconds (192 samples). After
the first sixty seconds for settling, 903.22 seconds
and 180 samples remained; all were manual.

| Measurement after settling | Range |
| --- | --- |
| CPU cores | 40.0–54.0 C |
| GPU | 50.0–55.0 C |
| PSU | 57.25–58.25 C |
| Actual RPM | 3144–5122 |
| Target RPM | 3150–5200 |

Mean actual fan speed was 3837 RPM. The final sample was
4076 actual / 3975 target RPM. The GPU drove
most requests; changing the PSU curve did not cap other components.
Occasional higher requests and gradual slowdown explain actual speeds above
the instantaneous PSU-only table. Readings every five seconds do not capture
every one-second controller decision.

The final service remained active and enabled, with zero automatic restarts.
Its invocation logged only control_start, quiet_mode and control events, and
no nonzero inspected SMC fault flags. Source and installed hashes match.
This validates operation during the observed workload, not a matched noise
comparison or long-term thermal safety. The original maximum-speed firmware behavior remains unexplained. No high-temperature shutdown was induced; that path was simulated.

Anonymized readings: `wide-psu-final-observation.jsonl`.
Summary: `wide-psu-summary.json`.
