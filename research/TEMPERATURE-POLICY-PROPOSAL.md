# Temperature control and spoken warnings: research and proposal

Researched 2026-09-25. **Historical proposal.** On 2026-09-26 (local time),
all-component temperature-based fan control was adopted without
spoken alerts. The temperature-only policy is now implemented; the current
behavior is in README.md and REFERENCE.md. Alerts, shutdowns and reboots remain
unimplemented at that revision. A subsequent profile added controlled shutdown;
see [QUIETER-PROFILE.md](QUIETER-PROFILE.md). The proposal below is retained as the reasoning behind the
revision, not as an installation status report.

## Findings

Intel specifies 105 C Tjunction for this machine's P8600 [S7]. This is a
maximum junction specification, not an ideal target or an exact temperature
at which permanent damage starts. A CPU reading of 75 C alone is not evidence
of thermal damage and does not justify a reboot. Intel describes throttling
and thermal shutdown as processor protections, but these cannot certify the
condition of the rest of this particular machine [S9].

Intel explicitly notes that other components can reach their limits
independently of the CPU [S10]. Heat and airflow are shared, but a CPU junction
reading does not give RAM chip, PSU component, or GPU temperature. SMC proximity
readings also need not equal the hottest junction inside the named component.
No verified model-specific PSU or installed-memory temperature specification
has been found; do not invent one or reuse the CPU's 105 C limit for them.

Read-only snapshot at Unix time 1790355153.2393782:

| Sensor | Reading C |
| --- | ---: |
| CPU core 0 / core 1 | 39 / 40 |
| CPU SMC diode TC0D | 41.5 |
| Independent GPU | 49 |
| Memory-labelled TM0P / TM0p | 37.5 / 37.5 |
| PSU-labelled Tp0C | 55.5 |
| Drive-proximity TH0P / TH0p | 25.5 / 25.5 |

Fan measured 3329 RPM, target 3325, manual mode. These readings do not establish
hardware health or measure every internal hotspot. No heat stress test was run.

## Recommended fan-policy revision

Use temperature as the controlling input and retain CPU percentage only for
diagnostics. Apple describes internal temperature and ambient conditions as
drivers of fan activity [S5]. A percentage is not a direct heat measurement.
This supports temperature-driven control, but does not establish an optimal
custom curve for this machine.

Retain the existing conservative per-sensor thermal curves, 3000 RPM floor,
5500 RPM ceiling, immediate upward response and gradual downward response.
Take the highest request across all required sensors, not the numerically
hottest component. For example, the PSU reaches our provisional full-cooling
point at 58 C; its request can override a cooler CPU. These settings are
custom intervention points, not manufacturer limits.

Removing utilization-based handoff would allow 100% CPU usage without forcing
auto if the temperatures remain low. It does not mean capping cooling at the
idle floor: any sensor can request up to 5500 RPM. Missing/invalid sensors,
fault flags, loss of fan tracking and watchdog expiry must retain the existing
fallback. Keep the qualification period and temperature hysteresis when
entering quieter control.

Automatic mode is not inherently stronger than a verified 5500 RPM command.
If considering auto at CPU 60 C, verify what cooling it actually delivers;
do not assume that a lower automatic fan target during high temperatures is
evidence of recovery. Prefer verified maximum cooling while hot. Root cause of
the original firmware maximum-speed request remains unresolved.

## Proposed alerts and emergency response

- CPU 75 C sustained for 10 seconds: spoken warning. This is an early-warning
  choice, not a damage threshold. It revises the earlier tentative 70 C idea.
- CPU 85 C sustained for a few seconds: stronger alert; stop heavy work and
  investigate cooling.
- CPU 95 C: urgent alert. Recommend shutdown and remaining off if temperature
  continues rising despite full cooling. No automatic shutdown is implemented.
- Also detect sustained rapid heating once already warm; filter isolated
  samples and use cooldown hysteresis and reminders rather than repeated
  alerts every monitoring cycle.
- Other monitored components need alerts based on their own conservative
  intervention settings. CPU warning levels must not replace these checks.
- Sensor unavailability and failed fan tracking need distinct warnings.

Rebooting is not a reliable thermal remedy: it restarts the workload and can
create repeated boot/overheat cycles. A deliberately configured emergency
shutdown should stay off. Software cannot give a universal guaranteed damage
temperature for the complete machine. Room air conditioning helps ambient
conditions but does not verify heat transfer or sensor accuracy.

## Spoken-warning delivery

eSpeak NG supports British English and Received Pronunciation [S11]. It can
render a short recording once for local playback, avoiding continuous speech
generation or an online service. This is recognisably synthetic speech, not
a natural human recording. WAV is directly supported by the installed paplay;
MP3 conversion is unnecessary for this use. No voice engine was installed or
recording generated during this research-only step.

A dummy audio output does not produce audible alerts. Verify audio routing
and playback before relying on notifications. Desktop audio does not
automatically reach a browser running on another device.

Keep warning delivery in a separate read-only process so notification/audio
failures cannot delay fan-control watchdog updates. It should use prerecorded
clips and log alerts when audio is unavailable.

## Additional sources

- S9: [Intel: Information about Temperature for Intel Processors](https://www.intel.com/content/www/us/en/support/articles/000005597/processors.html).
  Read 2026-09-25. Explains junction limits, throttling, shutdown, and why Intel
  does not give a universal typical operating range. General guidance rather
  than a guarantee about this old machine.
- S10: [Intel: Maximum Operating Temperature](https://www.intel.com/content/www/us/en/support/articles/000094759/processors.html).
  Read 2026-09-25. Other components can reach thermal limits independently.
- S11: [eSpeak NG English-language documentation](https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages/gmw/en.md)
  and [voice documentation](https://github.com/espeak-ng/espeak-ng/blob/master/docs/voices.md).
  Read 2026-09-25. British and Received Pronunciation voice support.

The S7 Intel product page was present in search results with 105 C on this
recheck, but direct page fetch timed out. The earlier preserved product facts
remain in SOURCE-NOTES.md. This access limitation should not be confused with
new measurements or a newly established temperature specification.
