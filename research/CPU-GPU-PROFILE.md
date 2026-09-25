# CPU and GPU endpoint curves

Research and implementation date: 2026-09-26. Model: Macmini4,1, Core 2 Duo
P8600, GeForce 320M. These are custom operating settings, not Apple's fan curve
or a mathematically established minimum cooling requirement.

## Why change the previous profile?

The old GPU ramp began at 48 C and reached 5500 RPM at 56 C. At 54 C it
requested 4725 RPM with the installed 2350 RPM floor. The old CPU ramp
reached maximum at 55 C. These were precautionary experiment settings;
no verified model-specific manufacturer source established those as necessary
full-speed temperatures. Related TN1 channels also reached maximum at 58 C,
so changing only the independent GPU curve would leave a competing old trigger.

## Sources and preserved findings

- [Intel P8600 specifications](https://www.intel.cn/content/www/cn/zh/products/sku/35568/intel-core2-duo-processor-p8600-3m-cache-2-40-ghz-1066-mhz-fsb/specifications.html):
  Tjunction 105 C, 25 W TDP. This is a processor specification, not a target
  temperature, a whole-machine limit, or a reason to raise the existing shutdown.
- [Intel temperature guidance](https://www.intel.com/content/www/us/en/support/articles/000094759/processors.html):
  other system components can reach their limits independently of the CPU.
- [Ubuntu's exact-model installation record](https://help.ubuntu.com/community/Macmini4-1/Maverick):
  reported fan readings approximately 1796–1804 RPM, CPU diode 51.2–51.8 C.
  This documents one original observation; it is not an official control table
  or clearance for a machine with an unexplained firmware cooling request.
- [Nouveau Linux 6.14 fan policy implementation](https://raw.githubusercontent.com/torvalds/linux/v6.14/drivers/gpu/drm/nouveau/nvkm/subdev/therm/base.c):
  `nvkm_therm_compute_linear_duty` interpolates between temperature endpoints.
  This provides an implementation example, not Mac fan thresholds. Nouveau's
  fan duty is not equivalent to the shared Mac fan's RPM.
- [Nouveau Linux 6.14 sensor defaults](https://raw.githubusercontent.com/torvalds/linux/v6.14/drivers/gpu/drm/nouveau/nvkm/subdev/therm/temp.c):
  defaults include 95 C downclock, 105 C critical and 135 C shutdown, followed
  by BIOS parsing. Local hwmon exposes these same three values. Their match
  to generic defaults prevents treating them as independently verified 320M
  manufacturer limits. Do not aim for those temperatures.
- [VirtualSMC sensor-name reference](https://raw.githubusercontent.com/acidanthera/VirtualSMC/master/Docs/iStat.txt):
  Macmini4,1 section names TC0D CPU die, TC0H CPU heatsink, TC0P CPU proximity,
  TN0D MCP die, TN1D MCP internal die and TN0P MCP proximity. This is a software
  mapping reference, not a calibration certificate. TN1E/F/S remain uncertain;
  their separate protection is retained. Profile numbers in that reference
  are not manufacturer thermal ratings.

No reliable public 320M temperature-to-RPM factory table was established.
The endpoint method is supported by a real driver implementation; the values
below are engineering choices constrained by the existing shutdown policy
and observed temperature ranges, not numbers derived from that driver.

## Installed endpoints

Each channel starts at the configured floor, then interpolates linearly to
5500 RPM. All requests are independent; the greatest wins. Rounding is upward
to 25 RPM. The unchanged PSU uses its own multi-point table.

| Reading | Floor through | Full fan at | Sustained shutdown |
| --- | ---: | ---: | ---: |
| Highest CPU core / TC0D | 50 C | 68 C | 70 C |
| Independent GPU / TN1D | 55 C | 72 C | 75 C |
| CPU heatsink TC0H | 45 C | 60 C | 65 C |
| CPU proximity TC0P/p | 45 C | 60 C | 65 C |
| MCP die TN0D | 50 C | 65 C | 70 C |
| MCP proximity TN0P/p | 42 C | 58 C | 65 C |
| Related TN1E, exact location uncertain | 55 C | 70 C | 75 C |
| Related TN1F/S, exact locations uncertain | 58 C | 72 C | 75 C |

The CPU starts earlier than the GPU because local CPU readings react quickly
to workload. Proximity/heatsink endpoints remain lower than die endpoints.
TN1F/S were several degrees warmer than TN1D/E during earlier observations;
the slightly higher starting point accommodates that offset without discarding
those channels. This correlation is not proof of their physical placement.
Memory, drive, ambient, wireless and PSU curves are unchanged.

Examples at the installed 2350 RPM floor, with every other request lower:

| Temperature | CPU-only request | GPU-only request |
| --- | ---: | ---: |
| 50 C | 2350 | 2350 |
| 54 C | 3050 | 2350 |
| 55 C | 3225 | 2350 |
| 60 C | 4100 | 3300 |
| 65 C | 4975 | 4225 |
| 68 C | 5500 | 4775 |
| 70 C | 5500 | 5150 |
| 72 C | 5500 | 5500 |

For example, a 54 C GPU requests 2350 RPM, but a 58 C PSU requests 3000 RPM:
the shared fan must satisfy 3000 RPM. A hot CPU or another sensor can ask for
more. No CPU percentage threshold or fixed low-speed cap is used.

## Startup and protection

Startup still uses firmware control until all channels qualify for thirty
continuous seconds and firmware target/actual speed remain near maximum.
CPU must be <=54 C, GPU <=57 C, PSU <=58 C. `ENTRY_MAX` contains the separate
SMC ceilings; all stay below the original supervised-probe cutoffs. A warm
restart may therefore wait before enabling the quieter curve. These are not
runtime full-speed thresholds. The original probe cutoffs remain unchanged.

Runtime increases are immediate; target decreases remain limited to 50 RPM
per approximately one-second loop. This is asymmetric slew limiting, not
true temperature hysteresis. Wider ramps reduce sensitivity, but workloads
can still cause speed changes. There is no adaptive learner lowering limits.

Shutdown thresholds, ten-second persistence, immediate emergency thresholds,
sensor validation, SMC fault checks, RPM tracking, watchdog and automatic
restoration remain unchanged. Full fan starts 2 C below CPU shutdown and 3 C
below GPU shutdown; numerical headroom does not guarantee a thermal response
before shutdown. No sensor is removed from monitoring to achieve quieter fans.

The unresolved firmware request is still unresolved. A plausible temperature
cannot exclude a detached/misreading sensor. This profile is the requested
software workaround and cannot establish hardware health or long-term safety.

## Validation

`pnpm run build`: 62 passing simulations, including all-channel independent
maximum requests, monotonic curves, sensor failures, new entry bounds within
original probe cutoffs, related GPU channels no longer forcing old maximums,
unchanged critical shutdowns, fan tracking and fault restoration.

See [the local observation](../evidence/CPU-GPU-VALIDATION.md) for measured
response. No intentional overheating, synthetic stress or real poweroff test.
