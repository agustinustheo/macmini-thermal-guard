# Hot startup cooling gap

A previous boot reached the controller's sustained CPU shutdown threshold.
The service requested and completed an orderly poweroff. The thermal readings
were valid and SMC fault flags in the logged samples were zero.

| Previous-boot sample | Highest CPU | GPU | PSU-labelled sensor | Fan actual / target | Controller mode |
| --- | ---: | ---: | ---: | ---: | --- |
| First recorded control sample | 68 C | 71 C | 61.25 C | 1807 / 1800 RPM | Automatic |
| Next recorded control sample | 71 C | 72 C | 60.5 C | 1797 / 1800 RPM | Automatic |

The log then recorded `critical_temperature` and `poweroff_requested` with
`CPU >= 70 C for 10 seconds`. Systemd completed the shutdown. These samples
show a firmware automatic fan target of 1800 RPM even while the controller's
calculated temperature request was 5500 RPM. The controller did not write a
new fan target because its previous automatic-to-manual transition required
thirty cool seconds and a firmware fan already near maximum.

The revised controller responds sooner when its calculated temperature request
at the supported 2350 RPM reference floor reaches at least 3500 RPM while
actual or firmware-target fan speed is more than 250 RPM lower. It enters
supervised manual control at the calculated speed. If the request reaches
4300 RPM, it instead starts at 5500 RPM and descends along the curve as the
machine cools. Required sensors, fault flags, fan tracking, watchdog and
critical shutdown still apply. Ordinary quiet takeover retains the
thirty-second cool qualification and strict startup checks. A high configured
idle floor by itself does not count as heat.

`pnpm run build` passes 68 simulations, including warm takeover at the curve
speed, hot CPU/GPU and SMC-channel rescue, adequate firmware cooling, a cool
automatic fan at 1800 RPM, and controller-loop replays that verify speed
writes before reaching the shutdown limit. These tests do not prove a hidden
hardware sensor is healthy or that firmware automatic control is repaired.

The first installed revision of this fix had a live rescue event: firmware
automatic mode was still targeting 1800 RPM at CPU 62 C; the controller
entered manual mode at 5500 RPM, actual fan speed subsequently reached about
5000 RPM, and CPU fell to about 52 C in later journal samples. No new critical
temperature event was recorded during that interval. The final revision adds
the earlier 3500 RPM takeover without changing the proven hot rescue path.

The [relative-time deployment samples](hot-start-deployment-observation.jsonl)
cover the first two minutes after that initial rescue-capable revision was
installed.

The final revision's [relative-time samples](warm-takeover-deployment-observation.jsonl)
and [summary](warm-takeover-deployment-summary.json) cover 151.55 seconds and
31 snapshots. Automatic fan control started near 1800 RPM. A `warm_takeover`
event occurred at CPU 57 C, GPU 58 C and PSU 58.25 C while actual fan speed
was 1791 RPM and firmware target 1800 RPM. The new controller entered manual
mode at its calculated curve speed. During the observation the fan reached
3814 RPM, CPU peaked at 59 C, GPU at 61 C, and PSU at 58.25 C. The final
sample showed CPU 56 C, fan 3437 RPM and target 3400 RPM. The service was
active and enabled at boot; eighteen fault-flag samples were zero. No critical
event, failed fan tracking or automatic restoration occurred.

The previous 1800-RPM-at-71-C behavior was not recreated on hardware. These
observations demonstrate the earlier live takeover and subsequent fan response,
but cannot guarantee that hidden hardware faults or future high-load events
will be safe. No deliberate heating or actual shutdown was performed for this
validation.
