# Post-reboot operating check — 2026-09-26

This follows the thermal audit, rather than
replacing it. The existing service was re-enabled at boot, followed by a reboot after a
15-second delay. Those actions completed.
The subsequent investigation used read-only measurements and left the running
controller and its configuration unchanged.

## Verified operation

- Service: active/running, enabled at boot, zero automatic restarts at check time.
- Installed and repository controller SHA-256:
  `64ce0dcd215d06b1f1eef4165c00d00b0f222c81499083992085fc1a474e3805`.
- Startup began in firmware automatic mode at approximately 5,500 RPM.
- CPU temperature reached 50 C during startup, interrupting the required
  30 continuous seconds below 50 C (also requiring GPU below 52 C and all
  monitored SMC channels at least 4 C below their configured cutoffs).
- After qualifying, the controller entered manual mode and gradually lowered
  the target. This explains why enabling startup did not immediately quiet
  the fan. Quieter operation was reported after the target fell.

## Follow-up observation

The accompanying `post-reboot-thermal-check-20260926.json` contains 21 samples
at approximately three-second intervals over one minute, reading all 31 exposed
temperature inputs and the fan input/target/manual attributes. Sysfs temperature
values in this file are millidegrees Celsius; fan values are RPM.

| Reading | Observed range |
| --- | --- |
| CPU cores, combined | 38–46 C |
| CPU diode TC0D | 38.25–43.5 C |
| Independent GPU | 48–50 C |
| PSU-labelled Tp0C | 55–55.75 C |
| Memory-proximity TM0P/TM0p | 36.75–37.5 C |
| Fan actual | 3,006–3,625 RPM |
| Fan target | 3,000–3,625 RPM |
| Manual mode | 1 throughout |

No read errors occurred. The seven constant G-suffixed SMC channels retained
their previous values; their physical interpretation remains unresolved.
This short observation shows temperature-responsive control without observed
thermal runaway. It does not establish long-term safety or explain the
firmware behavior. The controller still lacks the audit's proposed unexplained-
maximum latch and critical-temperature shutdown path; no such changes were made.

## Firmware-side findings

- Firmware and EFI boot information were inspected without changing settings.
  Machine-specific boot entries and firmware inventory are excluded.
- This boot's kernel log showed successful applesmc initialization and no
  SMC communication/read failure. Its deprecated hwmon registration message
  concerns the driver API; it does not identify a failed thermal sensor.
- Earlier firmware-stage loud-fan behavior remains reported. Linux
  measurements do not retroactively measure exact preboot RPM.
- While this controller owns fan targets, those targets cannot independently
  reveal the SMC's automatic cooling demand. No raw key-index scan was repeated
  alongside the running controller, and no undocumented fault flags were cleared.

## Remaining non-invasive options

NVRAM reset is optional firmware-state troubleshooting, not an established fix
for this fault. Apple describes NVRAM as storing settings including startup-disk
selection; it describes thermal/fan management as an SMC responsibility. A reset
could therefore require restoring Linux boot selection. No NVRAM reset, firmware
flash, further reboot or new fan-control experiment was performed in this check.

The model's original guide identifies Apple Hardware Test: start with D held;
if unavailable, it points to the original Applications Install DVD. Installing
Linux may have removed the disk-resident test. Availability is not verified,
and no diagnostic suite was run. A test would require leaving Linux, so it
cannot run while preserving uninterrupted operation of this Linux service.

Sources checked 2026-09-26; concise findings above are retained for offline use:

- [Apple: reset NVRAM](https://support.apple.com/en-us/102539)
- [Apple: SMC responsibilities and reset](https://support.apple.com/en-us/102605)
- [Mid-2010 Mac mini user guide, page 50: Apple Hardware Test](https://cdsassets.apple.com/live/6GJYWVAV/user/ma1538_mac_mini_mid2010_user_guide.pdf#page=50)

Current operating decision: keep the existing service running and enabled as
requested. Diagnostic conclusion remains unresolved hardware/SMC behavior,
with no demonstrated failed component and no certification of hardware safety.

Repository validation before publication: `pnpm run build` passed all 35
simulation tests, and `systemd-analyze verify macmini-thermal-guard.service`
passed. These checks did not restart or modify the installed service.
