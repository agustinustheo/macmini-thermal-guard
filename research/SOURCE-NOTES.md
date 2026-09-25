# Source notes preserved for offline reference

These are factual extractions and paraphrased notes, not complete article copies.
Retrieved [timestamp omitted].

## S1 — Macmini4-1/Maverick — Ubuntu community hardware measurements

https://help.ubuntu.com/community/Macmini4-1/Maverick

Type: firsthand model-specific sensor examples. Date: last edited 2013-12-14.

- Macmini4,1 is the Mid-2010 model.
- Example fan readings: 1804 and 1796 RPM; reported minimum 1800 RPM.
- CPU diode readings 51.8 and 51.2 C; core readings 51 and 47 C. Workload not specified.

Limitations: Two example snapshots, not a controlled idle population average.

## S2 — 2010 2.4 GHz owner fan observations — indg

https://forums.macrumors.com/threads/fan-speed-on-2-4ghz-mac-mini-2010-never-changes.943010/

Type: firsthand owner observations. Date: 2010-06-20 and 2010-06-25.

- Post 1: idle CPU approximately 38 C; both cores at 100% for five minutes reached approximately 73 C, fan remained near 1800 RPM.
- Post 16: CPU approximately 82 C with fan approximately 2200–2400 RPM.
- Post 24 reports a CUSTOM controller: base 2300 RPM, full encoding for six hours at 4000–4200 RPM, CPU 60–65 C, room about 38 C.

Limitations: Anecdotal; post 24 is not factory behavior and room temperature exceeded Apple operating range. Do not pool custom and factory curves.

## S3 — Mid-2010 owner PSU readings — nrajack

https://forums.macrumors.com/threads/safe-temp-levels-in-mid-2010-mini.1161364/

Type: firsthand owner observations. Date: 2011-05-31.

- Reported usual PSU temperature 130 F = 54.4 C.
- Hot-room PSU reading 140–150 F = 60.0–65.6 C; room 90 F = 32.2 C; fan about 2500 RPM.
- CPU 160 F = 71.1 C and reported heatsink 178 F = 81.1 C.

Limitations: Single owner, unverified sensor accuracy and an external fan blowing across the case; not a safe-temperature specification or population average.

## S4 — Macs Fan Control issue 214 — Macmini4,1 diagnostic dump

https://github.com/crystalidea/macs-fan-control/issues/214

Type: firsthand software diagnostic dump. Date: 2019-09-27.

- Macmini4,1 with P8800 2.66 GHz, GeForce 320M, macOS 10.12.6.
- Fan minimum 1800, maximum 5500, observed 5504 RPM with custom CPU-diode control.
- CPU diode 52.5 C; Tp0C PSU 39.7031 C; TN1D 54 C; TM0p 45.75 C; TH0P 29.5 C.
- Constant-looking G channels match this machine, including TN1G 90 C.

Limitations: Different CPU option and custom fan policy; high fan speed affects temperatures. Optical channels report invalid 128 C. Neither an ideal baseline nor a healthy-machine certification.

## S5 — Apple — About fans and fan noise

https://support.apple.com/en-ie/101576

Type: manufacturer guidance. Date: retrieved 2026-09-25.

- Internal temperature sensors influence fan cooling.
- Ambient temperature also affects fan response.
- Intensive workloads can increase fan noise.

Limitations: General Apple guidance; no model-specific CPU-percent/RPM table.

## S6 — Apple — Mac mini Mid 2010 technical specifications

https://support.apple.com/en-us/112588

Type: manufacturer specifications. Date: retrieved 2026-09-25.

- Surrounding operating temperature 10–35 C.
- Maximum continuous power 85 W.
- Processor options 2.4/2.66 GHz Core 2 Duo; GeForce 320M.

Limitations: Room temperature is not a limit on internal sensor readings. No PSU sensor temperature limit is provided.

## S7 — Intel — Core 2 Duo P8600 product specifications

https://www.intel.cn/content/www/cn/zh/products/sku/35568/intel-core2-duo-processor-p8600-3m-cache-2-40-ghz-1066-mhz-fsb/specifications.html

Type: manufacturer specifications. Date: retrieved 2026-09-25.

- P8600: two cores, 2.40 GHz, 25 W TDP.
- Tjunction specified as 105 C.

Limitations: Maximum junction specification is not an ideal operating temperature; CPU TDP is not whole-machine wall power.

## S8 — Apple — Mac mini power consumption and thermal output

https://support.apple.com/en-gb/103253

Type: manufacturer measurements for listed configuration. Date: retrieved 2026-09-25.

- Mid-2010 Core 2 Duo configuration: idle 10 W, CPU Max 85 W; thermal output 34 and 290 BTU/h.

Limitations: Not a measurement of this modified Linux system. Does not specify fan electrical power or justify converting CPU percentage linearly to RPM.
