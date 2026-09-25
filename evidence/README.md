# Measurement and validation records

These files preserve observations from one Macmini4,1 during development.
They are historical records, not the current service status or a guarantee
of long-term hardware safety. Earlier trials used different policies and
idle floors; see the main README and research reference for that history.

The [thermal audit](thermal-audit-20260925T1705Z/REPORT.md) records its historical
end state: controller stopped and boot-disabled, underlying cause unresolved.
A subsequent operating decision resumed the unchanged service and enabled
startup. See [the post-reboot check](POST-REBOOT-CHECK-20260926.md) for that
verified operating state; it does not overturn the audit's safety findings.

The published audit includes its report, numerical summary and temperature/RPM
samples. Raw machine inventories, broad journals and SMC key dumps are archived outside
the repository
because they can contain identifiers or unrelated host information. References
to those local artifacts in the report are not all available in a fresh clone.

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
