# Repository privacy

Published files and their reachable Git history contain generic model-specific
research, controller code, and anonymized thermal measurements. Personal incident
narratives, location, unrelated projects and applications, local account paths,
and machine-specific boot/firmware inventory are excluded. Exact observation
timestamps are replaced with elapsed seconds; record dates and measurement values
remain available for interpreting the experiments.

Public manufacturer model identifiers, sensor labels, standard Linux sysfs paths,
and source citations are retained. These describe the supported hardware and
measurement method, not unique device identities. SHA-256 references are updated
when the corresponding evidence is anonymized.

## Intentional authorship exception

Git author and committer names/email addresses and identity-bearing GPG
signatures are retained by explicit choice. The hosting account also identifies
the publisher. This is not an anonymous repository. Private signing keys are
never included in repository files.

## Local diagnostic data

Raw inventories, broad journals, SMC dumps, superseded local source backups and
a recovery bundle are retained in a private archive outside the repository.
Do not copy them into a commit. An ignore rule prevents accidental staging; it
does not sanitize file contents or protect a file already tracked by Git.

References to raw diagnostic artifacts in the historical audit describe that
private archive. Only the reviewed report, aggregate summary and anonymized
sample series are published.

## Validation and limits

The privacy review checked every file version in all five pre-cleanup commits
for known local identities, personal context, account paths, email addresses,
network addresses, device UUIDs, recognizable credential formats and private-key
blocks. All rewritten commits were signed and their signatures verified.
Controller source, tests and service-unit contents were compared byte-for-byte
with the preceding revision and preserved. A pattern scan cannot prove the
absence of every possible secret format; manually review new evidence before
publishing it.

History rewriting changes commit IDs. Old clones, forks and hosting-provider
caches can retain earlier copies even after the cleaned branch is pushed.
Use a fresh clone after a privacy rewrite; do not merge the old history back.
[GitHub's guidance on removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
explains the limits and the support process for cached copies.
