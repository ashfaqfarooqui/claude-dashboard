# scenario-weaver remediation — master tracker

Audit of `/home/ashfaqf/playground/synergies/ScenarioGenerationWorkspace/main` at commit
`a86466c` (branch `fix/openscenario-rs-catalog-locations`). Three parallel audits
(solver, exporters/IO, tests/build), cross-verified against source.

**Baseline as audited:** builds clean; 370 tests pass in ~100 s; production-lib clippy
essentially quiet; **and the core physics encoding has three critical soundness defects.**
The suite does not catch them because it largely exercises code the product never runs.

Read `FINDINGS.md` for the full evidence. Read `AGENT_PROMPT.md` before starting any issue.

## Status

| ID | Status | Agent | Notes |
|---|---|---|---|
| SW-01 | ☑ done | | scoped down by D1 — deps + README only; publish/merge deferred |
| SW-02 | ☑ done | | **superseded by D2** — `scripts/check.sh`, not a workflow |
| SW-03 | ☑ done | | fcd9dd8 — 4 tracked failures created |
| SW-04 | ☑ done | | b39e162 — 999.0 sentinel now unrepresentable |
| SW-05 | ☑ done | | f34c31c — XSD validation; found 2 SW-16 defects |
| SW-06 | ☑ done | | 21a09d4 — invariants at 1e-6; kinematics fails 21/21 |
| SW-07 | ☑ done | | b511921 — insta snapshots + proptest landed; XSD helpers deduped |
| SW-08 | ☑ done | | ec46ebc — exact rationals, lane centres 1.75/5.25, trapezoidal position update |
| SW-09 | ☑ done | | 4de6d29 — pedestrian.rs wired in; 234 kinematics breaches -> 0; Kinematics off the baseline |
| SW-10 | ☑ done | | a562508 — lane derived from `py` (444 bad steps -> 70, all pedestrians); min_distance lane-guarded; 2 criteria re-attributed to SW-12 |
| SW-11 | ☑ done | | bb12413 — Route B-lin per D3; θ/δ real and still QF_LRA (guards, not Bool selectors); H4 + H5 fixed; `min_turn_radius` uses `tan` and has 2 callers; clippy baseline 62 -> 60 |
| SW-12 | ☑ done | | cf01661 — forward progress, `Ahead` antisymmetry, strict violate mode, pedestrian octagon, DSL ranges; all 6 inherited items closed. **2 of 6 base items only partly delivered — jerk and the cut_in_left TTC, both now [SW-22](SW-22-ttc-non-vacuity.md)** |
| SW-13 | ☑ done | | adbb9a4 — `imports:` live, `--optimize` honoured for n>1, UNKNOWN no longer reported as UNSAT |
| SW-14 | ☑ done | | 894409b — both TTC targets now optimise TTC via a constant-level ladder (still LRA); objectives routed through `encode_same_lane_constraint`; cross-coordinate `min-ttc` gap 3.00 vs 32.49 → identical to 1e-14. Raised SW-26; `MinimizeSeverity` rename left undone (fenced) |
| SW-21 | ☑ done | | 669633d — `deny_unknown_fields` + typed `constraint_modes` errors; `min_velocity` default settled as `Enforce` (M7); `KNOWN_BROKEN_EXAMPLES` now empty |
| SW-15 | ☑ done | | 3e14fb3 — `LanePosition` everywhere, explicit revision, documented dims; new shared `scenario/lane_ids.rs` + cross-artifact drift test |
| SW-16 | ☑ done | | 971f519 — lane ids validated, trajectory-driven road extent + sidewalks, roadMark/type. **`Containment` NOT retired** — residual is solver-side, now [SW-23](SW-23-pedestrian-containment.md) |
| SW-17 | ☑ done | | 2c7fb00 — real objects/frames joinable to the `.xosc` by name (D4 Route A); **lane-change tag was inverted**; fabricated metadata gone. **Closes wave 4.** |
| SW-18 | ☑ done | | fcf6f74 — shared palette/`Projection`; **`classify_actor` was matching the actor *id*, not the role**. `ActorRole` typing blocked → SW-19, edit set recorded on the SW-18 doc |
| SW-22 | ☑ done | | 0e62dc1 — `cut_in_conflict` makes the cut-in a conflict, not just a lane change; **`KNOWN_BROKEN_INVARIANTS` now empty**; corpus net *faster*. M5 jerk deferred, hypothesis disproved. Raised SW-27, SW-28 |
| SW-23 | ☑ done | | dfb58a1 — per-step pedestrian `py` bound; **`Invariant::Containment` retired**; surfaced SW-24 + SW-25 |
| SW-24 | ☑ done | | 2357e2e — calls SW-23's `encode_pedestrian_lateral_containment` from the bicycle path; `py` 9.28 → within [1.75, 7.02]; both `pedestrian_physics_test.rs` skips retired |
| SW-30 | ☑ done | | 05b8c99 — `LateralDistanceGT` lowered non-strictly, SW-12's fix in the one proposition SW-12 skipped; violate now lands strictly inside the threshold. Doc's "zero corpus coverage" was wrong *and* its instinct right: `multi_lane_safety.yaml` covers the field but no corpus example **can** isolate the boundary. Raised SW-31, SW-32 |
| SW-29 | ☑ done | | 1a94942 — `LTLGenerator::generate` now calls `spec.validate()`; three UNSAT assertions converted to validation-message assertions; horizon predicate shared between `types.rs` and `encoder_utils.rs` (the `cartesian.rs` copy is fenced, still a literal) |
| SW-27 | ☑ done | | 3967332 — `same_lane_f64` + `LANE_OVERLAP_EPS`; exact side unchanged, `f64` side taught to reproduce it; proptest filter retired, **all six invariants live**. Raised SW-30 |
| SW-28 | ☑ done | | 3566c2e — `ScenarioSpec::validate` rejects a cut-in whose NPC target lane is not the ego's, reusing the loop's existing `current_lane` rather than a third copy of the merge arithmetic. Two fixtures tripped it, both papering over the degeneracy; `bidirectional_test` got `min_distance` back to `enforce`. Rest of the corpus already conformed |
| SW-26 | ☑ done | | 74c4f24 — **docs only, deliberately.** 100% of the growth is inside Z3's `check()`, not construction (2–8 ms at every horizon). The objective's term count is not the cause (1.26×). `Optimize` is 3–11× slower than `Solver` on a byte-identical constraint set, and the optimality *proof* is the work. Four alternatives measured and refuted. Raised SW-36 |
| SW-31 | ☑ done | | c6ebe91 — audit table of every `Proposition` (encoded vs measured) now lives on `compute_validation_metrics`; velocity fields measured for the first time; pedestrian pairs measured against the box the encoder actually asserts. **`unsafe_following.yaml` and `speed_limit_violation.yaml` — adversarial examples — reported `all_constraints_satisfied: true` pre-fix.** Raised SW-33/34/35 · [doc](SW-31-unmeasured-constraints.md) |
| SW-32 | ☑ done | | c5e5362 — `PedestrianCrossingModel::generate_safety` now lowers `min_lateral_distance` through the same `push_constraint` the default path uses. Route 1 (honour) chosen on measured evidence: `LateralDistanceGT` closes the gap the box's disjunction leaves open rather than fighting it. My own doc's "reported as satisfied" was wrong — see the log | · [doc](SW-32-pedestrian-ignores-lateral-distance.md)
| SW-33 | ☑ done | | 2967c90 — both pedestrian constraints now go through `push_constraint`, so `Violate`/`Ignore` mean what they mean everywhere else. Found and fixed a **fourth** instance of the boundary defect in `RectangularDistanceGT` while checking the negation was not vacuous |
| SW-34 | ☑ done | | e1be1ce — box ratios hoisted to `pub(crate)` divisor constants, imported by the validator. Kept as **divisors** deliberately: `x / 1.5` and `x * (1.0/1.5)` are not bit-identical |
| SW-35 | ☑ done | | cb3b218 — `PedestrianTTCGT` non-strict at its boundary. Third instance of the SW-12/SW-30 defect; the guarded-implication case was derived, not assumed |
| SW-36 | ☐ new | | **raised by SW-26** — solve time depends on the *exact rational value* of `time_step`, not just the step count: 64 steps at `0.16` took 26.4 s; 64 steps at `10/63` took **225 s**, 8.5× on the same problem size. Interacts with SW-08's exact `f64→Real` conversion (long denominators). sonnet |
| SW-37 | ☑ done | | 002265a / 405a974 — **two sign points, not one**: `vx` *and* `ax` (the bicycle `accelerations` array is `dv/dt` for the unsigned `speed_v`, so signing `vx` alone left the two mutually inconsistent). New example `head_on_near_miss_bicycle.yaml` closes the corpus gap. Pre-fix failure reproduced at `002265a`: bicycle closing speed **2** vs cartesian **18**. Was — `BicycleEncoder::get_longitudinal_vel` returns raw unsigned `speed_v`, unflipped by `actor.direction`, while `encode_kinematics` *does* flip position updates by direction. So the shared `encode_ttc_constraint` / `directed_conflict` / `encode_approaching` (all reached via `EncoderAccessor`) compute relative velocity **wrong** for a bicycle actor with `direction: -1`. Latent: no example combines bicycle + `direction: -1` — which is exactly why no test catches it. sonnet |
| SW-38 | ☑ done | | `2ea9dab` — bicycle's lane-change `direction:` is now actor-relative, matching cartesian. See the section below. |
| ~~SW-38 (original note)~~ | ☑ | | **was deferred by SW-20** — the lane-change transition dedup. SW-11 already unified two of the three divergences (ratio constant, rational precision); the third is semantic: cartesian flips Right/Left for backward actors, bicycle does not. Resolving it either way is a behaviour change, not cleanup, and the two have also diverged structurally (symbolic `Int` lanes vs bicycle's deliberately concrete lane index, for solver performance). Needs a decision, not a refactor. sonnet |
| SW-39 | ☑ done | | **raised by SW-37, verified independently** — in `head_on` scenarios the oncoming actor's `vx` decays monotonically to exactly `0.0` and stays there. Reproduced on the shipped **cartesian** `head_on_near_miss.yaml` (`[-10.0, -9.5, … -0.5, 0.0]`), so it predates SW-37 and is a property of the scenario model, not the bicycle encoder. **SW-37's guess at the cause was wrong and has been corrected** (it blamed `HeadOnModel::generate_safety`): the real cause is `encode_forward_progress` (`src/solver/encoder.rs:210`), whose only floor is a *total-displacement* one — `MIN_FORWARD_PROGRESS_FRACTION = 0.5`, so `|x[H]-x[0]| >= 0.5*speed.min()*duration` = 50 m here. The observed series integrates to exactly -50.0 m: the solver rides the bound. Nothing couples a later step's speed to the declared `speed:` (an initial condition since SW-11/H4), so monotone decay to zero is the cheapest satisfying assignment. This is **general**, not head-on-specific. Spec written: `SW-39-oncoming-coast-to-standstill.md`. An oncoming vehicle that coasts to a dead stop is not a near-miss. sonnet | **Landed `1bce284` / `130fd8c`** (+ `1d015b4`, `82020a3`) — terminal-speed floor. See the section below. |
| SW-40 | ☑ done | 76dd7e8 | **the terminal-speed floor forbade a legitimate stop, and the recorded fix was unimplementable.** `MASTER.md` recommended a soft cost under `Optimize`; only the four `cut_in_left_optimize_*.yaml` reach `OptimizerBackend`, and both examples exhibiting the defect run on the plain `SolverBackend`, which has `assert`/`check`/`get_model` and no objective at all — a soft cost would have left them bit-identical. Split into (A) the over-constraint, fixed, and (B) "Z3 rides the bound", declared not-a-defect: a plain `Solver` returns *some* feasible point and has no notion of "prefer". (A) reproduced, not refuted: an ego with `acceleration: [-5.0, -1.9]` sheds ≥1.9 m/s² at every step and reaches the horizon at ≤1 m/s, so the 10 m/s terminal floor made it UNSAT — while the SW-12 displacement floor accepted the same trajectory (100 m covered against 100 m required). The floor is now emitted only when `speed.max() + a_along_max * duration >= TERMINAL_SPEED_FRACTION * speed.min()`, evaluated on spec constants at encode time, so QF_LRA is untouched and no corpus actor is affected (every one has `acceleration.max() > 0`). |
| SW-41 | ☑ done | | `0a72391` / `6e8113b` — the strictness sweep. Fifth and sixth instances of the family found and fixed (`VelocityGT`, `VelocityLT`); the invariant is now pinned for every proposition by an exhaustive match with no wildcard arm. See the section below and `SW-41-strictness-sweep.md`. |
| SW-42 | ☑ done | | `ab81908` / `82f050b`. | **raised by SW-41; this row's original framing was wrong and is superseded by `SW-42-unmeasured-propositions.md`.** I had written "four propositions have no validator check — measure them or delete the two dead ones", from SW-41's report, without checking it. Two errors: (a) `OnSidewalk`/`CrossingRoad` are **live** (`pedestrian_crossing.rs:230,235`) and are `eventually()` **goals**, not spec thresholds, so a threshold check is the wrong shape for them; (b) there are **four** unemitted propositions, not two — `metrics.rs:105` already records `OnLeftOf`/`OnRightOf` alongside `Distance2DGT`/`ManhattanDistanceGT`. Also: SW-31 already *deliberately* deprioritised **measuring** unemitted propositions; that decision does not settle whether they should still **exist**. The real job is two independent halves — delete the four dead variants, and close the genuine gap: `pedestrian_crossing.rs:243` asserts the pedestrian eventually reaches the opposite sidewalk and **nothing confirms the shipped trajectory crosses**; the containment invariant only bounds `py` to an envelope, which a pedestrian that never leaves its kerb satisfies. Same shape as SW-39. sonnet |
| SW-25 | ☑ done | | 93f2ab2 — a *discarded* lane-change window left its steps with no lateral constraint at all, so SW-10's bracket was never evaluated; lateral encoding is now total. Corpus byte-identical. Raised SW-29 |
| SW-19 | ☑ done | | 3c7fb15 / 45bb6a1 / f98cafe — three commits. Split (`encoder.rs` 4286 → 1015, 539 non-test), then `ActorTrajectory::role: String → ActorRole`, then `ConstraintModes::Shorthand(String) → ConstraintShorthand`. **Snapshots byte-identical, zero test assertions edited in the split** |
| SW-20 | ☑ done | | 18a9619 / ab02754 / 0b591ba / ceaec17 / 896f014 — five commits. Dead TTC/distance pair deleted (**H7 checked first: the dead code was behind the live path on every axis, not ahead of it**), initial-conditions marshalling shared, trait doc corrected, `lane_ids` adopted, and `LanePosition`'s `s` fixed. **Clippy ratchet tightened 60 → 59.** Lane-change dedup deliberately skipped → SW-38 |

| SW-50 | ☑ done | opus | `a9ffb6b` — **Route A, and the doc's Route B was refuted by measurement: `HeadOnModel::generate_safety` identifies only the *oncoming* actor, so the `slow_npc` half of the issue was unreachable from that hook.** Corpus instrumentation found the drift in **16 of 19** vehicle examples (worst: `simple_bidirectional` ego +129%, `cut_in_right` ego +141%) — general, as suspected. Landed as opt-in `behavior.speed_retention: <fraction>` (floor *and* ceiling in one field) rather than a new `ActorSpec` field, because a struct field would have forced edits to the three fenced encoder files. 17 non-head-on examples numerically unchanged, no snapshot re-baseline. Raised: audit the other 16 for band drift. |
| SW-50 (original diagnosis) | ☑ | | **raised by SW-49, reproduced 2026-09-09 at `2c7c8fc`** — `speed:` is an initial condition only, so nothing holds an actor to its declared band between step 1 and H−1. `head_on_near_miss`'s `oncoming_npc` decays 12 → 4.1 m/s and steps back to exactly −5.0 at the horizon (= `TERMINAL_SPEED_FRACTION × speed.min()`), riding SW-40's terminal bound; and `slow_npc`, declared `[6.0, 8.0]`, reaches **13.5 m/s** — faster than the ego — so the overtake is enforced but its motivation has evaporated. General, not head-on-specific; same shape as SW-39. Must NOT widen SW-40's terminal floor to every step (that comment is a recorded decision). · [doc](SW-50-head-on-oncoming-speed-retention.md) |
| SW-51 | ☑ done | opus | `6d502a7` — `min_lateral_distance` on a pedestrian crossing is now guarded on longitudinal relevance, lowered as `RectangularDistanceGT { threshold_x: W, threshold_y: d }` rather than a bare `LateralDistanceGT`. `W = max(min_ttc × ego.speed.max(), min_distance / PEDESTRIAN_BOX_LONGITUDINAL_DIVISOR)`. **`2.0` went from UNSAT-by-construction to SAT**, and SAT at both `dt=0.30` and `dt=0.15` — the sampling dependence is gone. No new `Proposition` variant: the implication *is* the box's disjunction, so it inherits SW-33's boundary fix. Validator branches on `pedestrian_pair` and measures the guarded property. Suite 471/7, no snapshot re-baseline. | **raised by SW-45/46; MASTER's own "geometry, not a bug" verdict deliberately revisited** — `min_lateral_distance` is lowered *unguarded* under `Always` (`pedestrian_crossing.rs:157`), but a crossing pedestrian must traverse `py_ego`, so the constraint holds only by sampling artifact: `d_max ≈ (v_ped × time_step)/2`. Halve `time_step` and the same spec goes UNSAT; any physically meaningful value (2.0 m, the same order as the `min_distance` beside it) is UNSAT by construction. SW-32 traded "silently dropped" for "loudly impossible". Fix is to guard on longitudinal relevance — `\|dx\| <= W ⟹ \|dy\| >= d` — which is the shape the box next door already has. Watch the strictness family: `¬(A ⟹ B)` = `A ∧ ¬B`, so `Violate` must be proved non-vacuous. · [doc](SW-51-lateral-distance-unguarded-for-crossing.md) |
| pedestrian mid-road dwell | ⊘ won't fix | | **raised by SW-45/46, closed 2026-09-09 by the user.** Dwelling mid-crossing is real pedestrian behaviour, and the DSL already lets an author *request* it: `behavior.walking_mode: hesitate` is live and enforced (`pedestrian_crossing.rs:456-490`, a disjunction over the middle 40–60% of the horizon). A monotone-forward-progress constraint would forbid the one mode that exists to express it. Not a defect. |
| SW-57 | ☑ done | sonnet | `35f5596` on `fix/openscenario-rs-bump` — all 5 known errors fixed plus 3 more of the same class found once the lib compiled, all confined to `xosc_exporter.rs`. `clippy --lib --bins` back to 59 (resolves L11). Verified independently. Raised **SW-59** — one more break, different file, different type. |
| SW-59 | ☑ done | sonnet | `a34c593` on `fix/openscenario-rs-bump` — enum-choice walk rewritten, exactly per the issue. Verified independently: `cargo check --all-targets` 0 errors, gate `PASS`, `cargo nextest run` 483/7 (zero delta from baseline). **Closes the SW-57/58/59 cluster — the branch is gate-clean against openscenario-rs HEAD.** |
| SW-58 | ☑ done | sonnet | `c109d0c` on `fix/openscenario-rs-bump` — path fixed to relative form, branch cut off `main`, `main` clean (only pre-existing unrelated `README.md` diff remains). Verified independently: `cargo check` on the branch resolves the path dep and fails only at the 3 known SW-57 sites. · [doc](SW-58-path-dep-absolute-and-on-main.md) |

Legend: ☐ todo/ready · ◐ in progress · ☑ done · ⊘ blocked (on an open issue holding a shared file)

---

## Decisions taken (2026-08-31)

All four open decisions are resolved. **Where a decision contradicts an SW doc, the decision
wins** — SW-11 and SW-17 in particular still contain the superseded recommendation, so any
agent handed those docs must also be handed the decision.

1. **D1 / SW-01 — the path dependency stays.** `openscenario-rs` is consumed from
   `../../Workspace_OpenScenario-rs/main` while the two crates are developed and tested
   together before publishing. SW-01 was scoped down to removing the unused `nalgebra` and
   `pretty_assertions` deps and fixing `README.md`; the reason and the exit (publish 0.3.3 →
   restore the version dep → merge) are recorded in `Cargo.toml` beside the dependency.
   **Merge to `main` stays deferred** — a path dependency must not reach `main`.
2. **D2 / SW-02 — no workflow; `scripts/check.sh` instead.** A cloud runner cannot resolve a
   path dependency. The script gates on fmt, a clippy ratchet, and the suite.
   Note the audit's "production lib is nearly clean (62 warnings)" means 62, not zero — the lib
   clippy step is a **ratchet against a baseline of 62**, not a `-D warnings` gate. Burn-down
   deferred to wave 5, since 23 of the 62 are cast lints SW-08 rewrites anyway.
3. **D3 / SW-11 — implement, in LRA. Do NOT delete the bicycle model.**
   θ and δ are decorative *by design*: the whole encoding is deliberately confined to QF_LRA
   (`docs/z3_constraints.md:17-19`; `cartesian.rs` "Eliminates QF_NRA … 10-20x speedup";
   `bicycle.rs` header "hybrid LRA approach"; every multiplication in `src/solver/` is
   constant × variable). SW-11's Route B as written is variable × variable, which with the Int
   lane variable lands in **QF_NIRA — no decision procedure** — and Z3's `Optimize` (the entire
   `--optimize` feature) has essentially no support for nonlinear objectives. So implement θ for
   real via a **constant reference speed plus Bool-selected speed buckets**, staying in LRA.
   H4 (the `speed.max()` ceiling and forced constant acceleration) and H5 (the empty lateral
   velocity bound) are fixed unconditionally.
4. **D4 / SW-17 — Route A**, emit real OpenLABEL objects and frames so the `.ol.json` joins to
   the `.xosc` by entity name.
5. **D5 / SW-57, SW-58 (2026-09-22) — the `openscenario-rs` path dependency floats at HEAD, no
   commit pinned.** `openscenario-rs` HEAD (`4a84dcc`, branch `campaign/OSS-01`) is 81 commits
   past its own `v0.4.2` tag and unpublished (Finding M18). Asked the user whether to pin to the
   exact commit, block on a real publish, or accept the same floating-HEAD arrangement D1 already
   accepted once before **0.4.0** was published — chose the third. Do not add commit-pinning
   machinery to SW-57/SW-58; re-derive from a fresh `git log` in the sibling checkout if a build
   ever needs to be reproduced later.

Full execution plan, including these deltas:
`/home/ashfaqf/.claude/plans/you-have-written-a-shimmying-mochi.md`

---

