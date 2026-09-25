# Macmini4,1 thermal reference and current policy

Research date: 2026-09-25. Supported model: 2010 Mac mini, P8600 2.4 GHz, two CPU cores,
GeForce 320M, Linux. This reference preserves extracted facts locally so
future work need not depend on links remaining online.

## What the evidence establishes

Normal idle fan speed is approximately **1800 RPM** [S1, S2]. This machine itself
reports a minimum of 1800 and maximum of 5500 RPM. Neither 3000 nor 3500 RPM is
the original idle baseline. No verified Apple table assigns a particular RPM
to 70% or 80% CPU utilization. Apple describes temperature-dependent cooling
that also responds to ambient conditions [S5].

CPU observations span roughly 38–52 C in idle/light or unspecified examples;
individual loaded examples reach 73–82 C [S1, S2, S4]. These are separate
observations, not an ideal range or a statistical average. Intel specifies
105 C Tjunction for the P8600 [S7]; this is a maximum, not a recommended target.
The locally reported GPU thresholds are 95 C high and 105 C critical. They
come from the Linux driver; a manufacturer-specific GeForce 320M thermal
specification was not independently verified.

For PSU Tp0C, one owner reported a usual 54.4 C and 60–65.6 C in a hot room
[S3]; a different machine with a custom high fan setting reported 39.7 C [S4].
That spread does not establish a safe range or a meaningful average. A
manufacturer PSU-sensor limit, calibration tolerance, and expected thermal
resistance have not been located. The observed 55–56 C here is close to one
historical usual reading but cannot establish overall hardware health.

Apple's **10–35 C operating range is room temperature**, not CPU/PSU sensor
temperature [S6]. Published whole-machine figures are 10 W idle and 85 W CPU
Max for the listed 2010 configuration [S8]. No power meter was used here.

## How the current settings were selected

3000 RPM is a provisional, conservative workaround floor supported by short
supervised trials on this unit. It is above the documented 1800 RPM idle
baseline. It is not a calculated thermal optimum, a reproduction of Apple's
curve, or a declaration that the unexplained maximum-speed request is fixed.

There is insufficient matched data to fit a reliable RPM=f(CPU%) model:
room temperature, workload duration, GPU activity, power, sensor position,
custom controllers and hardware condition differ among the observations.
A statistical average or a linear interpolation of those unrelated examples
would be misleading. The CPU steps are user-requested anticipation of heat;
actual temperature demand always has priority.

| Rising aggregate CPU use | Load-based fan request |
| --- | ---: |
| 0 to below 35% | 3000 RPM |
| 35 to below 50% | 3500 RPM |
| 50 to below 70% | 3900 RPM |
| 70 to below 75% | 4300 RPM |
| 75 to below 80% | 4800 RPM |
| 80% or higher | Firmware automatic control |

CPU percentage covers both cores together, averaged over about five seconds.
Each manual step needs a five-percentage-point fall below its entry threshold
before dropping back. Thus falling-load RPM can differ from this rising-load
table. Targets decrease at no more than 50 RPM per second; increases are
immediate. Above the temperature triggers below, manual control requests
5500 RPM even with low CPU use. Temperature alone does not trigger automatic
handoff while already in manual mode.

| Temperature input | Begin temperature ramp | Maximum MANUAL cooling |
| --- | ---: | ---: |
| Highest CPU core/diode | 45 C | 55 C |
| Independent GPU | 48 C | 56 C |
| PSU Tp0C | 56 C | 58 C |
| Other required SMC sensors | LIMITS minus 4 C | LIMITS minus 2 C |

All these intervention temperatures are precautionary custom settings. They
are deliberately well below the verified CPU limit, but are not Apple/NVIDIA
limits and cannot be called optimal based on the available data.

The implemented calculation is:

- CPU thermal request = floor + (5500-floor) * clamp((CPU_C-45)/10, 0, 1).
- GPU thermal request = floor + (5500-floor) * clamp((GPU_C-48)/8, 0, 1).
- For each SMC sensor: floor + (5500-floor) * clamp((T-(LIMIT-4))/2, 0, 1).
- Take the maximum of the temperature requests and the CPU step; round up
  to 25 RPM, cap at 5500, and apply the downward slew limit.

Examples with otherwise cool sensors: CPU 50 C, GPU 52 C, or PSU 57 C each
requests 4250 RPM. Cool sensors with 70% rising CPU demand request 4300 RPM;
75% requests 4800 RPM. These are calculations of our chosen policy, not
predictions of what Apple's original controller would do.

The service starts in auto and qualifies conditions before taking control.
After an 80% CPU handoff, reentry requires 30 seconds below 65% CPU, CPU below
50 C, GPU below 52 C, and all SMC sensors at least 4 C below LIMITS. Missing or
invalid sensors, SMC faults, fan-tracking failure, service shutdown or watchdog
expiry still restore auto as an emergency fallback. Software cannot reliably
identify every plausible-but-incorrect reading or prevent electrical faults.

## Local measurements and validation

The staged 3500-floor observation lasted 201.8 seconds; a subsequent 3000-floor
observation lasted 232.1 seconds. Both observed PSU 55.0–55.75 C. The second
reached 2990 RPM. A further 363.1-second stepped-policy observation includes
one controller restart around its middle while changing thermal handoff to
maximum manual cooling; its automatic startup samples are not spontaneous
CPU-triggered handoffs. These are short observations, not long-term validation.

The guard passed 44 simulation tests. Independent watchdog restoration was
hardware-tested during the original implementation. The revised guard used
0.80% of total two-core CPU capacity during a 60-second measurement before
the stepped revision; the later steps were not separately profiled.

Current saved snapshot:

| Measurement | Value |
| --- | ---: |
| Actual fan | 2998 RPM |
| nouveau/temp1_input | 48 C |
| coretemp/temp2_input | 40 C |
| coretemp/temp3_input | 41 C |
| PSU Tp0C | 55 C |

Captured UTC: [timestamp omitted].

## Every required SMC channel

The following values are generated from the installed policy source. Channel
IDs are preserved to avoid inventing undocumented sensor locations.

| Channel | Snapshot C | Ramp begins C | Full manual cooling C |
| --- | ---: | ---: | ---: |
| TA0P | 26 | 34 | 36 |
| TC0D | 38 | 56 | 58 |
| TC0H | 36.75 | 46 | 48 |
| TC0P | 34.75 | 46 | 48 |
| TC0p | 34.75 | 46 | 48 |
| TH0P | 25.25 | 38 | 40 |
| TH0p | 25.25 | 38 | 40 |
| TM0P | 36.75 | 46 | 48 |
| TM0p | 36.75 | 46 | 48 |
| TN0D | 39.25 | 51 | 53 |
| TN0P | 33.5 | 44 | 46 |
| TN0p | 33.75 | 44 | 46 |
| TN1D | 48 | 56 | 58 |
| TN1E | 48 | 56 | 58 |
| TN1F | 48.75 | 56 | 58 |
| TN1S | 48.75 | 56 | 58 |
| TO0P | 27.75 | 38 | 40 |
| TO0p | 27.75 | 38 | 40 |
| TW0P | 35.25 | 44 | 46 |
| Tm0P | 31 | 41 | 43 |
| Tp0C | 55 | 56 | 58 |

Unknown constant-looking *G channels are logged but excluded from physical
thermal decisions. Their appearance in another Macmini4,1 dump [S4] supports
caution in interpreting them, not proof of their exact meaning. Drive-proximity
readings are not the same measurement as a disk's internal SMART temperature.

## Sources and future updates

- [Source notes](SOURCE-NOTES.md): eight sources, preserved facts, dates and caveats.
- [Machine-readable sources](sources.json).
- [Historical measurements](observations.csv).
- [Saved local snapshot](local-snapshot.json) and [driver output](local-sensors.txt).
- [Live-trial data](../evidence/load-steps-observation.jsonl).
- [Build/test results](../evidence/load-steps-build.log).

Read this reference and the current guard.py before retuning. Preserve old
observations; record workload, duration, room temperature if actually measured,
sensor names, actual and requested fan RPM, mode, CPU use and software version.
Do not relabel anecdotal temperatures as manufacturer limits, average unrelated
models together, or infer restored hardware health from quieter operation.
