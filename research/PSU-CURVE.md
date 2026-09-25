# Gentler PSU baseline curve

The Tp0C channel has been observed around 56–57 C. The previous straight ramp
from 56 to 58 C increased the request by roughly 400 RPM per 0.25 C at the
2350 RPM floor. This adjustment reduces that sensitivity below 57 C, without
raising the full-cooling or shutdown temperatures.

| Tp0C | Previous PSU request | New PSU request |
| --- | ---: | ---: |
| 56 C | 2350 | 2350 |
| 56.25 C | 2750 | 2550 |
| 56.5 C | 3150 | 2750 |
| 56.75 C | 3550 | 2950 |
| 57 C | 3925 | 3150 |
| 57.25 C | 4325 | 3750 |
| 57.5 C | 4725 | 4325 |
| 57.75 C | 5125 | 4925 |
| 58 C or higher | 5500 | 5500 |

Cooling fraction is one quarter of the available range at 57 C: linear from
zero at 56 C to 0.25 at 57 C, then linear to 1 at 58 C. Requests round upward
to 25 RPM. This is continuous and monotonic, with a steeper response above
57 C. It reduces sensitivity near the observed baseline, not everywhere.

The highest demand from any monitored component still wins. For example, a
51 C GPU independently requests 3550 RPM even if the PSU requests only 3150.
Decreases remain limited to 50 RPM per loop; increases remain immediate.
There is no new averaging or delay that could hide a high temperature.

The PSU startup allowance is now <=57.5 C for 30 continuous qualifying seconds,
instead of <=57 C. A read-only trial found that 57.25 C fluctuations repeatedly
reset the previous entry timer. This entry remains below full cooling at 58 C;
the new curve requests 4325 RPM at the highest permitted entry temperature.
CPU/GPU and other SMC entry limits and the thirty-second timer remain intact.

The floor, sensor validation, fan tracking, fault handling,
watchdog, and all critical-temperature shutdown rules are unchanged. PSU
full cooling is still 58 C; sustained PSU shutdown is still 65 C for ten
continuous seconds and emergency shutdown is 70 C on a valid sample.

This is an operator-requested noise/cooling tradeoff, not a finding that 57 C
is an officially normal or safe PSU temperature. No verified manufacturer
limit for this channel was found in the retained research. Apple's
[fan guidance](https://support.apple.com/en-us/101576), checked 2026-09-26,
describes temperature-responsive cooling and ambient influences but supplies
no component-specific PSU curve. The unexplained firmware maximum request
remains unresolved. Reduced airflow may warm components and offset the noise
improvement; a short observation cannot establish long-term safety.

See [PSU baseline research](PSU-BASELINE-RESEARCH.md) for the follow-up source
assessment and an explicitly uninstalled broader-ramp candidate.
