# ADR 0018: Offline compatibility assessment without capacity conversion

Status: accepted for M07B before implementation.

M01's B_RF-01 predicts an unresolved historical team/department productivity
quantity. M02's efficiency is an explicit fraction of standard worker-minute
capacity for a dedicated qualified crew, stage and assignment. Neither matching
ratio values nor sewing/finishing names establish compatible units or entities.
Existing EXP-003 validation gains and EXP-004/005 retrospective errors do not
establish operational calibration or transport to hypothetical planning inputs.

Add a separate `loometric.compatibility` offline package. Its frozen typed version-1
assessment consumes a declared prediction context, integrity-checked M01 metadata,
an unchanged typed scheduling instance and explicit assignment/order references.
Return deterministic mapping statuses/reason codes and mandatory readiness gates,
with request, model/data/split and planning fingerprints. No prediction, training,
capacity calculation, scheduling, HTTP route or scenario mutation occurs here.

Distinguish syntactic compatibility from semantic readiness. COMPATIBLE is allowed
for individual proven structural checks, such as matching declared dates. Overall
M01-to-capacity integration remains INSUFFICIENT_EVIDENCE, or INCOMPATIBLE for
concrete mismatches. Target-to-efficiency conversion is BLOCKED in this version,
and overall READY/COMPATIBLE cannot be unlocked by caller-supplied references.
References are review leads, not authenticated source-owner evidence. Changing
this scientific policy requires a separately reviewed contract/version decision.
All reports explicitly forbid applying a prediction or replacing efficiency.

Inspect trusted local artifact manifests and binary digests without unpickling or
executing a model. Use a separately retained expected manifest fingerprint. Hashes
prove integrity relative to that receipt, not authenticity or semantic correctness.
Keep optional ML imports outside the pure assessment package's import path.

Outer-validation artifacts contain aggregate reports, not saved prediction rows.
Reuse EXP-004's saved inner evaluation rows, clearly labeled original-training OOF.
For inspection, verify the saved file digest and use M01's training-only source
loader plus EXP-005's existing population/parameter/metric checks. Reuse existing
error summaries; never refit, rerun prediction or consume outer labels. No new
performance experiment or model selection is introduced. Preserve all prior reports,
artifacts, split bytes, features, environment pins and final-test policy.

Alternatives rejected: direct ratio substitution or clipping changes scientific
meaning; accepting evidence strings as verified approval fabricates readiness;
duplicating the experiment/model pipeline risks holdout use; a serving or storage
layer exceeds this task. Costs are intentionally blocked conversion, explicit
local artifact requirements and continued need for owner-approved units, timing,
crew/grain mappings, independent quality and uncertainty/rollback evidence.
M08 architecture is documentation only; no automatic ML-driven planning starts.
