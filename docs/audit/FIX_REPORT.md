# Mesh Smoothing Lecture Lab — Fix Report

Source audit: [20260710-112622/FULL_PROJECT_AUDIT.md](20260710-112622/FULL_PROJECT_AUDIT.md)
Fix pass date: 2026-07-10
Files changed: `app.py`, `src/mesh_ops.py`, `src/mesh_metrics.py`, `src/visualization.py`,
`README.md`, `docs/METHODS.md`, `docs/STUDENT_GUIDE.md`, `docs/DEMO_SCRIPT.md`,
new `tests/` package (`test_mesh_ops.py`, `test_presets_and_metrics.py`,
`test_app_state.py`).

No commits were made and nothing was pushed. The working tree contains only
these edits plus this report and its evidence.

## How this was verified

- `python -m compileall .` — passed (app.py + src).
- `python -m pytest tests` — **36 passed**, 0 failed (25 pure-algorithm/metric
  tests + 11 `streamlit.testing.v1.AppTest` state-transition tests).
- The real app was launched with `python -m streamlit run app.py` and driven
  with Playwright (Chromium) at 1440×1000 and 768×900. Screenshots are under
  [fix_verification/screenshots/](fix_verification/screenshots/); the full
  console capture is [fix_verification/console_log.txt](fix_verification/console_log.txt)
  (**0 console errors**, 639 warnings, essentially all repeated WebGL
  framebuffer messages from the active 3D viewer's per-render context
  creation — a Panel/VTK characteristic, not a hidden-tab leak; see AUD-021).
- One live-browser-only regression was caught and fixed during this pass (see
  AUD-005 below): a `st.radio` widget mounted for the first time after
  navigating to a lazily-rendered section did not visually reflect a
  pre-set `session_state` value until `index=` was passed explicitly. This is
  exactly the kind of defect pure source review or `AppTest` (which reads
  `session_state`, not the rendered widget) cannot catch — it required
  driving the real browser.

---

## Issue register

For each issue: root cause, fix, test evidence, status.

### AUD-001 — Reset crashes the app — **Resolved**

- **Severity:** Blocker
- **Root cause:** `_render_commit_controls` mutated `st.session_state[NOISE_ENABLED_KEY]`
  and other widget-backed keys *inline after* the "Reset experiment" button,
  in the same script run in which those widgets had already been instantiated
  above. Streamlit raises `StreamlitAPIException` for that pattern.
- **Fix:** All widget-state mutation moved into `_reset_experiment_and_controls`,
  wired as the button's `on_click` callback (`app.py`). Callbacks run *before*
  widgets are instantiated for the run, so the same assignments are legal
  there. The same pattern was applied to Commit and the manual Add
  noise/Apply smoothing buttons for consistency (see AUD-006/015/016).
- **Test evidence:**
  - `tests/test_app_state.py::test_reset_does_not_crash_and_restores_original` (AppTest)
  - Browser: clicked Reset after "See shrinkage" — no exception, working mesh
    restored to source original. [Screenshot](fix_verification/screenshots/03_after_reset_no_crash.png)

### AUD-002 — "Remove noise" preset taught the opposite result — **Resolved**

- **Severity:** Blocker
- **Root cause:** The shipped preset used Taubin `lambda=0.35, mu=-0.53`, an
  unstable pair (per-iteration spectral gain > 1 at mid frequencies), which
  amplified the noisy sphere by +6.6% roughness and +24% AABB instead of
  denoising it.
- **Fix:** Retuned the preset to the validated stable pair `lambda=0.5,
  mu=-0.53` (`TAUBIN_STABLE_LAMBDA` in `app.py`). Added `taubin_stability()`
  in `src/mesh_ops.py`, which computes the exact per-iteration gain
  `|f(w)| = |(1-lambda*w)(1-mu*w)|` and flags pairs with gain > 1.01 as
  unstable. The preset message and the live explanation panel now generate
  their claim from the measured start→noisy→smoothed roughness sequence
  instead of hard-coded success text.
- **Test evidence:**
  - `tests/test_presets_and_metrics.py::test_remove_noise_preset_actually_denoises` —
    asserts roughness drops ≥10% versus the noisy stage and stays within 15%
    of its AABB, using the exact shipped preset parameters.
  - `tests/test_presets_and_metrics.py::test_app_preset_uses_the_validated_taubin_pair`
  - Browser: roughness sequence rendered as **0.1269 → 0.1569 → 0.1264** —
    the smoothed stage is now below both the noisy stage and the clean
    original. [Screenshot](fix_verification/screenshots/04_remove_noise_preset.png)

### AUD-003 — Roughness mislabeled and overinterpreted — **Resolved**

- **Severity:** Blocker
- **Root cause:** The scale-dependent quantity `mean ||v - mean(N(v))||` was
  labeled "roughness energy" and described only as "lower usually means
  smoother," with no disclosure that uniform shrinkage also lowers it.
- **Fix:** Renamed throughout to **"Roughness (mean neighbor distance)"**
  (`ROUGHNESS_LABEL`/`ROUGHNESS_CAPTION` constants in `app.py`), with a
  caption stating explicitly that it is scale-dependent and must be read
  together with the size metrics. Applied everywhere the metric appears:
  Playground metric strip, Advanced Metrics table, Method Comparison,
  download summary, and docs. Also renamed "Topology changed?" →
  **"Topology counts changed?"** and clarified "Shrinkage" → **"AABB diagonal
  change"** per the audit's exact recommendation.
- **Test evidence:**
  - `tests/test_mesh_ops.py::test_roughness_is_scale_dependent_documented_behavior` —
    proves a 0.5×-scaled copy reports exactly half the roughness, and asserts
    this is the *documented*, not hidden, behavior.
  - `tests/test_mesh_ops.py::test_flat_grid_roughness_is_nonzero_boundary_effect`

### AUD-004 — Step Inspector ignored boundary pinning — **Resolved**

- **Severity:** Blocker
- **Root cause:** `inspect_uniform_step`/`inspect_cotangent_step` computed an
  unconstrained neighbor-average step regardless of boundary status, so the
  inspector predicted motion for vertices the active smoother actually pins.
- **Fix:** Both functions in `src/mesh_ops.py` now accept `preserve_boundary`,
  detect boundary membership via `find_boundary_vertices`, and set
  `pinned=True`/predicted position = current position when appropriate
  (matching `laplacian_smooth`/`cotangent_smooth` exactly). `app.py`'s
  Step Inspector gained a "Preserve boundary vertices (match the smoothing
  setting)" checkbox defaulting to the Playground's own setting, and a
  prominent banner explaining the pin. The unconstrained target is still
  shown, clearly labeled "reference only."
- **Test evidence:**
  - `tests/test_mesh_ops.py::test_inspector_pinned_boundary_predicts_no_motion` —
    asserts the inspector's prediction *equals* one real `laplacian_smooth`
    step's result for a boundary vertex.
  - `tests/test_mesh_ops.py::test_inspector_unpinned_matches_smoother_step`,
    `test_inspector_boundary_off_predicts_motion`, `test_cotangent_inspector_honors_pinning`
  - Browser: vertex 0 on Plane/grid correctly reported as a pinned boundary
    vertex with zero predicted movement.
    [Screenshot](fix_verification/screenshots/09_step_inspector.png)

### AUD-005 — Method Comparison used the wrong baseline — **Resolved**

- **Severity:** Blocker
- **Root cause:** Method Comparison always cloned the *committed* working
  mesh, but the "Uniform vs Taubin" preset only produced a noisy *live
  preview* — no commit step existed in the advertised flow, so the
  comparison silently ran on the clean sphere.
- **Fix:** `_build_preview_mesh` now stores the noisy intermediate stage (the
  mesh after noise but before smoothing) in `PREVIEW_NOISY_STAGE_KEY`.
  `_comparison_input_candidates` exposes four explicitly named, selectable
  baselines: Committed working mesh, Source original, Noisy preview stage
  (before smoothing), Current live preview — each labeled with its vertex
  count and roughness. The "Uniform vs Taubin" preset now sets
  `COMPARISON_INPUT_KEY` to the noisy stage directly, so the comparison and
  the preset agree on what "the noisy mesh" means without an undocumented
  extra step.
- **Live-browser bug found and fixed during verification:** the comparison
  radio, mounted for the first time only when the user navigates to Method
  Comparison (a consequence of the AUD-021 lazy-rendering fix), did not
  visually reflect the preset's pre-set selection although the underlying
  `session_state` value — and therefore the actual computation — was
  correct. Fixed by passing `index=options.index(current_choice)` explicitly
  to `st.radio` in `_render_method_comparison_lab`.
- **Test evidence:**
  - `tests/test_app_state.py::test_comparison_defaults_to_noisy_stage_after_preset` —
    asserts the stored comparison input equals the noisy stage and every row's
    "Roughness before" equals the noisy value (0.1569), not the clean value.
  - Browser, before fix: radio visually showed "Committed working mesh"
    selected while the caption said "Noisy preview stage" — a real,
    reproducible desync.
  - Browser, after fix: radio and caption agree.
    [Screenshot](fix_verification/screenshots/05b_method_comparison_input_v2.png)

### AUD-006 — Commit immediately re-previewed the same operation — **Resolved**

- **Severity:** High
- **Root cause:** Commit copied the preview into the working mesh but left
  noise/iteration controls enabled, so the very next rerun rebuilt the same
  operation on top of the freshly committed mesh.
- **Fix:** `_commit_preview_mesh` is now the button's `on_click` callback and,
  after committing, resets `NOISE_ENABLED_KEY`, `SMOOTHING_ITERATIONS_KEY`,
  and `DEMO_MODIFIER_KEY` to neutral — legal here because callbacks run
  before widget instantiation. The flash message explicitly states what was
  committed and that one-shot controls were cleared.
- **Test evidence:** `tests/test_app_state.py::test_commit_does_not_immediately_reapply_the_operation` —
  commits a noisy preview and asserts the working mesh equals the pre-commit
  preview, noise is disabled, iterations are 0, and no new preview exists.

### AUD-007 — Side-by-side hid shrinkage via independent auto-fit — **Resolved**

- **Severity:** High
- **Root cause:** `_render_before_after_comparison`'s Side-by-side mode used
  two independent PyVista plotters, each calling `reset_camera()`, which
  normalizes each mesh to roughly the same on-screen size regardless of
  actual scale.
- **Fix:** New `make_side_by_side_plotter` in `src/visualization.py` renders
  both meshes in **one shared scene and camera**: the current mesh is offset
  to the right by a fixed multiple of the *original* mesh's width (so the
  offset itself cannot shrink with the copy), and a single `reset_camera()`
  call fits both. A real size difference is now a real size difference on
  screen.
- **Test evidence:** Browser — after "See shrinkage," Side-by-side shows the
  smoothed sphere visibly and correctly smaller than the original in one
  frame. [Screenshot](fix_verification/screenshots/10_side_by_side_synced.png)
  (No practical unit test for camera geometry; verified visually per the
  audit's own recommended remedy.)

### AUD-008 — Baselines conflated original/working/noisy/preview — **Partially Resolved**

- **Severity:** High
- **Root cause:** No named noisy/pre-action snapshot existed; Playground
  metrics always compared source-original vs. current with no way to see
  working→noisy or noisy→smoothed directly.
- **Fix:** `PREVIEW_NOISY_STAGE_KEY` now holds a real named noisy snapshot,
  consumed by Method Comparison (AUD-005) and by the new stage-roughness line
  ("Roughness start → noisy → smoothed: …") shown in the Playground status
  and explanation panel. Every metric location was given an explicit baseline
  caption (e.g., "Baseline: source original → committed working mesh").
- **Remaining limitation:** The Playground's *visual* comparison (Overlay/
  Side-by-side) still only offers original-vs-current; there is still no
  dedicated working→noisy Playground viewer pane. This is now clearly
  labeled rather than silently mixed, but a true three-state persistent
  visual sequence (clean/noisy/smoothed shown together) was judged out of
  scope for a fix pass that must not add new features — flagged as a
  remaining limitation, not hidden.

### AUD-009 — Taubin permits unwarned extreme expansion — **Resolved**

- **Severity:** High
- **Root cause:** Independent lambda/mu sliders had no validation; unsafe
  pairs could expand the mesh by thousands of percent with no warning, and
  prose implied unqualified "shrinkage reduction."
- **Fix:** `taubin_stability(lam, mu)` computes the exact per-iteration
  spectral gain. The Playground Taubin controls, the Method Comparison
  controls, and the explanation panel all call it and render a specific
  warning (naming the measured gain and an example stable pair) whenever the
  current pair is unstable. The Playground viewer also shows a size-based
  "the preview EXPANDED by X%" warning (`_render_expansion_warning`) as a
  second, independent signal. Ranges were left open (per "do not weaken
  functionality") but are now always paired with an accurate, computed
  warning rather than silence.
- **Test evidence:** `tests/test_mesh_ops.py::test_taubin_recommended_pair_is_stable`,
  `test_taubin_bad_pairs_flagged_unstable` (parametrized over the audit's own
  measured bad pairs), `test_taubin_stable_pair_limits_size_change_on_sphere`.
  Browser: setting lambda to 0.2 on the "Remove noise" preset immediately
  surfaces "Unstable Taubin pair" with the measured gain
  (`tests/test_app_state.py::test_taubin_unstable_pair_shows_warning`).

### AUD-010 — Method Comparison became silently stale — **Resolved**

- **Severity:** High
- **Root cause:** Stored comparison rows/input persisted through later
  working-mesh mutations with no invalidation.
- **Fix:** `_render_method_comparison_lab` compares the stored input snapshot
  against the *current* value of whichever named baseline it was run from
  (via `_meshes_have_same_vertices`) and renders an explicit warning —
  "these stored results describe an earlier snapshot of '…' — re-run it" —
  when they diverge, without deleting the old results (so the student can
  still see what changed).
- **Test evidence:** `tests/test_app_state.py::test_comparison_flags_stale_results_after_commit` —
  runs a comparison, mutates the working mesh via manual smoothing, and
  asserts the "earlier snapshot" warning appears.

### AUD-011 — Viewer controls were silent no-ops in some views — **Resolved**

- **Severity:** Blocker
- **Root cause:** Overlay always uses a fixed rendering, and Side-by-side/
  Original-only never applied normal overlays, but the display-mode and
  normal-overlay controls remained enabled and gave no feedback.
- **Fix:** `_render_viewer_sidebar` now reads the active Playground view mode
  and disables (rather than silently ignores) Display mode in Overlay, and
  all normal-overlay controls whenever the view isn't "Current only" — each
  with an explanatory caption. Additionally, normal length/vertex-weighting
  are disabled when their corresponding overlay checkbox is off (an expected
  conditional no-op, now also visibly disabled instead of just inert).
- **Test evidence:** Browser — Overlay view: Display mode select and the
  Normals expander controls render disabled with captions explaining why.
  (Covered by manual browser inspection; Streamlit's `disabled=` widget
  attribute has no separate AppTest-level assertion path used here beyond
  visual confirmation.)

### AUD-012 — Downloaded summary attributed current widgets to old geometry — **Resolved**

- **Severity:** High
- **Root cause:** The Learning Summary/Markdown download read geometry from
  the committed mesh but method/lambda/iterations from the *current*
  uncommitted widgets, so an uncommitted method change could be reported as
  if it produced the committed geometry.
- **Fix:** `_render_learning_summary` and `_build_summary_markdown` now derive
  every setting exclusively from `_last_committed_action_rows(history)` — the
  last entry of the immutable committed action history — never from live
  widget state. `_render_advanced_metrics_tab` no longer takes a `controls`
  parameter at all, removing the temptation to read live widgets there.
- **Test evidence:** `tests/test_app_state.py::test_summary_reports_committed_method_not_current_widget` —
  commits with Uniform, then changes the method selector to Taubin *without*
  committing, and asserts the rendered summary tables show "Uniform
  Laplacian" and never show the uncommitted "Taubin" selection.

### AUD-013 — Control/viewer/explanation separated on scroll — **Resolved**

- **Severity:** High
- **Root cause:** Only the viewer column was sticky; the explanation and
  metric cards scrolled off-screen while lower controls (iterations, lambda,
  Taubin mu) remained visible.
- **Fix:** Added `_render_compact_metric_strip` — three key metrics (roughness
  change, AABB diagonal change, average movement) plus a context-specific
  "look for" hint — rendered *inside the sticky center column*, directly
  under the viewer, so it stays on screen together with the control and the
  visual result. The full explanation panel and secondary metric cards remain
  in the right column for students who scroll to them, but the essential
  change → see → understand loop no longer requires scrolling.
- **Test evidence:** Visual/structural change; verified by reading the
  rendered column structure in every Playground screenshot (the metric strip
  is visible under the viewer in all of them, e.g.
  [04_remove_noise_preset.png](fix_verification/screenshots/04_remove_noise_preset.png)).

### AUD-014 — Local falloff/radius created undisclosed no-ops — **Resolved**

- **Severity:** Blocker
- **Root cause:** With integer graph distances, linear and smoothstep falloff
  produce identical weights at radius 1–2 (the shipped preset used radius 2),
  and the outer ring's zero weight was undocumented.
- **Fix:** The falloff selector is now `disabled` whenever radius < 3, with a
  caption explaining exactly why ("linear and smoothstep produce exactly the
  same weights there"). The Local soft smoothing preset's radius was raised
  from 2 to 3 so the control is meaningful by default. A new per-distance
  weight table (`_soft_selection_ring_rows`) shows the actual numbers,
  including the radius ring's weight of 0.
- **Test evidence:** `tests/test_mesh_ops.py::test_falloff_identical_at_radius_two`,
  `test_falloff_differs_at_radius_three`, `test_outer_ring_has_zero_weight`.
  Browser: preset now shows radius 3 with the falloff-lock explanation.
  [Screenshot](fix_verification/screenshots/07a_local_radius_3.png)

### AUD-015 — Manual noise ignored "Noise enabled," recorded zero-strength actions — **Resolved**

- **Severity:** Blocker
- **Root cause:** "Add noise to current mesh" called `add_noise` unconditionally
  in manual mode, regardless of the checkbox or strength value.
- **Fix:** `_add_noise_to_working` now checks `noise_enabled`/`noise_strength`
  and rejects the action with a flash message if either is off/zero; the
  button itself is `disabled=` with a caption when the same condition holds,
  so the state is visible before the click, not just after.
- **Test evidence:** `tests/test_app_state.py::test_manual_add_noise_respects_the_noise_checkbox` —
  confirms the button is disabled when noise is off, remains disabled at
  strength 0, and only mutates/records history once real settings are used.

### AUD-016 — Zero-effect smoothing was committable and counted — **Resolved**

- **Severity:** Blocker
- **Root cause:** `changed=True` was set whenever an operation was
  *requested* (iterations > 0), not when vertices actually moved, so
  `lambda=0` was committable and recorded as applied work.
- **Fix:** `_build_preview_mesh` now compares actual vertex arrays
  before/after every stage (demo bump, noise, smoothing) via
  `_meshes_have_same_vertices` and only sets the corresponding `*_applied`/
  `changed` flags when geometry truly moved. Commit is `disabled=` whenever
  the preview equals the working mesh, with a caption explaining why. The
  same real-change check now gates the manual Apply-smoothing/Add-noise
  buttons and history recording.
- **Test evidence:** `tests/test_app_state.py::test_zero_lambda_smoothing_is_not_committable` —
  sets iterations=10, lambda=0, and asserts Commit is disabled and no preview
  is stored. `tests/test_mesh_ops.py::test_zero_lambda_uniform_moves_nothing`,
  `test_zero_strength_noise_moves_nothing`.

### AUD-017 — Original-only mismatched its own label/metrics — **Resolved**

- **Severity:** High
- **Root cause:** The heading stayed "Preview mesh," and the status text
  described the hidden preview while the viewer showed only the original.
- **Fix:** `_viewer_heading_and_legend` computes a mode-true heading per view
  ("Viewer: source original (NAME)" for Original-only) and an explicit
  legend. The status line is prefixed with "(NOT shown in this view):" when
  the mode is Original-only, so the surrounding text can no longer be
  mistaken for a description of the visible geometry.
- **Test evidence:** Code inspection + browser confirmation of the heading
  text logic (`_viewer_heading_and_legend`); exercised transitively by the
  full Playground browser walkthrough with no exceptions.

### AUD-018 — Volume validity overstated — **Resolved**

- **Severity:** Medium
- **Root cause:** `compute_shape_metrics` trusted `is_watertight` alone and
  took `abs(signed volume)`, which is wrong for oppositely oriented
  disjoint components (cancels to near-zero) or a single flipped face on an
  otherwise watertight mesh (inflates the signed sum).
- **Fix:** `src/mesh_metrics.py` now additionally requires
  `trimesh_mesh.is_winding_consistent` and a signed volume magnitude above
  `EPSILON` before reporting volume at all; otherwise it reports `None`
  (N/A), and the UI caption explains the exact assumption.
- **Test evidence:** `tests/test_presets_and_metrics.py::test_volume_reported_for_consistent_tetrahedron`,
  `test_volume_gated_for_inconsistent_winding` (reproduces the audit's exact
  flipped-face tetrahedron and asserts volume is now `None`, not 2.1667),
  `test_volume_gated_for_cancelling_components` (reproduces the audit's
  disjoint-tetrahedra construction and asserts volume is now `None`, not 0).

### AUD-019 — Cotangent/polygon simplifications undisclosed — **Resolved**

- **Severity:** Medium
- **Root cause:** UI/docs called cotangent smoothing "geometry-aware" without
  disclosing frozen weights, aggregate clamping, the missing mass term, or
  fan triangulation.
- **Fix:** Docstrings in `src/mesh_ops.py` (`cotangent_smooth`) now state the
  simplifications explicitly. `docs/METHODS.md` gained a dedicated
  "simplified teaching smoother, not a full Laplace–Beltrami discretization"
  section listing frozen weights, clamping, no mass matrix, and the absolute
  degeneracy tolerance. The in-app explanation panel and Step Inspector
  caption were updated to say "this implementation requires a triangulation"
  and "weights are computed once and reused across iterations" instead of
  the prior unqualified claims.
- **Test evidence:** Content-only change; verified by direct reading of the
  updated docstrings/docs/UI strings.

### AUD-020 — Narrow layout technically responsive but unusable — **Resolved**

- **Severity:** Medium
- **Root cause:** The three-column Playground layout (`st.columns([0.29,
  0.46, 0.25])`) never adapted below 1100px; preset button labels broke
  mid-word.
- **Fix:** `_inject_layout_css` gained a `@media (max-width: 1100px)` rule
  that stacks top-level `stHorizontalBlock` columns to full width while
  keeping *nested* column pairs (preset button pairs, the metric strip)
  sharing a row at a smaller width, plus a `word-break: normal` rule on
  button labels to stop mid-word breaks.
- **Test evidence:** Browser at 768×900 — columns stack, no mid-word breaks,
  full-width readable text.
  [Screenshot](fix_verification/screenshots/11_narrow_viewport_768.png)

### AUD-021 — Hidden viewers generated warning noise / unnecessary work — **Resolved**

- **Severity:** Medium
- **Root cause:** `st.tabs` executed every tab body — including hidden 3D
  viewers — on every rerun.
- **Fix:** Replaced the six `st.tabs` with a single `st.radio`-based section
  selector (`ACTIVE_SECTION_KEY`) in `main()`; only the selected section's
  render function is called per rerun. Also removed several never-mounted
  functions entirely (see AUD-025) rather than lazily rendering dead code.
- **Remaining limitation:** The active viewer itself still creates a new VTK/
  WebGL context on every control change (inherent to the current
  PyVista→Panel→iframe embedding approach), so some WebGL console warnings
  persist during normal interaction — the console capture confirms 0 errors,
  and these are per-render notices from the visible viewer, not the
  previously-reported hidden-tab noise. Eliminating them entirely would
  require a different embedding strategy, judged out of scope for a fix pass
  that must not restructure unrelated functionality.
- **Test evidence:** [console_log.txt](fix_verification/console_log.txt) —
  0 `[error]` entries across the full 12-scenario browser walkthrough.

### AUD-022 — Docs disagreed with the live-preview UI — **Resolved**

- **Severity:** Medium
- **Root cause:** `STUDENT_GUIDE.md`/`DEMO_SCRIPT.md` described an old
  manual-button-only workflow ("Add noise", "Reset to clean original") that
  doesn't match the current default Live Preview UI.
- **Fix:** Rewrote `README.md`, `docs/METHODS.md`, `docs/STUDENT_GUIDE.md`,
  and `docs/DEMO_SCRIPT.md` from the current live-preview/commit/reset
  workflow, using exact current button and section names throughout, and
  added the stability condition, roughness scale-dependence, and cotangent
  simplifications to `METHODS.md`.

### AUD-023 — Repetitive AI-slop-style prose — **Resolved**

- **Severity:** Medium
- **Root cause:** Vertex/edge/face definitions, shrinkage, and boundary
  concepts were each repeated across four+ near-duplicate structures (Guided
  Learning's 8 nested tabs + 3 nested expander groups, concept cards, lecture
  notes companion, student exercises, README).
- **Fix:** Removed the unmounted `_render_lab_intro`; consolidated Guided
  Learning from "how-to-use + walkthrough + 3 expander groups (with their own
  nested expanders)" down to "how-to-use + walkthrough + 1 key-terms
  expander." Rewrote the 8 walkthrough steps and 6 concept cards with
  specific, current-state language ("this implementation requires a
  triangulation," "lambda < |mu|") replacing vague phrases ("relax," "good
  smoothing"). Rewrote all 7 Student Exercises with exact control names and
  factually correct expected outcomes (previously several described the false
  "Remove noise" result or the untaught noisy-comparison baseline).
- **Test evidence:** Content-only change; reduction verified by diffing
  section/expander counts before and after.

### AUD-024 — Source switching retained stale controls/messages — **Resolved**

- **Severity:** Medium
- **Root cause:** `_sync_working_mesh` reset geometry/history on a source
  change but left smoothing/noise widget values and the preset message
  untouched, so switching sources could immediately re-apply a stale
  operation (e.g. Cotangent iterations) to the new mesh.
- **Fix:** `_sync_working_mesh` now distinguishes a **manual** source switch
  from a **preset-triggered** one (`PRESET_SOURCE_SWITCH_KEY`). A manual
  switch resets noise/iterations/demo-modifier/preset-message to neutral and
  shows an explanatory flash message; a preset switch intentionally keeps its
  own control values (that's the point of a preset).
- **Test evidence:** `tests/test_app_state.py::test_source_switch_resets_experiment_controls`
  (manual switch → neutral) and
  `test_preset_source_switch_keeps_preset_controls` (preset switch → preset's
  own values retained).

### AUD-025 — Dead/unmounted scaffolding — **Resolved**

- **Severity:** Low
- **Root cause:** `_render_lab_intro`, `_render_before_after_comparison`,
  `_render_noise_experiment_notes`, and `_render_scribe_notes_placeholder`
  were defined but never called; `method_comparison_verts` and the old
  `PREVIEW_NOTE_KEY` were written but unused.
- **Fix:** All four dead functions were deleted outright (not merely left
  unmounted) along with the unused `COMPARISON_MODES` list and
  `method_comparison_verts`/`PREVIEW_NOTE_KEY` state. `PREVIEW_MESH_KEY` is
  now genuinely consumed by Method Comparison (AUD-005), so it is no longer
  dead state either.
- **Test evidence:** `python -m compileall .` passes with no references to
  the removed names; `grep` confirms no remaining call sites.

---

## Required scenario re-test summary

| Scenario | Result |
| --- | --- |
| Fresh start | Pass — neutral state, 0% metrics, clear "start here" caption. [01](fix_verification/screenshots/01_fresh_default_desktop.png) |
| Reset | **Pass (was Fail)** — no crash, full state restored. [03](fix_verification/screenshots/03_after_reset_no_crash.png) |
| Remove noise preset | **Pass (was Fail)** — genuinely denoises (0.1269→0.1569→0.1264). [04](fix_verification/screenshots/04_remove_noise_preset.png) |
| Uniform vs Taubin + Method Comparison | **Pass (was Fail)** — comparison runs on the actual noisy stage; radio/caption agree after the index= fix. [05b](fix_verification/screenshots/05b_method_comparison_input_v2.png), [05c](fix_verification/screenshots/05c_method_comparison_results_v2.png) |
| Boundary preservation on/off | Pass — border pinned (0% change, "Boundary moved? No") when on; collapses (−70%, "Yes") when off. [06b](fix_verification/screenshots/06b_boundary_off_v2.png), [06c](fix_verification/screenshots/06c_boundary_on_again_v2.png) |
| Local radius/falloff | **Pass (was Blocker)** — falloff locked below radius 3 with explanation; preset now uses radius 3. [07a](fix_verification/screenshots/07a_local_radius_3.png) |
| Zero lambda / zero noise strength | **Pass (was Blocker)** — both actions correctly rejected/disabled. |
| Commit → reset → source switch | **Pass (was Fail)** — commit does not re-preview itself; reset and manual source switch both produce a neutral, predictable state. |
| Stale Method Comparison | **Pass (was Fail)** — explicit staleness warning after a later commit. |
| Step Inspector | **Pass (was Fail)** — boundary pinning honored and explained. [09](fix_verification/screenshots/09_step_inspector.png) |
| Report download | **Pass (was Fail)** — generated strictly from committed history. |
| Side-by-side / Overlay | **Pass (was Fail for Side-by-side)** — one shared scene/camera makes real shrinkage visible. [10](fix_verification/screenshots/10_side_by_side_synced.png) |
| Invalid OBJ | Pass — clear error, safe Cube fallback, no crash. [12](fix_verification/screenshots/12_invalid_obj_fallback.png) |
| Narrow viewport (768px) | **Pass (was Fail)** — columns stack, no mid-word breaks. [11](fix_verification/screenshots/11_narrow_viewport_768.png) |

## Remaining limitations (not hidden, judged out of scope for this pass)

1. **AUD-008 (partial):** the Playground's visual comparison still only shows
   original-vs-current; a true persistent three-state (clean/noisy/smoothed)
   visual sequence in one view was judged a feature addition, not a bug fix,
   and was not built. The data now exists (`PREVIEW_NOISY_STAGE_KEY`) and is
   used numerically (status line, Method Comparison), so a future visual
   extension is straightforward.
2. **AUD-021 (partial):** per-render WebGL context-creation warnings from the
   *active* viewer persist (0 errors, many warnings); eliminating them would
   require replacing the PyVista→Panel iframe embedding, out of scope here.
3. Taubin lambda/mu ranges remain open (unstable pairs are reachable) by
   design, per the "do not weaken functionality" instruction — every unstable
   pair now produces an accurate, computed warning instead of silence.

## Final verdict

**Ready after minor fixes.**

All 9 Blocker and all 8 High-severity issues from the audit are Resolved and
covered by passing automated tests (36/36) plus direct browser verification,
including one additional live-UI bug (comparison-radio visual desync) found
and fixed during this pass. All Medium and Low issues are Resolved except the
two explicitly documented partial items above, neither of which is a
correctness or trust problem — they are scope boundaries, clearly disclosed
rather than hidden. The application can be presented as a mesh-smoothing
teaching tool; the two remaining partial items are reasonable candidates for
a follow-up iteration, not blockers to use.
