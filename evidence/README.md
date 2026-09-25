# Measurement and validation records

These files preserve observations from one Macmini4,1 during development.
They are historical records, not the current service status or a guarantee
of long-term hardware safety. Earlier trials used different policies and
idle floors; see the main README and research reference for that history.

- `initial-probes.log`, `lower-speed-probes.log`, and `../observation.json`:
  initial supervised speed trials.
- `controller-and-watchdog.log`: controller and independent rollback checks.
- `idle-floor-*.jsonl`: staged lower-floor observations.
- `load-steps-observation.jsonl`: later stepped-policy observation, including
  one deliberate service restart while updating the temperature response.
- `final-verification.json`: the final recorded service check at that time.
- `final-build.log`: latest saved test result.

Build logs use `<project>` instead of local project paths.
Local `before-*` code backup directories are excluded from Git; the repository
tracks the current implementation and subsequent changes instead.
