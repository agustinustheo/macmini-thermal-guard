# PSU curve adjustment validation

**Historical record:** the broader PSU table is now installed. See the
[current profile](../research/WIDE-PSU-PROFILE.md); statements below about an uninstalled
candidate or a 58 C PSU full-cooling trigger describe the earlier state.


The installed curve uses a gentler 56–57 C PSU segment, then reaches the
unchanged 5500 RPM request at 58 C. The floor is still 2350 RPM. CPU/GPU/other
sensor curves, critical-temperature poweroff, readback, watchdog and fault
handling are unchanged. See [the curve](../research/PSU-CURVE.md).

The first restart exposed the existing <=57 C PSU entry limit: intermittent
57.25 C readings prevented thirty continuously qualifying seconds. All 37
samples over 181.5 seconds remained automatic, with CPU cores 38–48 C,
GPU 48–51 C and PSU 56.5–57.25 C. This is retained in
`psu-curve-observation.json`; it is not a quiet-mode thermal trial.

The PSU entry allowance was then changed to <=57.5 C while retaining all
other entry checks and the full thirty-second timer. It remains below the
58 C full-cooling point and requests 4325 RPM at the entry ceiling. This is
a custom policy change, not a finding about a manufacturer safety rating.

`pnpm run build` passed all 55 simulation tests. Coverage includes the gentler
quarter-degree response, all-component maximum selection, unchanged full
cooling from each sensor, intermittent 57–57.5 C entry after thirty seconds,
rejected entry at 57.75/58 C, sensor and fan faults, and shutdown timing/retries.
No actual critical heating or poweroff was induced. One initial test expectation
was corrected from 3725 to 3750 RPM to respect upward 25 RPM rounding.

Final installed controller SHA-256:
`98b3ae7d61f6575fb5a7bf4fb3d6095ab9ec545da3d524fc97051b58457c83c7`.

The proposed broader 56–62 C curve in the research report was only calculated
offline. It was not installed or used in either live observation. The live
workaround does not resolve the underlying firmware/hardware uncertainty.

## Final live observation

The final installation was observed for 181.46 seconds in
37 read-only samples. It entered manual mode during the observation
and stayed active and enabled at boot, with zero automatic restarts. The current
invocation logged only control_start, quiet_mode and control events; its logged
SMC fault flags remained zero. Source and installed file hashes matched.

| Measurement | Observed range |
| --- | --- |
| CPU cores | 38.0–47.0 C |
| GPU | 48.0–51.0 C |
| PSU | 56.75–57.5 C |
| Actual fan after 90 seconds | 3567–4645 RPM |
| Target after 90 seconds | 3550–4825 RPM |

Late-window average actual speed was 3993 RPM; final
actual/target were 4457/4325 RPM. Target
and actual speed retain the effect of earlier demands during gradual slowdown.
Five-second samples do not capture every one-second controller input.

This verifies startup recovery and continued monitored control, **not a quieter
steady state**. Workloads and temperatures were not matched against a baseline,
and speed still fluctuated. A wider PSU ramp remains a research proposal.
No synthetic stress load was run. The short trial does not establish long-term
safety or validate the 65 C PSU cutoff as a manufacturer limit.

Raw anonymized readings: `psu-curve-final-observation.json`.
Summary: `psu-curve-final-summary.json`.
