# PSU baseline, normal fan speed, and quieter curve assessment

Research checked 2026-09-26. Model scope: Macmini4,1, Mid-2010. This document
distinguishes firsthand observations from manufacturer limits and proposed
custom settings. It supplements the retained source notes and thermal audit.

## Findings

| Source | What it directly establishes | What it does not establish |
| --- | --- | --- |
| [Ubuntu model-specific measurements](https://help.ubuntu.com/community/Macmini4-1/Maverick) | Examples at 1796–1804 RPM, fan minimum 1800; CPU diode about 51–52 C | No PSU reading or PSU-to-RPM curve |
| [Mid-2010 owner's PSU report](https://forums.macrumors.com/threads/safe-temp-levels-in-mid-2010-mini.1161364/) | Usual PSU about 130 F (54.4 C); 140–150 F (60–65.6 C) and about 2500 RPM in a 90 F (32.2 C) room | Single self-report, not calibrated testing or a safety rating; an external fan was also blowing across the case |
| [Macmini4,1 software diagnostic dump](https://github.com/crystalidea/macs-fan-control/issues/214) | Tp0C labelled PSMI AC/DC supply; about 39.7 C at 5504 RPM with custom CPU control | Not a normal idle baseline; another CPU option and invalid optical-drive readings |
| [2010 owners' fan reports](https://forums.macrumors.com/threads/fan-speed-on-2-4ghz-mac-mini-2010-never-changes.943010/) | Firsthand stock behavior around 1800 RPM; separate custom configuration with 2300 RPM base | CPU reports cannot be substituted for PSU thresholds |
| [Apple model specifications](https://support.apple.com/en-us/112588) | Room operating range 10–35 C; maximum continuous power 85 W | No internal PSU sensor temperature or fan-control table |
| [Apple fan guidance](https://support.apple.com/en-us/101576) | Temperature and surroundings influence cooling | No numeric Macmini4,1 PSU setpoints |
| [Apple technician guide, mirrored](https://manualzz.com/doc/1275070/apple-mac-mini-server--mid-2010-specifications) | Page 17 associates unread PSU sensing with fast fan operation; pages 26–27 discuss sensor/fan diagnostics | No verified Tp0C-to-RPM transfer function or damage threshold was found |
| [VirtualSMC iStat profile dump](https://github.com/acidanthera/VirtualSMC/blob/master/Docs/iStat.txt) | Macmini4,1 profile lists 1800/5500 RPM limits | Its Macmini4,1 section omits Tp0C; another model's ACDC high value must not be imported as a PSU safety limit |
| [mbpfan implementation description](https://github.com/linux-on-mac/mbpfan) | CPU-only temperature input, applesmc fan output | Its CPU defaults are not PSU thresholds |

Only firsthand reports are used as observational evidence; forum replies
asserting that a running machine must be safe are not adopted. The PSU owner
report has an external-airflow confounder and does not justify running this
machine at 2500 RPM with a 65 C PSU. Searches for OEM supply ratings and further
2010 PSU/RPM pairs did not find an authoritative, calibrated curve. Reports
from other generations and marketplace compatibility claims were excluded.

## What this means for a 54–57 C baseline

A PSU reading in the mid-50s is consistent with at least one contemporary
owner report. There is no located evidence that exactly 57 C requires 3000,
3150, or 3925 RPM. Those numbers come from the custom policy, not Apple.
Likewise, the present 58 C full-cooling trigger and 65 C shutdown trigger are
precautionary choices, not documented failure temperatures.

The observed temperature depends on the existing airflow, workload and room
temperature. Lowering airflow can move the equilibrium upward. Consequently
one cannot derive a safe fan curve by subtracting a baseline from temperature.
The retained audit also leaves the firmware's maximum-speed request unexplained.
Readable values do not verify sensor attachment or every firmware fault input.

The installed 2350 RPM floor already falls within a proposed 2000–2450 RPM
quiet-floor range and is 550 RPM above the model's documented minimum. PSU
readings of 54–56 C already request that floor; CPU, GPU or other channels can
still request more. Lowering the floor to 1800 is unnecessary for testing a
gentler PSU response and would change a second variable.

## Why simply lowering 57 C is not a complete solution

The just-installed intermediate curve asks for 3150 RPM at 57 C but retains
5500 at 58 C. Reducing the 57 C point to 2450 while retaining that endpoint
requires a 3050 RPM rise within the next degree. It moves the abrupt increase
instead of providing a gradual curve throughout the warm range. A wider ramp
would be a deliberate increase in the temperature at which full cooling is
requested. Neither this research nor a shutdown command makes that risk zero.

A candidate for a future monitored experiment, **not installed or thermally
validated**, is:

| PSU reading | Candidate PSU-only request |
| --- | ---: |
| Up to 56 C | 2350 RPM |
| 57 C | 2550 RPM |
| 58 C | 3000 RPM |
| 59 C | 3600 RPM |
| 60 C | 4300 RPM |
| 61 C | 4900 RPM |
| 62 C and above | 5500 RPM |

These are designed interpolation points, not values extracted from a published
Apple curve. They respond to the requested gradual increase while retaining
the floor and providing full cooling before the current 65 C shutdown rule.
The three-degree separation is arithmetic, not proof of adequate thermal margin.
Actual slope, sensor lag, heat distribution, and shutdown reliability are unknown.

Recommendation: retain 2350 as the starting floor; assess a broader ramp as a
supervised experiment rather than declaring it safe from forum readings.
Do not silently raise CPU/GPU/memory/drive triggers to force an overall RPM.
All-component maximum selection, immediate hot response and fault checks must
remain. A future trial should change only the PSU policy, include stable room
conditions and ordinary workload, log at least 15–30 minutes after settling,
and end the reduced-airflow trial if temperatures keep climbing or any sensing
or fan-tracking fault appears. An unresolved hardware issue still limits what
such a trial can prove. The broader candidate was evaluated only offline; it was not deployed.

## Read-only local comparison and startup finding

The first 181.5-second observation contains 37 samples: PSU 56.5–57.25 C,
GPU 48–51 C, CPU cores 38–48 C. The controller stayed in automatic mode
throughout this window. The existing entry check requires 30 continuous
qualifying seconds at PSU <=57 C; intermittent 57.25 C samples reset it.
This is a separate policy limitation, not an SMC-write error or a new heat surge.

On these *same recorded readings*, an offline calculation of the candidate
curve gives a mean temperature demand of 3023 RPM versus 3262 for the installed
curve. Other components exceed the candidate PSU request in 32 of 37 samples.
The 239 RPM difference is a calculation, not a measured noise reduction or
prediction of temperatures under reduced airflow. Readings were taken with
firmware running the fan near maximum, so they cannot validate the candidate.
The comparison excludes startup gating and downward rate limiting.

Reproducible inputs and calculated requests are in
[the observation](../evidence/psu-curve-observation.json) and
[the candidate replay](../evidence/psu-candidate-replay.json).
Any future broader-curve implementation also needs an explicitly tested entry
policy compatible with its operating range. The intermediate curve's entry
allowance was subsequently changed from <=57 C to <=57.5 C, retaining all other
entry checks and the thirty-second timer. Simulation verifies fluctuating
57–57.5 C readings qualify only after the full interval, while 57.75 C and
58 C do not qualify. This addresses the observed startup snag without deploying
the broader candidate or raising the 58 C full-cooling threshold.
