# ADR 0014: Bounded local optimization jobs and process-tree ownership

Status: accepted for M05B before job execution or measured HTTP workflows.

Extend the existing local API with an in-memory job registry. All jobs belong to
the single configured authenticated local user and this application lifetime.
Opaque random128-bit IDs identify jobs; they are not authorization credentials.
Any holder of the configured Bearer token can inspect/cancel any job. Do not store
credentials, request headers or protected ML data in job records. No persistence,
multi-user identity, database, queue service or deployment is introduced.

Use one fixed supervisor thread, one active job and two FIFO waiting entries.
Submission briefly uses the existing two M05A request slots to read and validate
input in its existing guarded worker. Background jobs never occupy those slots.
Run whole jobs in a separate guarded process, reusing unchanged M03B/M04 engines
and their guarded native optimizer child. No task or supervisor thread per job.
Reserve at most2MiB result capacity per admitted job; retained plus reserved bytes
must stay within8MiB. Store at most32 records; reject admission when any cap is full.
Never evict active/waiting work or an unexpired retained result to admit new work.

Freeze defaults in packaged default_job_limits.json. Preserve all M05A transport
limits,32 orders/96 stages/64 changes, two sync slots,256MiB/5s sync worker budget.
Job wall watchdog15s, outer Windows aggregate memory768MiB; inner optimizer512MiB/5s.
On Linux the existing per-process RLIMIT_AS limits bound outer768 + inner512MiB
address space, rather than claiming an aggregate Windows-style memory measurement.
Allow at most four Windows processes (two virtual-environment launcher/interpreter
pairs) in the outer job; existing single-worker guards retain their two-process cap.
Linux outer jobs start their own session; a stop kills the entire process group.
Suspended Windows launch, hard-guard membership checks and kill-on-close remain.

M03C found all18 small one-second runs proved optimal, while medium one-second
outcomes included missing/worse incumbents and large cases were mostly UNKNOWN.
Choose seed42, one solver worker,1s wall and1 internal deterministic unit per phase;
2,000 alternatives/6,000 variables/15,000 constraints and96 operations. These are
conservative local software budgets, not production scalability guarantees.
Scheduling jobs use that fixed configuration. Scenario jobs retain M04's explicit
greedy/optional CP request; reject requested budgets above this envelope rather
than rewriting a specification/fingerprint or changing M04 defaults silently.

QUEUED -> RUNNING -> SUCCEEDED/FAILED/CANCELLED. Queued cancellation is immediate;
RUNNING cancellation sets a flag and reports cleanup pending until the native tree
has been killed/reaped. The same registry lock orders races: accepted cancellation
before terminal publication wins; a prior terminal publication remains unchanged.
Completed cancellation is idempotent, never changes an already succeeded result.
Do not release the active lease or result reservation before native cleanup.
Queued work expires after30s. Terminal records expire after300s, discard result
bytes and become EXPIRED; tombstones remain for300s, then disappear. Cleanup is lazy
on requests and at fixed supervisor wakeups. On restart all old IDs return404.

Reuse whole-stage-minute-v1, exact Decimal/parsers, atomic transformations, objective
order, independent verification, UNKNOWN/FEASIBLE/OPTIMAL evidence and strict-better
selection. Nested optimizer failures/watchdogs retain verified greedy through M04.
A whole-job stop with no completed verified report fails explicitly; never invent
a fallback. Cancellation publishes no successful result, even if solving just ended.
Progress is only queued/startup/worker-running/cleanup/terminal, never percent or
an unobserved solver phase. Strip exception/native diagnostic text at the API edge.

Normal lifespan shutdown closes admission, cancels waiting/active jobs and joins
the supervisor after native cleanup. Client disconnection after admission does not
cancel jobs; DELETE is explicit. No durable/crash-recovery or Linux orphan cleanup
after an abrupt server death is promised. Support one process, without reload,
reverse proxy or public/multiworker hosting. M06 remains separately scoped.

References: [M03C observations](../experiments/M03C-solver-scalability.md),
[Windows nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs),
[Python subprocess timeouts](https://docs.python.org/3.13/library/subprocess.html#subprocess.Popen.communicate).
