# Quieter floor with controlled thermal shutdown

This profile changes the installed floor from 3000 to 2350 RPM, a 650 RPM
reduction when all monitored components are cool. It does not clear the
unexplained maximum automatic fan behavior identified by the thermal audit.
The operating decision accepts that unresolved risk; normal readings do not
prove sensor attachment or exclude hidden hardware faults.

## Evidence and its limits

Sources checked 2026-09-26; findings are retained here for offline reference:

- The [Ubuntu Macmini4,1 hardware page](https://help.ubuntu.com/community/Macmini4-1/Maverick)
  records 1796–1804 RPM, an 1800 RPM minimum, CPU-diode readings of 51.2–51.8 C,
  and independent core readings of 47–51 C. The workload is unspecified. These
  support 1800 RPM as a normal model baseline, not clearance for a faulty unit.
- A [firsthand 2010 report](https://forums.macrumors.com/threads/fan-speed-on-2-4ghz-mac-mini-2010-never-changes.943010/)
  describes approximately 1800 RPM with CPU temperatures reaching 73 C during
  a short workload, and later approximately 2200–2400 RPM at 82 C. It is anecdotal,
  not a controlled safety study or a recommended curve.
- [Intel specifies P8600 Tjunction as 105 C](https://www.intel.cn/content/www/cn/zh/products/sku/35568/intel-core2-duo-processor-p8600-3m-cache-2-40-ghz-1066-mhz-fsb/specifications.html).
  This is a processor junction specification, not an ideal temperature or a
  threshold transferable to proximity, memory, drive or power-supply readings.
- [mbpfan's configuration](https://github.com/linux-on-mac/mbpfan/blob/master/mbpfan.conf)
  uses default CPU thresholds of 63/66/86 C and normally discovers fan limits
  through applesmc. These are another project's defaults, not Apple limits.
  Its [CPU-based input](https://github.com/linux-on-mac/mbpfan) does not replace
  whole-system monitoring for an unresolved sensing fault.

Conclusion: the previous curve is aggressive relative to these examples.
No located source establishes a safe RPM/temperature curve for this particular
fault condition or a verified damage temperature for the PSU-labelled channel.
2350 is a bounded operating choice, 550 RPM above the reported model minimum;
it is not an Apple-recommended or mathematically optimal setting.

## Cooling calculation

The linear temperature fractions, all-component maximum selection, immediate
target increases and 50 RPM-per-loop downward limit are unchanged. For any fixed set of readings, reduction
versus the 3000 RPM profile is between zero and 650 RPM, including rounding.

| Dominant reading; other channels cool | Previous request | New request |
| --- | ---: | ---: |
| CPU <=45 C, GPU <=48 C, PSU <=56 C | 3000 | 2350 |
| GPU 49 C | 3325 | 2750 |
| GPU 50 C | 3625 | 3150 |
| CPU 50 C / GPU 52 C / PSU 57 C | 4250 | 3925 |
| GPU 54 C | 4875 | 4725 |
| CPU >=55 C / GPU >=56 C / PSU >=58 C | 5500 | 5500 |

These are requests at fixed temperatures; lower airflow can increase temperatures
and thus raise the request again. A quieter floor does not guarantee quieter
steady-state operation. Read-only live observation is required after installation.

The manual RPM validity check retains a 250 RPM tolerance below the quieter floor.
A higher target must allow physical acceleration from that floor; the existing
15-second acceleration allowance and target-minus-250 tracking check still apply.
Target readback, ownership, sensor checks, watchdog and
automatic restoration remain. CPU utilization is still not a cooling input.

Startup still requires 30 continuous qualifying seconds, CPU <50 C and GPU <52 C.
All SMC entry margins remain 4 C below their existing cutoffs except Tp0C, which
uses a 3 C margin (<=57 C). In the initial trial the old gate kept automatic
maximum cooling while Tp0C remained at 56.25–56.5 C. This entry-only adjustment
allows the temperature curve to operate at that baseline; it does not raise
the PSU's 58 C full-cooling or 65 C shutdown threshold. At 57 C the curve requests
3925 RPM, not the idle floor. No manufacturer PSU limit is inferred from this.

## Controlled shutdown policy

All values below are precautionary custom cutoffs, not manufacturer damage limits.
The sustained threshold requires 10 continuous seconds on the same channel;
a brief fall below it resets that channel's timer. Emergency thresholds act on
the first valid sample. Unknown constant G channels remain excluded.

| Channel(s) | Sustained C | Emergency C |
| --- | ---: | ---: |
| Highest CPU core/diode, TC0D | 70 | 85 |
| Independent GPU | 75 | 90 |
| Tp0C (PSU-labelled) | 65 | 70 |
| TA0P | 45 | 50 |
| TC0H, TC0P, TC0p | 65 | 70 |
| TH0P, TH0p, TO0P, TO0p | 55 | 60 |
| TM0P, TM0p, TW0P, Tm0P | 60 | 65 |
| TN0D | 70 | 75 |
| TN0P, TN0p | 65 | 70 |
| TN1D, TN1E, TN1F, TN1S | 75 | 80 |

A critical reading together with fan speed below the reported minimum minus
250 RPM also triggers immediately. The shutdown decision latches for the life
of the process. It requests maximum cooling before asking systemd to power off;
failure of that write does not prevent the request. Rejected poweroff requests
are retried every 10 seconds. Once accepted, the controller keeps requesting
maximum cooling until systemd stops it. It never reboots or forces a power cut.

The poweroff command is the locally documented asynchronous
`systemctl --no-block poweroff`. Enqueueing it is not proof that the entire
shutdown completed. Missing/invalid sensors still follow the existing fault
restoration path; a failed controller/kernel or plausible-but-wrong sensor can
defeat software protection. This is not an independent hardware cutoff.

## Validation

51 simulation tests pass. Added coverage checks the bounded/monotonic reduction,
unchanged maximum cooling from every sensor, lower-floor tachometer tolerance,
every shutdown channel and timer, short spikes, alternating hot channels,
emergency readings, stalled-fan critical readings, and poweroff failures.
The controller-loop test verifies a poweroff retry despite failed fan writes
and lost sensor reads after the critical decision has latched,
and confirms reduced targets never resume after a critical event.

Actual shutdown and overheating are not induced. The service remains enabled
at boot. The [completed live trial](../evidence/QUIETER-PROFILE-VALIDATION.md)
records the measured result and its limitations.
