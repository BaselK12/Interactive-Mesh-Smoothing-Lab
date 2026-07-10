Overall verdict:
- **Not ready**

Scores:
- Visual quality: **5/10**
- Content correctness: **4/10**
- Functional controls: **5/10**
- Beginner educational value: **4/10**
- Control-to-explanation proximity: **4/10**
- Before/after clarity: **4/10**
- Overall readiness: **4/10**

# Mesh Smoothing Lecture Lab — Full Product Audit

Audit timestamp: 2026-07-10 11:26:22 (Asia/Jerusalem)  
Repository: `C:\Personal\University\Computer Graphics\Interactive Mesh Processing Visualizer`  
Runtime: Python 3.13.6, Streamlit 1.58.0, NumPy 2.5.0, Trimesh 4.12.2, PyVista 0.48.4, Panel 1.9.3  
Browser viewports: 1440×1000 desktop and 768×900 narrow  
Server: `http://127.0.0.1:8501` (default port was free)  

Recommendation: **Fix high-priority UX issues first.** The uniform-smoothing core and several visual teaching ideas are salvageable, but the reset crash, false denoising preset, misleading roughness interpretation, incorrect boundary inspector, and comparison-state problems must be fixed before presentation.

## Audit method and evidence standard

This was not a source-only review. I:

- inspected every tracked project file (`app.py`, `requirements.txt`, `README.md`, all files under `src/`, `docs/`, and `examples/`);
- ran `python -m compileall .` successfully and reverted the tracked bytecode file it touched;
- launched the unmodified app with `python -m streamlit run app.py` on port 8501;
- used Playwright against the real Streamlit UI at desktop and narrow widths;
- exercised presets, sliders, checkboxes, selectors, tabs, uploads, commit/manual actions, comparison, inspector, reset, and download;
- inspected the browser console and Streamlit logs;
- ran numerical probes directly against the implemented geometry functions to distinguish UI problems from algorithm behavior;
- created only this audit, screenshots, runtime logs, and one downloaded-summary artifact. No product source was changed, committed, or pushed.

The repository contains no automated test suite. All pass/fail statements below come from browser runs, numerical probes, and source-to-UI reconciliation.

The exact browser contexts, endpoint values, state-transition checks, and deterministic probes are summarized in [RUNTIME_PROBES.md](RUNTIME_PROBES.md). This companion is test traceability, not a separate source of conclusions.

Console/runtime classification:

- Normal app interactions produced **0 browser-console errors** in the tested environment.
- An earlier console inspection observed harmless unsupported feature-policy names and Streamlit iframe sandbox warnings; those messages are not part of the later archived warning-level capture.
- The archived QA-session capture contains **198 warnings**, all repeated zero-size WebGL framebuffer/texture operations from hidden iframe canvases; the visible viewer still rendered. [Captured log](browser_console_warnings.log)
- Real application failure: Reset raised a Streamlit exception in the UI and server log, not a JavaScript-console error.

## Internal architecture map

```text
source radio / sample selector / OBJ upload
                    |
                    v
             base MeshData + source key
                    |
                    v
            _sync_working_mesh()
             |                 |
             |                 +--> ORIGINAL_MESH_KEY: source baseline
             +--------------------> WORKING_MESH_KEY: committed state
                                      |
                                      v
             live controls -> _build_preview_mesh()
                               clone working
                                  + teaching bump
                                  + optional noise
                                  + optional smoothing
                                      |
                                      v
                                active preview
                                  |       |
                       Playground UI     Commit
                                          |
                                          v
                                    working mesh + history

Independent readers of committed working state:
- Method Comparison (stored snapshot/results)
- Step Inspector
- Advanced Metrics and Markdown download
```

Important state limitations:

- There is no dedicated named noisy/pre-action snapshot. A noise-only commit temporarily makes `working_mesh` the exact noisy geometry, but that baseline is overwritten by the next commit and the Playground never offers working→preview comparison; separate noise state stores only a boolean and last settings.
- Playground comparisons always use source original versus active current/preview; they cannot show working/noisy input versus its next smoothing preview.
- `PREVIEW_MESH_KEY` and `PREVIEW_NOTE_KEY` are written but never read.
- comparison rows survive same-source commits and become stale.
- all top-level tab bodies execute on every rerun, including hidden viewer serialization.

Source evidence: `app.py:45-81`, `1062-1100`, `2126-2201`, `2211-2361`, `2477-2563`, `2752-2806`, and `2838-2863`.

## 1. Executive summary

The app has a promising visual-learning skeleton: prominent experiment presets, a real interactive 3D viewer, deterministic noise, a clear uniform-Laplacian formula, live preview separated from committed geometry, useful local-selection highlights, and a comparison table that internally runs each method from one saved input. The best single experience is the shrinkage preset in Overlay mode; one click produces a dramatic and correctly measured result.

That promise is undermined by failures that directly affect trust:

1. **Reset crashes the running app.**
2. **The “Remove noise” preset roughens and expands the sphere while claiming the opposite.**
3. **The quantity called “roughness energy” rewards uniform scaling/shrinkage and is presented too broadly as smoothness.**
4. **The Step Inspector predicts motion for boundary vertices that the active smoother pins.**
5. **The advertised noisy Uniform-vs-Taubin comparison silently compares the clean committed sphere unless the user performs an undocumented commit.**
6. **Committing a live preview immediately builds the same operation again, so a committed noise preview is followed by a second uncommitted noise preview.**
7. **Side-by-side viewers independently auto-fit, visually hiding even 71.36% AABB-diagonal contraction.**
8. **Several controls are actual or contextual no-ops without disclosure.**

As a result, the application can help an instructor demonstrate basic uniform smoothing, but it is not trustworthy as an unsupervised beginner lab or homework companion.

## 2. Top 10 problems

1. **AUD-001 — Reset crashes with `StreamlitAPIException`.**
2. **AUD-002 — “Remove noise” produces +31.84% roughness and +33.20% AABB change versus clean.**
3. **AUD-003 — “Roughness energy” is scale-dependent mean neighbor-centroid residual, not a general smoothness score.**
4. **AUD-004 — Step Inspector contradicts preserved-boundary smoothing.**
5. **AUD-005 — Uniform-vs-Taubin preset and Method Comparison use different baselines.**
6. **AUD-011 — Display and normal controls silently do nothing in Overlay and other incompatible views.**
7. **AUD-014 — The shipped Local preset exposes a falloff selector whose two choices produce exactly the same geometry.**
8. **AUD-015 — Manual Add noise ignores the Noise enabled checkbox and records zero-strength actions.**
9. **AUD-016 — Zero-effect smoothing is committable and recorded as applied work.**
10. **AUD-009 — Allowed Taubin parameter pairs can expand the sphere by thousands of percent without warning.**

## 3. Critical blockers

### AUD-001 — Reset crashes the app

- Severity: **Blocker**
- Area: Functional/state management
- Reproduction: Start the app, change any experiment setting, click **Reset experiment**.
- Expected: Working state returns to the source baseline; noise, iteration, preview, history, and comparison state clear; the app rerenders normally.
- Actual: `_reset_experiment()` partially clears derived state, then the handler writes `noise_enabled` after that keyed widget has been instantiated. Streamlit raises `StreamlitAPIException` and displays a traceback.
- Student impact: The advertised recovery path fails precisely when a novice needs it. State may be partially reset before the crash.
- Technical evidence: widgets are created at `app.py:1969-2002`; illegal same-run mutation begins at `app.py:2390`.
- Screenshot: [reset exception](screenshots/broken_reset_streamlit_exception.png)
- Recommended correction: Move all widget-state changes into an `on_click` callback executed before widget instantiation, or set a reset-request flag and apply widget defaults at the beginning of the next run. Add a browser regression test.

### AUD-002 — “Remove noise” teaches the opposite result

- Severity: **Blocker**
- Area: Educational correctness/preset tuning
- Reproduction: Fresh session → click **Remove noise**.
- Expected: The noisy sphere becomes measurably less rough while avoiding the large contraction of uniform smoothing.
- Actual: Browser cards show **+31.84% roughness**, **+33.20% AABB**, and **+74.36% area** versus clean. Numerical isolation shows the Taubin stage changes noisy roughness `0.156868 → 0.167281` (**+6.64%**) and expands AABB **+24.28% versus the noisy input**.
- Student impact: The primary denoising lesson is false, while nearby prose still says smoothing attempts to reduce roughness and the preset message promises success.
- Technical evidence: common preset μ state at `app.py:1838-1847`, denoise preset λ/iteration state at `app.py:1858-1867`, and unconstrained Taubin pair at `src/mesh_ops.py:341-369`.
- Screenshot: [false Remove noise result](screenshots/broken_remove_noise_preset_rougher_larger.png)
- Recommended correction: Retune against measured noisy-before/final values, validate the preset automatically, and generate its interpretation from those values instead of hard-coded success text.

### AUD-003 — Roughness is mislabeled and overinterpreted

- Severity: **Blocker**
- Area: Mathematics/content/metrics
- Reproduction: Compare a sphere with an exact half-scale copy, or inspect the method-comparison results after heavy uniform shrinkage.
- Expected: A smoothness metric should not improve solely because the entire shape is uniformly scaled down.
- Actual: the implemented mean `||v_i - mean(N(i))||` halves when the sphere is uniformly scaled by .5 (`0.126881 → 0.063441`). In a direct clean-sphere 10-iteration probe, Uniform’s reported 58.63% “roughness reduction” accompanies 59.13% AABB-diagonal contraction. A perfectly flat grid still scores `0.136569` because of boundary/valence effects.
- Student impact: Students can conclude that collapse is superior smoothing. Rankings and summary prose inherit the same error.
- Technical evidence: `src/mesh_ops.py:221-255`; UI claims at `app.py:767-770`, `1603-1605`, and `1691`.
- Screenshot: [10-iteration comparison table rewarding contraction as roughness reduction](screenshots/method_comparison_table_ranking.png)
- Recommended correction: Rename to **mean umbrella-Laplacian magnitude** or **mean neighbor-centroid residual**, state its length units and fixed-scale/connectivity limitation, and normalize by a scale such as median edge length if cross-size comparison is intended.

### AUD-004 — Step Inspector is not “exact” under boundary preservation

- Severity: **Blocker**
- Area: Educational/mathematical correctness
- Reproduction: Select Plane/grid, keep boundary preservation on, open Step Inspector at vertex 0, λ=.5.
- Expected: The inspector should say the boundary vertex is pinned and predict no motion.
- Actual: It predicts `(-0.875,-0.875,0)` from `(-1,-1,0)`. Actual smoothing leaves the vertex at `(-1,-1,0)`.
- Student impact: The strongest formula-teaching feature contradicts the algorithm the student actually runs.
- Technical evidence: unrestricted inspector `src/mesh_ops.py:539-568`; real boundary skip `src/mesh_ops.py:183-196`; claim at `app.py:1357-1362`.
- Screenshot: [boundary inspector mismatch](screenshots/step_inspector_boundary_mismatch_grid_vertex0.png)
- Recommended correction: Pass the current boundary/method/local settings into the inspector and show a prominent **Pinned: predicted motion suppressed** state. Explain synchronous updates.

Additional issues classified as **Blocker** under the supplied rubric are AUD-005 (the promised noisy comparison uses the wrong baseline), AUD-011 (exposed viewer controls silently do nothing in some modes), AUD-014 (the active falloff control is an exact no-op in the shipped Local preset), AUD-015 (Noise enabled does not control manual noise), and AUD-016 (a no-op is presented and recorded as applied work).

## Detailed issue register

### AUD-005 — Noisy comparison preset uses a clean comparison input

- Severity: **Blocker**
- Area: Workflow/comparison/state
- Reproduction: Fresh session → **Uniform vs Taubin** → Method Comparison → **Run comparison from current mesh**.
- Expected: All methods start from the noisy mesh promised by the preset.
- Actual: Noise exists only in live preview; Method Comparison clones committed `working_mesh`. The table’s “Rough before” is `0.1269` (clean sphere), not `0.1569` (seed-42 noisy sphere).
- Student impact: A seemingly fair comparison answers a different question from the one the student was instructed to run.
- Technical evidence: `app.py:1869-1878`, `1224-1255`, `2148-2190`, `2850-2852`.
- Screenshot: [clean comparison despite noisy preset](screenshots/method_comparison_clean_despite_noisy_preset.png)
- Recommended correction: Let comparison explicitly select **original / committed / displayed preview** as input and show a fingerprint/roughness of that baseline. Update the preset to navigate or provide the exact required commit step.

### AUD-011 — Viewer controls are silent no-ops in several modes

- Severity: **Blocker**
- Area: Controls/visualization
- Reproduction: Choose Overlay, switch Display mode from Wireframe+shaded to Points, then enable face normals.
- Expected: The selected display and overlays change, or disabled controls explain why they do not apply.
- Actual: Playwright iframe screenshots were byte-for-byte identical after both changes. Overlay hardcodes its rendering. Side-by-side and Original-only also ignore normal controls.
- Student impact: Controls appear broken and students may mislearn what normals/display modes affect.
- Technical evidence: `app.py:2507-2562`; `src/visualization.py:108-153`.
- Screenshot: [Points and face normals selected while Overlay remains unchanged](screenshots/overlay_points_and_normals_selected_no_effect.png); baseline Overlay: [before](screenshots/uniform_high_14_overlay.png)
- Recommended correction: Scope, disable, or hide incompatible viewer controls and state the rendering legend per mode.

### AUD-014 — Local radius/falloff semantics create no-op controls

- Severity: **Blocker**
- Area: Local smoothing/education
- Reproduction: Local preset, radius 2, switch smoothstep ↔ linear; then compare at radius 3.
- Expected: A falloff selector should visibly alter weights when offered as an active teaching control.
- Actual: radius 1 and 2 produce exactly identical linear/smoothstep weights and browser metrics. The shipped preset uses radius 2. Vertices exactly at radius receive zero weight; “maximum radius 4” highlights 21 of the grid’s 25 vertices, not all 25.
- Student impact: A beginner sees a selector that does nothing and receives no explanation of the zero-weight outer ring.
- Technical evidence: `src/mesh_ops.py:646-687`; preset at `app.py:1891-1903`.
- Screenshot: [radius 1](screenshots/local_radius_1.png), [radius 3](screenshots/local_radius_3_smoothstep.png)
- Recommended correction: Define graph steps as edge hops, label the outer ring as zero influence, and disable/annotate equivalent falloffs at radius ≤2.

### AUD-015 — Manual noise ignores “Noise enabled” and records zero-strength actions

- Severity: **Blocker**
- Area: Functional controls/history
- Reproduction: Turn Live Preview off, leave Noise enabled unchecked, click **Add noise to current mesh**; then set strength 0 and click again.
- Expected: Disabled noise should not apply; zero strength should be rejected as no change.
- Actual: unchecked noise changed Cube AABB +30.97%. Strength 0 left all cards identical but still recorded a noise action and set noise metadata.
- Student impact: Checkbox semantics are inconsistent between live and manual modes; history implies work that did not occur.
- Technical evidence: `app.py:2266-2297`, button exposure at `2381-2386`.
- Screenshot: [Noise disabled while manual action still applies](screenshots/manual_noise_disabled_but_applied.png)
- Recommended correction: Disable Add when noise is unchecked/zero, or remove the checkbox in manual mode and make the button label fully explicit.

### AUD-016 — Zero-effect smoothing is committable and counted

- Severity: **Blocker**
- Area: Functional controls/history
- Reproduction: Positive iterations, Uniform λ=0; observe cards and Commit button, then apply/commit.
- Expected: No-op preview is recognized, Commit is disabled, and iteration/history totals do not change.
- Actual: status says “10 iterations,” Commit is enabled, all geometry metrics remain zero. Manual application incremented committed iterations to 1 with unchanged geometry.
- Student impact: History and experiment summaries overstate work; students may believe iterations alone cause smoothing.
- Technical evidence: `changed=True` is set by requested operation at `app.py:2164-2194`, not actual vertex comparison.
- Screenshot: [zero-lambda committable preview](screenshots/broken_zero_lambda_committable.png)
- Recommended correction: Compare output vertices against the input before enabling commit or recording an action.

### High-severity issues

### AUD-006 — Commit immediately previews the same operation again

- Severity: **High**
- Area: State model/functional behavior
- Reproduction: Create a noise-only live preview at strength .35; note +23.63% roughness; commit it.
- Expected: The viewer shows the geometry just committed, with a neutral next-preview state.
- Actual: Enabled controls remain active, so the rerun applies the same noise to the newly committed noisy mesh. Cards jump to +101.72% roughness and +25.54% AABB versus clean.
- Student impact: The visible post-commit state is not the state just committed. Students cannot tell whether commit worked or why the mesh changed again.
- Technical evidence: commit at `app.py:2225-2263`; unconditional next preview at `app.py:2148-2199`.
- Screenshot: [second noise after commit](screenshots/broken_commit_immediately_previews_second_noise.png)
- Recommended correction: After commit, clear one-shot preview operations or show working and next preview as separately labeled states. Do not silently stack the same noise seed.

### AUD-007 — Side-by-side comparison hides shrinkage

- Severity: **High**
- Area: Before/after visualization
- Reproduction: **See shrinkage** → Playground view **Side-by-side**.
- Expected: Identical cameras, projection, zoom, and scale make the 71.36% AABB contraction obvious.
- Actual: Two independent plotters each call `reset_camera()`, auto-fitting both meshes to nearly the same on-screen size; interactions are not synchronized.
- Student impact: The principal before/after mode visually denies the metric it is meant to teach.
- Technical evidence: `app.py:2519-2540`; `src/visualization.py:103-105`.
- Screenshot: [independent auto-fit](screenshots/before_after_side_by_side_unsynchronized_autofit.png)
- Recommended correction: Render both meshes in one synchronized scene or share camera parameters and fixed world bounds. Add linked rotation/zoom.

### AUD-008 — Before/after baselines conflate original, working, noisy, and preview states

- Severity: **High**
- Area: Comparison/state model
- Reproduction: Commit noise, disable noise, preview smoothing, then view Overlay and quick metrics.
- Expected: A denoising lab should offer clean vs noisy, noisy vs smoothed, and clean vs smoothed comparisons.
- Actual: Playground always compares source `original_mesh` with active current/preview. A noise-only commit can make working the exact noisy geometry, but there is no dedicated noisy/pre-action snapshot, it is lost on the next commit, and Playground has no viewer/metric path for working→preview. Method Comparison can overlay a deliberately committed noisy input against each method result, but it does not preserve a named clean/noisy/final sequence, the supplied preset does not feed that noisy input to it, and its rows can become stale.
- Student impact: In the advertised Playground/preset workflow, the student cannot answer “how much noise did smoothing remove?” without extra commits, tab changes, and mentally reconstructing baselines.
- Technical evidence: `app.py:52-53`, `2477-2559`, `2691-2697`, `2754-2774`.
- Screenshot: [clean vs raw noise only](screenshots/noisy_sphere_seed42_strength035.png)
- Recommended correction: Store named baseline snapshots (`source`, `pre-action/working`, `noisy`, `preview`) and label every metric and visual with its A/B pair.

### AUD-009 — Taubin controls permit severe expansion without warning

- Severity: **High**
- Area: Algorithm controls/content
- Reproduction: Sphere, 10 iterations, choose Taubin; try λ=.05, μ=-.95 or λ=0, μ=-.95.
- Expected: Unsafe or semantically invalid λ/μ pairs should be constrained or warned; prose should not promise size preservation.
- Actual: numerical probes produced +1,952.90% and +4,205.70% AABB changes respectively. The browser also rendered an allowed pair expanding AABB +177.22% with no warning.
- Student impact: A beginner can destroy the mesh and be taught that an explosive result is a shrinkage-reduction method.
- Technical evidence: independent sliders `app.py:1995-2023`; two-pass implementation `src/mesh_ops.py:341-369`.
- Screenshot: [allowed Taubin expansion](screenshots/taubin_allowed_parameters_expand_177_percent.png)
- Recommended correction: Provide validated paired presets, explain the spectral condition, constrain the ranges, detect excessive expansion, and qualify all “preserves size” language.

### AUD-010 — Method Comparison silently becomes stale

- Severity: **High**
- Area: State management/comparison
- Reproduction: Run comparison, return to Playground, commit smoothing or noise on the same source, return to Method Comparison without pressing Run.
- Expected: Results clear or show a stale banner.
- Actual: Old rows, input mesh, visuals, and ranking remain. Browser verification retained old `0.1569` baseline after a new commit.
- Student impact: The table appears to describe the current mesh while actually describing an earlier snapshot.
- Technical evidence: clearing only at `app.py:1093-1095` and `1936-1938`; mutations at `2211-2361` do not invalidate comparison.
- Screenshot: [stale results retained after a new committed smoothing step](screenshots/method_comparison_stale_after_new_commit.png)
- Recommended correction: Version the working mesh and invalidate/relabel stored comparison whenever that version changes.

### AUD-012 — Downloaded summary can attribute current controls to older geometry

- Severity: **High**
- Area: Reporting/content/state
- Reproduction: Commit with Uniform, change the selector to Taubin without committing, then download from Advanced Metrics.
- Expected: Report settings identify the operation that produced the committed mesh.
- Actual: Geometry/metrics come from committed working state, but method, iterations-per-apply, λ, and boundary fields come from current widgets. Taubin μ and local radius/falloff are omitted. A noise-only commit was recorded as “Uniform Laplacian, λ=.45.”
- Student impact: A submitted lab report can be factually false even though the download succeeds.
- Technical evidence: `app.py:1529-1701`, `2791-2805`.
- Screenshot: [history says Uniform while committed-summary settings say Taubin](screenshots/download_summary_method_mismatch.png). The download transport also succeeded; a transport-test artifact is stored as [downloaded_summary.md](downloaded_summary.md).
- Recommended correction: Build reports from immutable action-history records and explicitly separate committed settings from current uncommitted controls.

### AUD-013 — Control, viewer, and explanation separate during scrolling

- Severity: **High**
- Area: UX/educational proximity
- Reproduction: At 1440×1000, scroll the left Playground column until Commit/smoothing controls are visible.
- Expected: Current explanation and compact metrics remain visible next to the control and sticky viewer.
- Actual: at main scrollTop 965, the viewer remained at y=272, but “What you are seeing” was at y=-668 and “Quick metrics” at y=-186—both entirely off-screen.
- Student impact: The intended `change → see → understand` loop becomes `change → see → remember text from above`.
- Technical evidence: CSS sticks only the center column at `app.py:1737-1757`; layout at `2752-2775`.
- Screenshot: [explanation scrolled away](screenshots/control_visible_explanation_scrolled_away.png)
- Recommended correction: Put a short dynamic explanation and 2–3 relevant metrics in the same sticky experiment panel as the viewer, or use a compact two-column layout.

### AUD-017 — Original-only view describes a preview it does not show

- Severity: **High**
- Area: Before/after labels/state
- Reproduction: See shrinkage → Playground view **Original only**.
- Expected: Heading, status, explanation, and cards clearly say the viewer is original while metrics refer to a hidden preview.
- Actual: heading remains “Preview mesh,” status says 14 Uniform iterations, and cards show -71.36% shrinkage while the iframe displays only the original.
- Student impact: Visual output and surrounding interpretation contradict one another.
- Technical evidence: `app.py:2485-2497`, `2541-2548`, `2772-2774`.
- Screenshot: [Original-only mismatch](screenshots/original_only_but_preview_status_metrics.png)
- Recommended correction: Make the selected view the primary label and state metric baselines independently.

### AUD-018 — Volume validity is overstated

- Severity: **Medium**
- Area: Metrics/mathematics
- Reproduction: Supply oppositely oriented closed components or a watertight mesh with inconsistent winding.
- Expected: Volume is rejected or qualified unless orientation/components are validated.
- Actual: code trusts `is_watertight` and takes `abs(signed volume)`. Numerical probes produced volume 0 for two disjoint, oppositely oriented tetrahedra whose physical total is 1/3, and 2.1667 for a translated tetrahedron with one reversed face whose volume is 0.1667.
- Student impact: A seemingly authoritative shrinkage metric can be wrong for valid-looking uploads.
- Technical evidence: `src/mesh_metrics.py:65-73`; [exact vertices, faces, command, and output](RUNTIME_PROBES.md#exact-volume-probe-reproduction).
- Screenshot: [volume presented in the comparison table](screenshots/method_comparison_table_ranking.png); the pathological values themselves are numerical/source evidence because they cannot be produced by built-in UI meshes.
- Recommended correction: validate winding and connected-component orientation; explicitly state assumptions in UI/report.

### AUD-019 — Cotangent and polygon support are simplified beyond the UI wording

- Severity: **Medium**
- Area: Algorithm/content/input handling
- Reproduction: Run multiple cotangent iterations on changing geometry; load concave polygons or scaled near-degenerate triangles.
- Expected: “Geometry-aware” explanation identifies the simplification and supported assumptions.
- Actual: cotangent weights are computed once and frozen across iterations; aggregate negative edge weights are clamped; no standard dual-cell/barycentric vertex-area mass term is used (the row is instead normalized by its positive weight sum); degeneracy uses an absolute tolerance; metric polygon triangulation is a simple fan. `pyramid.obj` is authored with a quad base but Trimesh loads it as six triangles.
- Student impact: Students may mistake a stable teaching smoother for a production Laplace–Beltrami implementation.
- Technical evidence: `src/mesh_ops.py:395-487`; `src/mesh_metrics.py:121-145`; `src/mesh_core.py:132-151`.
- Screenshot: [uploaded pyramid becomes triangle mesh](screenshots/cotangent_supported_uploaded_pyramid.png)
- Recommended correction: Label the implementation as simplified, document frozen weights/clamping/triangulation, and validate degeneracy/manifold assumptions.

### AUD-020 — Narrow layout is technically responsive but not usable

- Severity: **Medium**
- Area: Responsive design/accessibility
- Reproduction: Resize to 768×900.
- Expected: Primary experiment stacks or becomes a readable two-column layout.
- Actual: all three columns remain. Preset buttons split words (“shrinkage,” “boundary preservation,” “smoothing”) across many lines; explanation is ~150 px wide; viewer is reduced; top tabs crowd one row; sidebar disappears behind a chevron.
- Student impact: Controls and prose remain operable but require excessive reading effort and scrolling.
- Technical evidence: layout fixed at `st.columns([0.29,0.46,0.25])` in `app.py:2755`; only the center sticky rule is customized.
- Screenshot: [768 px viewport](screenshots/narrow_viewport_768.png)
- Recommended correction: add breakpoints that stack controls → viewer/explanation and use horizontally scrollable or wrapped tab navigation with intact labels.

### AUD-021 — Hidden viewers generate warning noise and unnecessary work

- Severity: **Medium**
- Area: Runtime/performance/diagnostics
- Reproduction: Load a fresh session and inspect the browser console; run Method Comparison and move any unrelated slider.
- Expected: Hidden tabs do not render heavy viewers; console remains useful.
- Actual: the archived QA-session warning capture contains 198 repeated zero-size WebGL framebuffer/texture warnings from hidden iframes and 0 browser errors. Separate earlier inspection also observed non-blocking feature-policy/sandbox warnings. All tab render functions execute on every rerun.
- Student impact: slower reruns and noisy diagnostics; visible viewer still rendered in this environment.
- Technical evidence: `app.py:2838-2863`; HTML serialization `src/visualization.py:221-230`.
- Screenshot: [fresh loaded state](screenshots/fresh_default_desktop_loaded.png)
- Console evidence: [archived browser warning log](browser_console_warnings.log). It contains the 198 WebGL warnings; the earlier non-blocking framework warnings were observed separately and are not claimed to be in this file.
- Recommended correction: lazily render active/heavy tab content and avoid creating WebGL canvases in zero-sized hidden containers.

### AUD-022 — Documentation and UI workflows disagree

- Severity: **Medium**
- Area: Documentation/education
- Reproduction: Follow `docs/DEMO_SCRIPT.md` or `docs/STUDENT_GUIDE.md` literally with default Live Preview on.
- Expected: Exact current labels and actions lead to the claimed experiment.
- Actual: docs refer to sidebar noise/smoothing controls, “Add noise,” “Apply smoothing,” “Reset to clean original,” and scrolling to metrics; current default UI uses live preview, Playground controls, **Commit preview**, **Reset experiment**, and a separate Advanced Metrics tab.
- Student impact: a novice looks for controls that are hidden until Live Preview is off.
- Technical evidence: `docs/DEMO_SCRIPT.md:10-34`, `docs/STUDENT_GUIDE.md:10-64`, `app.py:1961-2058`, `2364-2397`.
- Screenshot: [default Live Preview UI where manual-only Add/Apply actions are absent](screenshots/fresh_default_desktop_loaded.png)
- Recommended correction: rewrite all guides from the current default workflow and include exact button names.

### AUD-023 — Repetitive generated prose obscures the actual lesson

- Severity: **Medium**
- Area: Content/AI-slop
- Reproduction: Read Guided Learning, concept cards, lecture notes companion, Student Exercises, README, and summary.
- Expected: progressive teaching, each concept introduced once and tied to a current experiment.
- Actual: “vertices, edges, faces,” neighbor averaging, shrinkage, and boundaries are repeated across multiple near-duplicate structures. Vague phrases such as “relax,” “main shape,” “geometry-aware,” and “good smoothing” often substitute for current-state observations. No lecture sources or external method citations are provided.
- Student impact: more scrolling without a stronger mental model; authority is implied without provenance.
- Technical evidence: repeated blocks at `app.py:119-410`, `460-514`, `900-973`, and `1529-1701`.
- Screenshot: [eight nested Guided Learning tabs plus repeated action/observation structure](screenshots/guided_learning_nested_repetition.png)
- Recommended correction: consolidate to one guided path, cite external methods, label course core versus project extensions, and replace generic prose with measured current-state sentences.

### AUD-024 — Source switching retains stale experiment controls/messages

- Severity: **Medium**
- Area: State management
- Reproduction: Choose Cotangent with iterations >0 on Cube, then switch to Plane/grid or Sphere; or apply a preset then switch source manually.
- Expected: new source opens in a neutral state or clearly asks whether to reuse settings.
- Actual: geometry/history reset, but smoothing/noise/view settings and preset message persist. In browser testing, switching Cube → Plane/grid retained an unsupported Cotangent preview; switching to Sphere immediately applied five Cotangent iterations.
- Student impact: the first view of a new mesh may already be transformed or accompanied by an unrelated preset message.
- Technical evidence: `_sync_working_mesh` at `app.py:1070-1095` omits widget settings and messages.
- Screenshot: [unsupported retained settings](screenshots/cotangent_unsupported_cube.png)
- Recommended correction: define and communicate a source-switch policy; default to neutral controls or explicitly preserve them with a banner.

### AUD-025 — Dead/unmounted scaffolding increases maintenance risk

- Severity: **Low**
- Area: Code/content hygiene
- Reproduction: inspect call sites.
- Expected: implemented educational sections correspond to mounted UI.
- Actual: `_render_lab_intro`, `_render_before_after_comparison`, `_render_noise_experiment_notes`, and `_render_scribe_notes_placeholder` are never called. Stored preview keys and `method_comparison_verts` are unused.
- Student impact: no direct runtime impact, but stale copy and duplicate comparison logic make audits and future changes error-prone.
- Technical evidence: `app.py:119-137`, `437-443`, `576-657`, `1112-1139`, `65-66`, `1255`.
- Screenshot: [runtime surface containing only the mounted six tabs](screenshots/fresh_default_desktop_loaded.png)
- Recommended correction: remove dead scaffolding or mount one corrected, concise implementation; delete unused state.

## 4. Visual design findings

### Overall visual assessment

The interface is more intentional than an unstyled Streamlit prototype: typography is consistent, the red accent is restrained, presets are prominent, status messages use consistent cards, and the viewer has readable mesh colors. It still feels closer to a dense technical dashboard than a focused learning playground. Six equal-priority tabs, three narrow Playground columns, large sidebar statistics, long left-column controls, a long right-column metric stack, and repeated prose compete for attention.

The main viewer is not dominant enough. At 1440 px the content area is 970 px wide, but the viewer receives only ~404 px while controls receive ~239 px and explanations ~200 px. At 768 px all three columns remain, producing severe word wrapping. The first viewport contains title, tabs, presets, status, and selector before much of the viewer; a novice sees many choices before a first experiment is established.

### Visual finding table

| Severity | Location | Finding | Why it hurts usability | Recommended correction | Evidence |
| --- | --- | --- | --- | --- | --- |
| High | Playground, lower controls | Viewer is sticky; explanation/metrics are not | Current control and effect remain visible, but the explanation is entirely above the viewport | Sticky compact explanation beside/below viewer | [Screenshot](screenshots/control_visible_explanation_scrolled_away.png) |
| High | Side-by-side | Independently auto-fit meshes appear the same size | Hides the exact shrinkage lesson | Shared camera/world bounds | [Screenshot](screenshots/before_after_side_by_side_unsynchronized_autofit.png) |
| Medium | Desktop Playground | Three columns are too narrow | Explanations wrap heavily and cards form a very long vertical rail | Two columns: experiment + visual/interpretation | [Screenshot](screenshots/fresh_default_desktop_loaded.png) |
| Medium | 768 px | Desktop three-column layout is retained | Buttons split words; explanation becomes a narrow newspaper column | Responsive stacking breakpoint | [Screenshot](screenshots/narrow_viewport_768.png) |
| Medium | Overlay | Displacement lines fill the entire interior after large shrinkage | Strong result is visible but orange spokes and black wireframe create clutter | Toggle/sparsify displacement vectors and include legend | [Screenshot](screenshots/uniform_high_14_overlay.png) |
| Medium | Original-only | Label/status/cards describe preview while original is shown | Visual hierarchy communicates the wrong state | Mode-specific heading and baseline chip | [Screenshot](screenshots/original_only_but_preview_status_metrics.png) |
| Medium | Sidebar | Three large statistic metrics consume most vertical space | Source/view controls and relevant state become separated | Compact one-row stats or collapsible details | [Screenshot](screenshots/fresh_default_desktop_loaded.png) |
| Medium | Top navigation | Six tabs compete equally | No clear “start here,” and beginner/advanced material has equal visual weight | Beginner path first; group advanced tabs | [Screenshot](screenshots/fresh_default_desktop_loaded.png) |
| Low | Presets | Six equal buttons have no suggested order | A novice cannot tell which is the first experiment | Number or mark a recommended first preset | [Screenshot](screenshots/fresh_default_desktop_loaded.png) |
| Low | Right metric cards | Five or six full cards are stacked | Excessive scrolling and repeated boilerplate captions | Show 2–3 context-relevant cards; move rest to Advanced | [Screenshot](screenshots/uniform_low_1_overlay.png) |

### Direct answers to visual questions

- Main viewer visually dominant enough? **No.** It is the largest single object, but only 42% of the already reduced main content width.
- Obvious where to begin? **Partly.** Presets are prominent, but none is marked as first and Guided Learning is the fourth tab.
- Clear primary workflow? **Partly.** Live preview is explained, but preview/commit/comparison baselines diverge.
- Learning playground or technical dashboard? **Dashboard-leaning playground.** The visual experiment is surrounded by many controls, tabs, tables, metrics, and repeated text.
- Advanced details hidden until needed? **Not enough.** Seed, λ, μ, method, graph radius, falloff, and preservation are exposed early; Advanced Metrics is separated, but hidden tabs still render.
- Related controls grouped? **Mostly yes** within Noise/Smoothing, but source/view controls live in the sidebar and experiment controls in the page.
- Too many competing elements? **Yes**, especially tabs, presets, three rails, and metric cards.
- Consistent across tabs? **Stylistically yes; interaction patterns no.** Playground is three-column visual, comparison is cards/table, inspector is formula/table, learning is nested tabs/expanders.
- 3D viewer readable/framed? **Current-only and Overlay: generally yes. Side-by-side: misleading scale.**
- Normals/wireframes/regions/noise distinguishable? **Colors are distinguishable in Current-only.** Normal controls silently do nothing in other modes; local red/orange highlighting is the clearest overlay.

## 5. Content correctness findings

Content trustworthiness rating: **4/10**.

| Statement or concept | Where | Verdict | Implementation evidence | Correction needed |
| --- | --- | --- | --- | --- |
| Meshes contain vertices, edges, faces | app intro/cards/docs | Correct but basic | `MeshData`, polygon loops, unique edges in `src/mesh_core.py` | Add geometry-vs-connectivity distinction and surface-approximation context |
| Connectivity identifies touching/neighboring elements | Guided Learning/cards | Correct | adjacency from polygon boundary edges, `src/mesh_ops.py:141-147` | Define one-ring visually and distinguish face/edge adjacency |
| Face normals describe face orientation | Guided Learning | Correct but oversimplified | oriented fan area vectors, `src/mesh_ops.py:79-112` | Mention winding, degeneracy, and nonplanar polygons |
| Vertex normals average incident face normals | Guided Learning | Correct | `src/mesh_ops.py:115-138` | Explain these are shading/orientation estimates and crease behavior |
| Area-weighted normals give larger faces more influence | Cards/sidebar | Correct | unit face normals multiplied by polygon area | State that nonplanar, degenerate, or self-intersecting faces do not have the simple normal interpretation implied here |
| Uniform update `v'=v+λ(mean(N)-v)` | Inspector/METHODS | Correct | synchronous `next_vertices`, `src/mesh_ops.py:164-198` | Explicitly teach synchronous rather than in-place updates |
| More iterations make a surface smoother | Cards | Misleading | λ=0 is a no-op; high/unstable settings can collapse/roughen | Qualify by method/parameter and show contraction tradeoff |
| Smoothing leaves topology unchanged | Throughout | Correct for these functions; UI check is weak | faces reused unchanged by `copy_with_vertices`; UI compares counts only | Rename card to “Topology counts changed?” or compare face indices |
| Repeated uniform averaging often shrinks closed meshes | Throughout | Correct | sphere results: -59.13% AABB at 10×.5 | Use “often,” not universal; separate AABB, area, and volume |
| Boundary edge belongs to one face | Guided/METHODS | Correct for manifold inputs | edge multiplicity, `src/mesh_ops.py:150-161` | Disclose non-manifold limitations |
| Boundary preservation prevents collapse | Cards/METHODS | Oversimplified | only detected boundary vertices are pinned | Say it pins the border; interior collapse/self-intersection remain possible |
| Local smoothing uses graph-distance falloff | App/METHODS | Correct core, incomplete semantics | BFS hops and linear/smoothstep at `646-710` | Define an edge hop and zero-weight outer ring |
| Radius increases the affected region | App/exercises | Generally correct | affected counts 1, 5, 13, 21 for center grid radii 1–4 | State that exactly-at-radius vertices have zero influence |
| Taubin reduces shrinkage | App/docs/summary | Conditional, currently misleading | λ=.5/μ=-.53 works; .35/-.53 expands; unsafe pairs explode | State suitable-pair condition and validate controls |
| Cotangent is geometry-aware | App/METHODS | Correct but incomplete | weights derive from starting triangle angles then freeze | State frozen weights, clamping, normalized target, and no mass term |
| Cotangent is defined only for triangles | App | Too absolute | this implementation requires triangle-only connectivity | Say “this implementation requires a triangulation” |
| Negative cotangents are clamped | METHODS | Partly accurate | contributions sum per edge, then aggregate is clamped | Describe aggregate clamping; do not claim it prevents all failure |
| Lower roughness means smoother | Metrics/summary/README | Misleading | scale-dependent mean neighbor-centroid residual | Rename and constrain interpretation to same scale/connectivity |
| “Shrinkage” card | Playground | Misleading label | AABB diagonal percent change only | Rename to “AABB diagonal change” |
| Surface-area change measures removed detail | Cards | Oversimplified | area is fan-triangulated; area can rise/fall for many reasons | Present as area change, not direct detail loss |
| Volume is N/A for open/non-watertight meshes | Advanced/docs | Correct as a gate, incomplete as validity | watertight only; winding/components unvalidated | State orientation/component assumptions |
| Displacement is distance from original | Cards/summary | Correct, but baseline is easy to miss | vertex-wise index correspondence | Put “from source original” in label |
| Method Comparison is fair | Comparison | Same input is correct; equal effort is not | Taubin performs two passes/iteration, others one | Call “controlled same-input,” not normalized fairness |
| “Least shrinkage” ranking | Comparison | Misleading | minimum absolute AABB change, including expansion | Use exact metric label and show ties/expansion |
| “Largest roughness reduction” ranking | Comparison | Unsupported when no method reduces/ties | unconditional max row | Only rank positive reductions and show ties |
| Noise simulates surface roughness | App | Educational approximation | Gaussian displacement scaled by global median edge length; each displacement is capped at 0.5× that global median | Explain distribution, units, cap, seed, and synthetic nature |
| Step Inspector is exact | Inspector/demo | Incorrect with constraints | ignores boundary preservation; no Taubin/local second/effective steps | Show active constraints/method or narrow the claim |
| Generated summary describes current experiment | Advanced download | Inconsistent | committed geometry + current widget settings | Generate from committed history record |

### Course material versus project extensions

The repository does not contain the lecture transcript, citations, or a syllabus mapping, so course provenance cannot be verified. The app explicitly labels polygonal meshes, connectivity, normals, neighbor-average/local smoothing, shrinkage, and boundaries as “Lecture idea” topics. Taubin smoothing, cotangent smoothing, synthetic noise, comparison rankings, and the custom metrics appear to be project extensions, but the UI/README do not distinguish them. Production-grade geometry processing is not implemented: cotangent weights are frozen and clamped, validation is structural, polygon triangulation is simplistic, and no self-intersection/manifold/winding checks are performed.

## 6. AI-slop findings

The content is not uniformly bad; the formula and many short definitions are clear. The “slop” problem is repetition and unsupported confidence rather than grammar.

- “A mesh is vertices, edges, faces” is repeated in at least four UI structures plus docs.
- Neighbor averaging, shrinkage, and boundary definitions recur in the intro, walkthrough, lecture companion, concept cards, exercises, README, methods guide, demo script, and generated summary.
- Guided Learning nests eight tabs inside a top-level tab, then adds three expanders containing more near-duplicate material.
- “Relax,” “main shape,” “geometry-aware,” “good smoothing,” and “lower is smoother” sound plausible but do not precisely identify the metric or current state.
- Rankings automatically convert one experimental table into “least” and “largest” winners even when the metrics do not justify broad method claims.
- “Lecture Notes Companion” implies lecture mapping without sources; an unmounted scribe placeholder admits transcription is absent.
- The generated summary uses generic interpretation templates and can pair them with the wrong control settings.
- `STUDENT_GUIDE.md` and `DEMO_SCRIPT.md` describe an older manual-button workflow; README documents the live/manual distinction more accurately but still repeats overbroad metric/method claims.

Recommended content model: one 5-minute guided path, one glossary, one method reference with citations/limitations, one exercise set tied to exact current controls, and interpretations generated from explicitly named A/B states.

## 7. Complete control matrix

Legend: **V** = visible geometry change, **M** = metric change, **E** = explanation/status change, **H** = committed history/state change. “Conditional” means a no-op is legitimate only when its dependency is visibly inactive.

| Control | Location | Default / tested range | Expected behavior | Actual browser/source behavior | V/M/E/H | Correct and meaningful? | Severity if not |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Source kind radio | Sidebar | Built-in; Upload | Switch source workflow | Works; source change resets geometry/history but retains experiment widgets/messages | V/M/E/H | Partial | Medium |
| Sample mesh | Sidebar | Cube; tested all four | Replace original+working with sample | Works; stale smoothing/noise can immediately preview on new source | V/M/E/H | Partial | Medium |
| OBJ uploader | Sidebar | none; valid pyramid, empty, invalid | Load valid OBJ; safe error/fallback | Valid pyramid loads as 5v/6 triangles; empty/invalid clearly error and fall back Cube | V/M/E/H | Yes | — |
| Display mode | Sidebar | Wireframe+shaded; four modes | Change rendering only | Works only in Current-only/Original-only/side cards; ignored by Overlay | V only | Partial | Blocker |
| Background | Sidebar | Light; Light/Dark | Change viewer background | Propagates to Playground modes; comparison cards hardcode white | V only | Partial | Medium |
| Show axes | Sidebar | on | Toggle axes | Works broadly | V only | Yes | — |
| Normals expander | Sidebar | closed | Reveal normal controls | Works | — | Yes | — |
| Show face normals | Sidebar | off | Red face-normal overlay | Works only Current-only; byte-identical no-op in Overlay | V only | Partial | Blocker |
| Show vertex normals | Sidebar | off | Blue vertex-normal overlay | Same mode restriction | V only | Partial | Blocker |
| Normal length | Sidebar | .25; 0/.5/1 | Scale enabled normal lines | Conditional no-op when normals off; ignored outside Current-only | V only | Partial | Medium |
| Vertex normal weighting | Sidebar | average; area-weighted | Recompute vertex normals | Conditional no-op unless vertex normals visible; ignored outside Current-only | V only | Partial | Medium |
| See shrinkage | Playground preset | button | One-click shrinkage demo | Works; 14×.5 gives -71.36% AABB, very visible in Overlay | V/M/E | Yes, though extreme | — |
| Remove noise | Playground preset | button | Denoise with limited shrinkage | Does the opposite: rougher/larger | V/M/E | No | Blocker |
| Uniform vs Taubin | Playground preset | button | Prepare noisy fair comparison | Prepares a live noise+Uniform preview, while comparison reads clean working state | V/M/E | No | Blocker |
| Boundary preservation | Playground preset | button | Demonstrate pinned border | Off/on difference is strong; on state is subtle and baseline is flat original, not unsmoothed bump | V/M/E | Partial | Medium |
| Local soft smoothing | Playground preset | button | Demonstrate localized radius/falloff | Highlight and radius work; preset falloff switch at radius 2 is an exact no-op | V/M/E | Partial | Blocker |
| Inspect one vertex | Playground preset | button | Prepare inspector example | Sets sphere/one step but does not navigate; student must open another tab | V/M/E | Mostly | Low |
| Live Preview | Playground | on; on/off | Toggle preview versus manual mutation | Works; mode changes button set. Commit immediately creates next preview | V/E | Partial | High |
| Noise enabled | Playground | off | Gate noise | Gates live noise; ignored by manual Add button | V/M/E | No across modes | Blocker |
| Noise strength | Playground | .4; tested 0/.35/1 | Scale synthetic displacement | 0 no live change; .35 and 1 visible; cap keeps finite. Manual 0 still records action | V/M/E/H | Partial | Medium |
| Noise seed | Playground | 42; tested 42/43/42 | Reproducible variation | Same seed gives identical cards/vertices; different seed differs | V/M/E | Yes | — |
| Noise mode | Playground | Along normals; Random 3D | Change displacement direction | Implemented; normal mode has degenerate fallback | V/M/E | Yes, explanation weak | Low |
| Smoothing mode | Playground | Global; Local | Switch control/algorithm family | Works; downloaded settings still describe current controls rather than an immutable committed action | V/M/E | Mostly | Medium |
| Smoothing iterations | Playground | 0; tested 0/1/5/10/20/30 | Progressive effect | Correct progression for Uniform; high values collapse mesh; positive count with λ=0 falsely counts as change | V/M/E/H | Partial | Medium |
| Smoothing λ | Playground | .3; tested 0/.1/.5/1 | Step strength | Correct for Uniform/Cotangent/Local; λ=0 still committable. For Taubin it is unsafe without μ pairing | V/M/E/H | Partial | Blocker |
| Preserve boundary vertices | Playground | on | Pin detected open border | Correct for smoothing; irrelevant on closed meshes and not honored by Inspector prediction | V/M/E | Partial | Blocker |
| Smoothing method | Playground | Uniform; three methods | Choose global method | Dispatch works; unsupported Cotangent is honest. Method alone does not guarantee comparable effect | V/M/E | Mostly | Medium |
| Taubin μ | Playground | -.53; -.95 to -.05 | Negative correction | Implemented, but unrestricted pairing can explode | V/M/E | No as exposed | High |
| Center vertex | Local | 0 on manual switch; preset chooses nearest bbox center; tested min/mid/max-valid | Move soft-selection center | Works and clamps after source switch; numeric selection is hard for novices | V/M/E | Yes but awkward | Medium |
| Soft radius | Local | 1 on manual switch; preset chooses 2; tested 1 to eccentricity | Grow affected region | Counts/highlights change; outer ring zero; max does not affect all vertices | V/M/E | Partial | Medium |
| Falloff type | Local | linear; tested linear/smoothstep | Change weight curve | Exact no-op at radii 1 and 2, including the shipped radius-2 preset; meaningful at ≥3 | V/M/E | Partial | Blocker |
| Commit preview | Playground | disabled at neutral | Promote actual preview once | Works but uses requested-change flag; accepts no-op and immediately builds same next preview | V/M/E/H | No | High |
| Add noise to current mesh | Manual mode | button | Mutate only when noise requested | Ignores Noise enabled; strength 0 records no-op | V/M/E/H | No | Blocker |
| Apply smoothing | Manual mode | button | Mutate with valid settings | Iterations 0 correctly rejected; λ=0 still recorded/counts | V/M/E/H | Partial | Blocker |
| Reset experiment | Playground | button | Recover clean state | Crashes app | E/H | No | Blocker |
| Playground view | Playground | Current only; four modes | Choose trustworthy A/B display | Overlay strongest; Side-by-side unsynced; Original-only labels/cards contradict view | V only | Partial | High |
| Top-level tabs | Main | six tabs | Navigate learning modes | Work; no lazy rendering and no clear beginner order | E | Yes, UX issue | Medium |
| Comparison iterations | Method Comparison | 10; 1/10/30 | Apply same shown count | Works, but Taubin does two passes per “iteration” | V/M/E | Partial | Medium |
| Comparison λ | Method Comparison | .5; 0/.5/1 | Shared nominal strength | Works; λ=0 is not a Taubin no-op because μ still runs | V/M/E | Misleading equivalence | High |
| Comparison μ | Method Comparison | -.53; -.95/-.53/-.05 | Set Taubin correction | Works; unsafe pairs and no validation | V/M/E | No as exposed | High |
| Comparison boundary | Method Comparison | on | Pin open borders for all methods | Works for compatible methods | V/M/E | Yes | — |
| Run comparison | Method Comparison | button | Snapshot current working input; do not mutate | Same-input and nonmutating; wrong preset input and stale after later commits | V/M/E | Partial | Blocker |
| Inspector vertex | Step Inspector | 0; min/mid/max, source switches | Select valid index | Works; out-of-range state clamps to 0 after source switch | V/E | Yes | — |
| Inspector method | Step Inspector | Uniform; Cotangent if triangle | Choose formula | Works for supported triangle input; omits Taubin/local | V/E | Partial | Medium |
| Inspector strength | Step Inspector | .5; 0/.5/1 | Update predicted point/formula | Arithmetic correct for unconstrained step | V/E | Partial | Blocker with boundary claim |
| Guided nested tabs | Guided Learning | 8 tabs | Progressive concept path | Navigation works; repeated prose and actions require tab switching | E | Partial | Medium |
| Guided expanders | Guided Learning | collapsed | Reveal concept/notes/prompts | Work; content duplicates walkthrough | E | Low value | Medium |
| Exercise expanders | Student Exercises | 7 collapsed | Reveal actionable exercises | Work; several steps use stale labels or false preset assumptions | E | Partial | High |
| Download summary | Advanced Metrics | `.md` | Download faithful committed report | Download succeeds; content can mismatch committed action settings | file/H | Function works, report untrustworthy | High |

Unmounted controls are not counted as live controls: `_render_before_after_comparison()` defines a separate “Comparison mode” selector, but that function is never called.

### Browser control test traceability

The matrix above records the verdict; this table records the values and contexts actually exercised. “Back to default” means the value was restored in the same session and the visible/metric state was checked again. It does not imply that Reset was usable.

| Control family | Default / minimum / middle / high or alternate values exercised | Related-state and source contexts | Back-to-default / state-transition result |
| --- | --- | --- | --- |
| Source and upload | Built-in; Upload; Cube, Plane/grid, Low-poly sphere, Cylinder; no file, valid `pyramid.obj`, empty OBJ, invalid text | Neutral state, after smoothing/noise controls remained set, and after source switches | Geometry/history reset on source identity change; experiment widgets/messages can remain stale. Invalid/empty upload safely falls back to Cube. |
| Display and viewer | Wireframe + shaded, Solid shaded, Wireframe, Points / vertices; Light/Dark; axes on/off | Overlay, Side-by-side, Original only, Current only; clean and changed meshes | Returning to the default display restores Current-only rendering. In Overlay, display changes are byte-identical no-ops. |
| Normal controls | Face/vertex off/on; length 0/.5/1; average/area-weighted | Cube and sphere; Overlay and Current only | Returning off removes overlays in Current only. Overlay ignores all normal settings, including visibly enabled settings. |
| Presets | All six preset buttons | Fresh source, changed source, comparison/inspector follow-up | Shrinkage and boundary presets visibly work; denoise and comparison workflows fail their promises; Inspector preset does not navigate. |
| Live/manual mode | Live Preview on/off | Neutral, noise-only, smoothing-only, commit, and manual action paths | Toggling back on rebuilds a preview from current working geometry. Commit can immediately preview the same operation a second time. |
| Noise | Enabled off/on; strength 0/.35/1; seed 42/43/42; along normals/random 3D | Live preview, manual mode, clean sphere, committed noisy sphere, and after commit | Seed 42 reproduced exactly after 42→43→42. Manual Add ignores enabled=off; strength 0 can still record an action. |
| Uniform smoothing | Iterations 0/1/5/10/20/30; λ 0/.1/.5/1; boundary on/off | Sphere, Cube, bumped grid; clean, noisy, live preview, manual, and committed state | Returning to 0 removes a live smoothing preview. λ=0 remains falsely committable/countable; high values visibly collapse. |
| Taubin smoothing | λ 0/.05/.3/.35/.5/1; μ -.95/-.53/-.05; iterations 1/10 | Clean and noisy sphere; Playground and comparison | Default-like .5/-.53 limits contraction, while allowed pairs expand or diverge; no pair guard appears when values are restored. |
| Cotangent smoothing | λ 0/.5/1; low/middle/high iteration contexts | Sphere, uploaded pyramid, Cube, and grid | Sphere/pyramid change; Cube/grid remain unchanged with an honest unsupported warning. |
| Boundary preservation | on/off/on | Bumped grid, closed sphere, global smoothing, and Step Inspector | Grid border result returns to pinned when re-enabled; closed sphere is a legitimate no-op. Inspector continues predicting motion for pinned grid vertices. |
| Local smoothing | Center min/middle/max-valid across source switches; radius 1/2/3/4; linear/smoothstep | Bumped grid, preserved/unpreserved boundary, changed source | Radius counts return correctly. Linear and smoothstep are identical at radii 1 and 2, and diverge only once interior graph distances exist. |
| Playground view | Overlay, Side-by-side, Original only, Current only | Identical, noisy, strongly shrunken, preview, and committed states | Overlay shares one frame and is strongest. Side-by-side auto-fit hides scale; Original-only retains current-preview status/cards. |
| Method Comparison | Iterations 1/10/30; λ 0/.5/1; μ -.95/-.53/-.05; boundary on/off | Clean committed sphere, committed noisy sphere, then a new same-source commit | Fresh results use one nonmutating input. Rows remain stale after the later commit; preset preview noise is not the comparison input. |
| Step Inspector | Vertex min/middle/max; λ 0/.5/1; Uniform/Cotangent where available | Cube, sphere, grid, pyramid; source switch with an out-of-range prior index | Index clamps safely. Arithmetic matches an unconstrained first pass; boundary-preserved result does not match the Inspector prediction. |
| Commit, manual buttons, Reset | Disabled neutral commit, changed commit, Add noise, Apply smoothing, Reset | Preview, committed preview, second preview, manual noise/smoothing | Commit/manual state changes were observed. Reset consistently terminates the scenario with the Streamlit exception, so no post-Reset combination could be truthfully tested. |
| Download | Current committed state; then uncommitted method change | Advanced Metrics after Uniform commit, with Learning Summary set to Taubin | File transfer succeeds. Visible history and generated settings disagree, proving state attribution is not reliable. |

The requested “interaction after Reset” matrix is blocked by AUD-001 itself: the first Reset click crashes before any dependent control can be exercised. That is recorded as a failed test, not silently treated as untested or passed. Cross-family cases after source switching, noise, and committed smoothing were exercised as listed above.

### Navigation and disclosure inventory

Every rendered top-level tab, nested walkthrough tab, and exercise expander was opened in the browser. Aggregating them into one matrix row above does not mean they were sampled as one control.

| Rendered control | Browser result | Content/meaning verdict |
| --- | --- | --- |
| Top tab — Playground | Opens and remains interactive | Primary workflow, but no clear first step and excessive vertical separation |
| Top tab — Method Comparison | Opens; Run produces cards/table | Fresh calculation works; intended noisy input and later invalidation fail |
| Top tab — Step Inspector | Opens; selectors and viewer update | Strong numeric teaching surface; boundary context is incorrect |
| Top tab — Guided Learning | Opens; nested controls work | Content is repetitive and separated from the experiment controls |
| Top tab — Student Exercises | Opens; all seven exercises reveal | Several workflows/expected results are stale or false |
| Top tab — Advanced Metrics | Opens; table/history/download render | Dense but useful; downloaded setting attribution can be stale |
| Guided tab 1 — Polygonal Mesh | Opens | Basic definition; duplicates concept cards/notes |
| Guided tab 2 — Connectivity | Opens | Correct basic idea; no direct one-ring demonstration |
| Guided tab 3 — Normals | Opens | Oversimplifies winding/nonplanarity; tells user to switch tabs |
| Guided tab 4 — Smoothing | Opens | Useful basic rule; categorical language and no synchronous-update caveat |
| Guided tab 5 — Shrinkage | Opens | Useful concept, but phrased too generally |
| Guided tab 6 — Boundaries | Opens | Good one-face-edge introduction; limitations absent |
| Guided tab 7 — Local | Opens | Useful brush analogy; graph-step and zero outer-ring semantics absent |
| Guided tab 8 — Compare | Opens | Sends user to another tab; Taubin and ranking claims need qualification |
| Guided outer expander — Lecture concept cards | Expands/collapses | Contains six more expanders that repeat walkthrough content |
| Guided outer expander — Observation prompts | Expands/collapses | Brief generic prompt; no current-state measurement |
| Guided outer expander — Lecture notes companion | Expands/collapses | Contains eight more expanders and duplicates the same concepts again |
| Concept-card expander — Polygonal Mesh | Expands/collapses | Correct basic definitions; repeats Guided tab 1 |
| Concept-card expander — Mesh Connectivity | Expands/collapses | Correct basic idea; repeats Guided tab 2 |
| Concept-card expander — Normals | Expands/collapses | Useful distinction, with winding/nonplanarity caveats absent |
| Concept-card expander — Neighbor-Average Smoothing | Expands/collapses | Gives λ intuition; “more iterations” is too categorical |
| Concept-card expander — Shrinkage | Expands/collapses | Useful observation; repeats Guided tab 5 |
| Concept-card expander — Boundary Preservation | Expands/collapses | Useful basic rule; overstates prevention of collapse |
| Lecture-companion expander — Polygonal Mesh | Expands/collapses | Repeats the top guided tab and concept card |
| Lecture-companion expander — Mesh Data and Connectivity | Expands/collapses | Repeats connectivity material with app-action mapping |
| Lecture-companion expander — Face Normals | Expands/collapses | App action is usable only in compatible view modes |
| Lecture-companion expander — Vertex Normals | Expands/collapses | App action is usable only in Current-only mode |
| Lecture-companion expander — Neighbor-Average Smoothing | Expands/collapses | Actionable, but still separated from Playground controls |
| Lecture-companion expander — Local / Soft Smoothing | Expands/collapses | Repeats local material; graph semantics remain incomplete |
| Lecture-companion expander — Repeated Smoothing and Shrinkage | Expands/collapses | Useful observation, duplicated across several structures |
| Lecture-companion expander — Boundary Preservation | Expands/collapses | Actionable grid suggestion; duplicates exercise and guided tab |
| Exercise 1 — Topology stays fixed | Expands/collapses | Actionable, but UI only proves count preservation |
| Exercise 2 — Shrinkage | Expands/collapses | Actionable and produces a strong visible result |
| Exercise 3 — Boundary preservation | Expands/collapses | Actionable; sequential comparison requires remembering the prior state |
| Exercise 4 — Noise removal | Expands/collapses | Expected outcome is false at the shipped preset |
| Exercise 5 — Method comparison | Expands/collapses | Omits the commit needed to compare the intended noisy input |
| Exercise 6 — Local soft smoothing | Expands/collapses | Visible highlight helps; radius/falloff semantics are incomplete |
| Exercise 7 — Step inspector | Expands/collapses | Actionable, but “predicted” does not match pinned boundary behavior |

## 8. Novice student journey

### Can the app answer the novice’s 20 questions?

| # | Question | What a novice can learn from the app | Verdict |
| --- | --- | --- | --- |
| 1 | What is a polygonal mesh? | Vertices, edges, faces | Partial; no geometry/connectivity distinction |
| 2 | What are vertices, edges, faces? | Points, connections, polygon patches | Good basic answer |
| 3 | What is connectivity? | Which elements touch; neighbors form a one-ring | Partial; “one-ring” not directly demonstrated |
| 4 | Why use neighbors? | A vertex moves toward connected-neighbor average | Partial; no diffusion intuition |
| 5 | What happens to one vertex? | Inspector formula/list/point | Strong for unconstrained Uniform; wrong for pinned boundaries |
| 6 | What does λ control? | Fraction of move toward target | Good basic answer; no stability/pairing context |
| 7 | Why shrinkage? | Repeated averaging pulls inward | Useful and visually strong in Overlay |
| 8 | What is noise? | Controlled normal/random displacement | Weak: no units/distribution/cap/seed explanation |
| 9 | What does Taubin change? | Adds negative correction pass | Partial; valid λ/μ pairing not taught |
| 10 | How is cotangent different? | Triangle angles weight neighbors | Good basic contrast; simplifications hidden |
| 11 | Why triangles here? | App only says it is triangle-only | Insufficient; opposite-angle construction is not connected to restriction |
| 12 | What is boundary preservation? | One-face edge vertices are pinned | Good basic answer; scope overstated |
| 13 | What is local/soft smoothing? | Center-weighted soft brush | Good basic answer |
| 14 | What is graph radius? | Labeled “graph steps” | Weak; does not define crossing one edge or zero outer ring |
| 15 | What is roughness energy? | Mean distance to neighbor average | Formula given; name/interpretation misleading |
| 16 | Why can roughness fall while preservation worsens? | Compare roughness with size cards | Partial; scale confounding not taught |
| 17 | How compare methods fairly? | Same starting working copy | Partial; preset baseline and work-per-iteration problems |
| 18 | What should I look at? | Inward motion, boundaries, overlay, highlights | Useful but distributed across tabs |
| 19 | Which values first? | Presets suggest values | No coherent safe parameter guide; one preset is false |
| 20 | How recover? | Reset experiment | Answer exists but the button crashes |

### Required novice tasks

| Task | Discoverable? | Actions | Scrolling | Visual result | Explanation | Likely misunderstanding |
| --- | --- | ---: | --- | --- | --- | --- |
| A. Understand shrinkage preset | Yes; first preset | 1 | None initially | Very obvious in Overlay | Nearby and adequate | May equate “roughness reduction” with good smoothing despite collapse |
| B. Add noise and remove some | Yes; preset named exactly | 1 | None initially | Visible, but final expands/roughens | Explicitly claims intended denoising | Student learns a false result |
| C. Compare Uniform and Taubin | Yes | 3 as instructed; ≥5 for a true noisy baseline | Tab switch | Cards clear | Same-input text is clear but baseline hidden | Believes noisy preset fed comparison when it did not |
| D. Understand one vertex | Yes via preset+tab | 2 | Table may require scroll | Selected/neighbors/prediction clear | Best formula explanation | Believes prediction includes boundary rules/all methods |
| E. Understand boundary preservation | Preset is clear | 2–3 | Must scroll to lower checkbox; explanation scrolls away | Off/on difference obvious | General explanation correct | Does not know preset bump baseline; assumes all collapse prevented |
| F. Use local smoothing | Preset is clear | 2+ | Must scroll to radius/falloff; explanation scrolls away | Highlights/counts clear | Graph semantics incomplete | Expects falloff at radius 2 to change something |

Suitability estimates:

- 5-minute instructor-led demo: **6/10**, if Reset and Remove noise are avoided.
- 20-minute self-guided lab: **4/10**.
- Homework companion: **4/10** because the downloadable report can be inconsistent.
- Without an instructor: **3/10** because recovery and two central explanations are untrustworthy.

## 9. Explanation-proximity findings

| Experiment/control | Control/explanation placement | Must scroll or remember? | Viewer visible with control? | Current-state or generic? | Says what to look for / why subtle? | Nearby metrics or unexplained-table burden | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Noise strength | Control low in left column; theory in right column above | Yes after normal page scroll; student must remember clean/noisy state | Sticky viewer remains visible | Status has current strength, but theory omits actual σ, cap, and direction details | No; it does not explain saturation or why low values are subtle | Quick cards are farther down and use source-original, not noisy-before, baseline | Weak |
| Noise seed | Beside other noise controls; no dedicated explanation | Yes; must remember previous seed/result to compare reproducibility | Yes while control is reached | No seed-specific dynamic explanation or status interpretation | No; it never says same seed should reproduce or what visual region to compare | Cards change, but no plain-language seed interpretation | Weak |
| Smoothing method | Selector in lower left; method notes in upper/right explanation block | Yes; method notes scroll off while selector remains | Sticky viewer remains visible | Notes switch by method but stay generic | Partly; broad effect only, no warning that a small change may be hard to see | Quick cards are separated; comparison table is in another tab | Partial |
| Iterations | Lower-left slider; explanation above/right | Yes; at `scrollTop≈965`, explanation was ≈668 px above viewport | Yes | Status includes current count | General “more smoothing,” but no subtle-change cue at 1 iteration or collapse warning at high values | Metric cards were ≈186 px above viewport in the measured scroll state | Poor |
| λ | Lower-left slider; fuller fraction-of-motion explanation is in Guided Learning/Inspector, not the nearby dynamic explanation | Yes; must retain prior λ to judge progression or change tabs for the definition | Yes | Status includes λ, not current risk/effect size | No; no cue for λ=0 no-op, λ=1 severity, or interaction with method | Cards are off-screen; no pair-specific summary | Poor |
| Taubin μ | Conditional lower-left slider; generic bullet elsewhere | Yes; must remember λ and prior shape | Yes | Only generic “negative correction,” not current λ/μ interpretation | No; expansion/instability can be dramatic yet is not predicted or warned | No nearby safety metric; table/ranking elsewhere can legitimize bad output | Poor |
| Boundary preservation | Checkbox lower left; explanation above/right and in other learning tabs | Yes; off/on result is sequential, so prior border shape must be remembered | Yes | Status/card updates, but explanation is general | Partly tells user the border should stay fixed; does not explain closed-mesh no-op/subtlety | Boundary-motion card is lower and can be off-screen | Partial/poor |
| Local center vertex | Lower-left local controls; selection summary beneath them | Little extra scrolling within control group, but prior center result must be remembered | Yes, with highlight | Counts are current; theory is generic | Highlight shows where to look; numeric vertex index is not visually mapped before selection | Small affected/movable table is nearby and interpretable | Partial |
| Local radius | Adjacent to center/falloff and summary | Sequential radius comparison requires memory | Yes, with highlight | Counts update for current radius | Yes for region growth; no explanation that the outer ring has zero weight | Nearby count summary helps; geometry cards use flat source baseline | Partial |
| Local falloff | Adjacent to local controls | Must remember the previous curve result | Yes | Label/status changes, explanation is formula-free | No warning that linear/smoothstep are exactly identical at radii 1–2, so visible no-change looks broken | Count table does not reveal equal weights/geometry | Poor |
| Method Comparison | Controls, result cards, captions, then table in one tab | Some vertical scrolling; no need to retain another page when result is fresh | Yes for result cards, not all rows simultaneously | Fresh rows/captions are current; stored results can silently become stale | Captions identify input/result, but not why differences may be subtle or unsafe | Dense table is explained only by overclaiming rankings; several columns require prior metric knowledge | Good placement, weak trust |
| Step Inspector | Selectors above viewer; formula and neighbor table adjacent | Minimal; formula/table follow directly | Yes | Numeric values are current | Clearly identifies current point, neighbors, target, and prediction | Formula/table are nearby and readable | Best proximity, but boundary context makes the “exact” result false |

Control-to-explanation score: **4/10**. The three-column concept is directionally right, but only the viewer is sticky. Explanations are generic method summaries rather than parameter- and baseline-specific interpretations, and lower controls cannot be seen with the explanatory heading or first metrics.

## 10. Before/after findings

| Scenario | Starting state | Result A | Result B | Visual clarity | Explanation clarity | Metric clarity/correctness | Issues |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Clean vs noisy | Clean sphere | Original wireframe | Seed-42 noise .35 | Good in Overlay | Generic | Correct versus source original | No stored noisy baseline for next stage |
| Noisy vs Uniform | Committed noisy sphere | Saved comparison input | Uniform result | Available in Method Comparison after explicit noise commit; absent in Playground preview | Comparison caption is generic | Comparison metrics use noisy input; Playground reports clean→final | Default preset omits required commit; result can become stale |
| Noisy vs Taubin | Committed noisy sphere | Saved comparison input | Taubin result | Available in Method Comparison after explicit noise commit; false preset path does not create this input | Preset claim is false | Fresh comparison metrics use noisy input; Playground cards hide denoising stage | Blocker preset and no persistent three-state sequence |
| Uniform vs Taubin | Clean or committed noisy | Each card overlays same input | Separate result cards | Visually useful | Captions concise | Internally same baseline when freshly run | Not a direct A/B pair; equal iterations ≠ equal work |
| Boundary off vs on | Bumped grid preview | Toggle off | Toggle on | Strong difference, but sequential only | General text | Boundary motion card correct | Must remember prior state; no saved A/B |
| Local radius 1 vs 3 | Bumped grid preview | Center only | 13 highlighted/9 movable | Clear highlight growth | Counts helpful | Cards relative to flat source | No simultaneous A/B; outer ring semantics absent |
| Original vs committed | After commit | Source original | Working mesh | Available | Labels generally clear | Advanced metrics correct | Live preview immediately applies same controls again, obscuring committed state |
| Original vs live preview | Any preview | Source original | Active preview | Overlay is strongest mode | Status clear | Cards named too generically | Original-only mismatch; displacement clutter at extremes |
| Side-by-side | 71.36% AABB-diagonal contraction | Auto-fit original | Auto-fit preview | Misleadingly similar size | Labels present | Metric says -71.36% | Cameras/scale unsynchronized |

Before/after score: **4/10**. Overlay provides a strong shared-camera original-vs-current view, clear black/blue/orange differentiation, and obvious shrinkage. A deliberately committed noisy input can also be compared with method results in a freshly run Method Comparison. No obvious z-fighting was observed in the tested overlays; at extreme displacement the overlapping wireframe/shaded layers can still become visually cluttered. The default preset/state model and side-by-side implementation still prevent a trustworthy persistent clean/noisy/smoothed sequence or direct Playground working-input/preview comparison.

## Required runtime scenarios

| Scenario | Result | Evidence and notes |
| --- | --- | --- |
| 1. Fresh start | **Partial pass** | Clean Cube, zero metrics, disabled Commit, clear neutral status. No explicit first experiment; initial console has warning noise. [Screenshot](screenshots/fresh_default_desktop_loaded.png) |
| 2. Uniform live controls | **Pass with issues** | Browser tested iterations 0/1/5/10/20 and λ 0/.1/.5/1. Progressive geometry/metrics are correct; λ=0 is falsely committable; high settings nearly collapse the sphere. [1 iteration](screenshots/uniform_low_1_overlay.png), [20 iterations](screenshots/uniform_20_overlay.png) |
| 3. Taubin | **Fail educationally** | λ=.5/μ=-.53 reduces contraction versus Uniform, but preset λ=.35/μ=-.53 expands/roughens; unsafe pairs have no warning. [Comparison](screenshots/method_comparison_clean_despite_noisy_preset.png) |
| 4. Cotangent | **Pass support handling; partial algorithm teaching** | Sphere and imported pyramid change; Cube/grid show honest unsupported warning and unchanged cards. Uploaded pyramid is triangulated from authored mixed faces. [Supported](screenshots/cotangent_supported_sphere.png), [unsupported](screenshots/cotangent_unsupported_cube.png) |
| 5. Noise | **Pass core reproducibility; partial lesson** | Seed 42 repeated exactly; seed 43 differs. Strength 0/.35/1 remains finite and topology counts fixed. A noise-only commit can temporarily store exact noisy geometry as `working_mesh`, but no dedicated persistent named noisy-before baseline or Playground working→preview comparison exists. [Screenshot](screenshots/noisy_sphere_seed42_strength035.png) |
| 6. Boundary preservation | **Pass effect; partial baseline** | Off: -70.12% AABB and boundary moved Yes. On: boundary moved No and +0.00% AABB. The temporary teaching bump is disclosed in the preset/status/explanation, but metrics still use the flat source as baseline. [Off](screenshots/boundary_preservation_off.png), [on](screenshots/boundary_preservation_on.png) |
| 7. Local/soft | **Partial pass** | Radii 1/2/3/4 change counts 1/5/13/21; max has 9 movable after boundary rules. Linear/smoothstep identical at 1/2, meaningful at 3/4. [Radius 1](screenshots/local_radius_1.png), [radius 3](screenshots/local_radius_3_smoothstep.png) |
| 8. Step Inspector | **Fail exactness claim** | Neighbor arithmetic correct on Cube, sphere, grid, pyramid; index clamps after source switch; grid boundary prediction contradicts actual pinned result. [Screenshot](screenshots/step_inspector_boundary_mismatch_grid_vertex0.png) |
| 9. Method Comparison | **Partial pass** | Same saved input and nonmutating when run. Clean and committed-noisy runs produced internally consistent rows; preset input and later-staleness behavior fail. [Clean](screenshots/method_comparison_clean_despite_noisy_preset.png), [noisy](screenshots/method_comparison_committed_noisy_input.png) |
| 10. Reset and commit | **Fail** | Reset crashes. Commit works but immediately previews the same enabled operation again; noise-only history is mislabeled as Uniform. [Reset](screenshots/broken_reset_streamlit_exception.png), [commit](screenshots/broken_commit_immediately_previews_second_noise.png) |
| 11. Invalid OBJ | **Pass** | Empty: explicit empty-file error; invalid text: no-usable-faces error; both safely fall back to Cube with no stale invalid geometry. [Screenshot](screenshots/invalid_obj_safe_fallback.png) |
| 12. Narrow viewport | **Fail usability expectation** | No horizontal overflow, but three columns remain, labels break midword, explanation is too narrow, sidebar is hidden, and scrolling is excessive. [Screenshot](screenshots/narrow_viewport_768.png) |

## 11. Algorithm correctness findings

| Component | Verdict | Evidence / caveat |
| --- | --- | --- |
| Mesh representation | Structurally sound | Finite Nx3 vertices and indexed polygon loops; validation does not check degeneracy, duplication, manifoldness, winding, or self-intersection |
| Unique edges/adjacency | Correct for polygon boundary loops | Symmetric one-ring adjacency; stable sorted lists used by inspector |
| Boundary detection | Correct for ordinary manifold inputs | One-face edges; non-manifold edges with count >2 are not treated specially |
| Face normals | Correct teaching implementation | Oriented triangle-fan area vector; zero on degeneracy; nonplanar, degenerate, or self-intersecting face ambiguity remains |
| Vertex normals | Correct labels/implementation | Equal incident-face and area-weighted modes normalize safely |
| Uniform Laplacian | Correct | Fully synchronous update; λ clipped to [0,1]; boundary pinning correct |
| Taubin sequence | Structurally correct | Positive synchronous λ pass then negative μ pass; no parameter-pair validation, so UI claims fail for many allowed pairs |
| Cotangent calculation | Correct simplified formula | Half-cotangent contributions; degenerates contribute zero; aggregate negative edge weight clamped |
| Cotangent normalization | Correct for the chosen simplified smoother | Row-normalized neighbor target; not a mass-matrix Laplace–Beltrami discretization |
| Cotangent iteration | Simplification not disclosed | Weight map is computed once from initial geometry and reused through all iterations |
| Degenerate handling | Safe but scale-sensitive | Absolute `1e-12` threshold makes geometrically similar tiny meshes behave differently |
| Local graph distance | Correct | Unweighted BFS edge-hop distance |
| Linear/smoothstep falloff | Formula correct | Integer distances make both identical at radii 1/2; exactly-at-radius ring has weight zero |
| Local smoothing | Correct synchronous weighted Uniform | Weights fixed from original connectivity, as expected; boundary pinning correct |
| Noise | Correct deterministic synthetic displacement | Global-median-edge scaling, Gaussian samples, each displacement capped at 0.5× that median, normal/3D modes; UI does not teach these facts |
| Step Inspector arithmetic | Correct for unrestricted first step | Omits boundary constraints, Taubin’s second step, and local effective weight |
| Method dispatcher | Correct support signaling | Unsupported Cotangent returns unchanged clone and note; UI handles it honestly |

Selected numerical results on the built-in low-poly sphere:

| Method/settings | Roughness residual change | AABB diagonal change | Area change | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Uniform, 1×.5 | -8.17% | -8.86% | -16.23% | Visible mild contraction |
| Uniform, 10×.5 | -58.63% | -59.13% | -83.06% | Residual improvement nearly tracks collapse |
| Uniform, 20×1 | -97.58% | -97.61% | -99.94% | Near-total collapse within allowed UI values |
| Taubin, 10×(.5,-.53) | -1.96% | -3.14% | -4.87% | Sensible shrinkage-reduced pair |
| Taubin, 10×(.35,-.53) | +28.80% | +27.79% | +64.75% | Clean sphere expands/roughens |
| Taubin, 10×(.05,-.95) | +11,515.23% | +1,952.90% | +84,609.44% | Unstable/expansive allowed pair |
| Cotangent, 5×.3 | -22.32% | -23.02% | -40.13% | Supported but strongly contractive |

## 12. Metric correctness findings

| Metric | Implementation | What is correct | Trust problem / required label |
| --- | --- | --- | --- |
| Vertex/face/edge counts | Direct counts and unique polygon edges | Correct for displayed mesh | “Topology changed?” only tests counts; rename to “Topology counts changed?” |
| Average/max displacement | Same-index Euclidean displacement | Correct when both meshes retain identical vertex indexing/correspondence | Baseline is caller-specific: source original in Playground/Advanced/history, stored comparison input in Method Comparison; label it explicitly |
| AABB diagonal % | Axis-aligned min/max diagonal | Numerically correct | Not a general shrinkage/volume measure; orientation/anisotropy sensitive |
| Surface area % | Trimesh over fan-triangulated polygons | Correct for built-in planar convex faces and already-valid triangle meshes as represented | Concave/nonplanar arbitrary polygons can be wrong; not a direct feature-loss score |
| Volume % | Absolute Trimesh signed volume if watertight | Correct for consistently oriented closed built-ins | Watertightness alone is insufficient; components/winding can cancel or inflate |
| Mean roughness | Mean distance to neighbor centroid | Implementation matches displayed formula | Scale-, sampling-, boundary-, valence-, and curvature-dependent; not an “energy” in the usual squared/integrated sense |
| Max/RMS roughness | Max/RMS of same residual | Numerically correct | Inherits same interpretation limitations |
| Boundary average movement | Original-boundary displacement | Correct for comparable open meshes | Baseline is source original; “Boundary moved?” threshold fixed at 1e-6 |
| Percent change | `(current-original)/original` with guards | Correct finite/near-zero handling | Meaning depends on trustworthy base metric |
| Rankings | minimum absolute AABB; maximum reduction | Deterministic | Labels overclaim; no tie/no-reduction handling; equal iterations do not equal effort |

Metric baseline map:

```text
Playground cards: source original -> active live preview/current
Advanced Metrics: source original -> committed working
Method Comparison: stored comparison input -> each stored result
History roughness: immediate pre-action -> post-action
History size/displacement: source original -> accumulated committed result
```

That mixture is not explained clearly enough. Every metric group should name both A and B states in its heading.

## 13. State-management findings

Positive aspects:

- Source original and committed working geometry are deep copies.
- Live preview derives from a working clone and does not mutate working until Commit.
- Method Comparison clones its input and does not mutate working.
- Source-key hashing includes upload bytes, so different uploads with the same name are distinct.
- Inspector state is clamped after source switches.

Failures:

- Reset mutates widget-backed session state too late and crashes.
- Commit leaves one-shot operations enabled and immediately previews the next application.
- No named noisy/pre-action geometry is retained.
- Comparison results lack a working-version key and become stale.
- Source switching resets geometry but not experiment controls/messages.
- Preview keys are unused, so state names imply persistence the UI does not consume.
- A noise-only commit is stored as the currently selected smoothing method with its λ.
- Download settings are read from current widgets rather than the history action that produced geometry.
- Original-only changes only the iframe; status/explanation/metrics continue to track active preview.

State predictability rating: **4/10**.

## 14. Responsive-layout findings

At 768×900:

- sidebar collapses behind a small chevron, hiding source and viewer controls;
- the six top tabs remain a dense single row;
- three main columns remain instead of stacking;
- top-level controls receive ~168 px, viewer rail ~291 px, explanation rail ~150 px;
- preset names break inside words across up to five lines;
- the large page title consumes a substantial first viewport;
- main scroll height reaches ~2,562 px before exploring other tabs;
- there is no horizontal overflow, but avoiding clipping is not equivalent to usable responsive design.

The narrow viewport is technically operable, but it does not meet the requested standard that controls, viewer, explanation, and cards remain comfortably usable.

## 15. Bugs and no-op controls

### Confirmed bugs

- Reset crash (AUD-001).
- False Remove noise preset (AUD-002).
- Incorrect boundary-aware inspector claim/result (AUD-004).
- Wrong preset baseline in Method Comparison (AUD-005).
- Post-commit double preview (AUD-006).
- Stale stored Method Comparison (AUD-010).
- Committed-summary settings can be false (AUD-012).
- Original-only label/status mismatch (AUD-017).

### Expected conditional no-ops

- normal length/weighting while the corresponding normal overlay is off;
- noise parameters while Noise enabled is off in live mode;
- smoothing parameters while iterations are 0;
- boundary preservation on a closed mesh with no detected boundary;
- display-only controls do not change geometry/metrics.

### Problematic or undisclosed no-ops

- Display mode in Overlay (browser iframe screenshot unchanged).
- Face/vertex normals and normal settings outside Current-only.
- Linear versus smoothstep at local radius 1 or 2.
- Uniform/Cotangent/Local λ=0 marked changed, committable, and countable.
- Manual noise strength 0 recorded as an action.
- Noise enabled checkbox ignored by manual Add.
- Smoothing an equilibrium or fully pinned affected region can be recorded despite no vertex movement.
- Original-only intentionally suppresses all visible geometry feedback while preview cards continue changing.

## 16. Misleading or useless controls

| Control | Why misleading/useless | Disposition |
| --- | --- | --- |
| Remove noise preset | Claims verified success but produces verified failure | Block release; retune or remove |
| Reset experiment | Advertised recovery action crashes | Block release; fix first |
| Taubin μ independent full range | Parameter pairs have no safety guidance and can explode | Replace with validated paired presets + advanced override |
| Falloff at radius ≤2 | Two choices are exactly equivalent | Disable with explanation or require radius ≥3 |
| Noise enabled in manual mode | Does not gate Add button | Unify semantics or remove checkbox in manual mode |
| Display/normals in Overlay | UI accepts values with no visible effect | Disable/hide per view |
| Side-by-side | Implies trustworthy scale comparison while auto-fitting separately | Fix camera or remove until fixed |
| Original-only | Surrounding UI still describes preview | Relabel all dependent content or isolate metrics |
| “Topology changed?” | Tests counts only | Rename |
| “Shrinkage” | Measures AABB diagonal only | Rename |
| “Roughness energy” | Overclaims a scale-dependent residual | Rename/normalize |
| Automatic ranking | Produces winners without tie/no-improvement logic | Replace with literal observations |

## 17. Valuable controls and features

These features are worth keeping after the blockers are fixed:

- **See shrinkage preset + Overlay:** one-click, highly visible, and numerically consistent.
- **Live Preview separation:** the clone-based concept is good and safe before Commit.
- **Deterministic noise seed:** reproducibility passed browser and numerical checks.
- **Boundary toggle:** the off/on difference is strong and boundary motion card is useful.
- **Local center/radius highlights:** red center, orange region, affected/movable counts create a useful spatial mental model.
- **Step Inspector visual and formula:** selected/neighbors/predicted coloring and numerical table are excellent once constraints are honored.
- **Honest Cotangent unsupported state:** no hidden fallback; unchanged geometry and clear warning.
- **Method Comparison saved input:** internally consistent and nonmutating when freshly run.
- **Invalid-upload fallback:** clear errors and safe Cube fallback.
- **Advanced history:** rich raw evidence, though it needs more compact presentation and truthful action labels.
- **Markdown download transport:** the action works reliably; content/state provenance needs repair.

## 18. Features that should be simplified

- Reduce Playground quick cards to the two or three metrics relevant to the current lesson.
- Replace six equal presets with a numbered beginner path plus a “More experiments” expander.
- Collapse sidebar statistics into a compact row/table.
- Merge Guided Walkthrough, concept cards, lecture companion, and exercises; remove repeated definitions.
- Replace unrestricted Taubin λ/μ sliders with 2–3 validated pairs and an advanced disclosure.
- Replace automatic method winners with a small observation summary that names the exact metric and baseline.
- Shorten the smoothing history table; put method-specific parameters in a detail expander/download.
- Remove dead render functions and unused preview/comparison state.
- Use one explicit comparison component rather than separate mounted/unmounted implementations.

## 19. Features that should be moved or hidden

- Move Taubin μ, cotangent implementation details, noise mode/seed, and normal weighting behind **Advanced settings** until introduced.
- Keep the active experiment’s short explanation and relevant metrics with the sticky viewer.
- Move the full metric tables/history/download to Advanced Metrics, but add a direct link from each quick card.
- Move Guided Learning to the first/start experience or embed a three-step first experiment in Playground.
- Hide/disable normal and display controls when the chosen view mode ignores them.
- Hide falloff choice when graph distances make both choices identical.
- Hide Method Comparison results or mark them stale immediately after working-state mutation.
- Keep course-core concepts separate from project extensions and implementation limitations.

## 20. Recommended fix order

### P0 — Release blockers

1. Fix Reset without same-run widget-state mutation; add a browser regression test.
2. Remove or retune the false Remove noise preset; assert its noisy-before/final metrics in a test.
3. Rename/qualify roughness everywhere, including rankings and downloaded summary.
4. Make Step Inspector honor boundary pinning or narrow its claim and show constraints.
5. Make the Uniform-vs-Taubin preset feed the displayed intended noisy input to comparison.
6. Disable, hide, or implement display/normal controls in every view mode where they are currently exposed.
7. Define graph radius/falloff semantics and disable or explain equivalent falloffs at radius 1–2.
8. Make Noise enabled govern manual Add noise and reject zero-strength actions.
9. Compare actual vertices before enabling Commit or recording any smoothing action.

### P1 — Restore state and comparison trust

10. Define explicit source/working/noisy/preview snapshots and metric baselines.
11. Stop reapplying operations immediately after Commit.
12. Invalidate/version stored comparison after every working mutation.
13. Generate reports from committed action records.
14. Synchronize side-by-side cameras/world bounds; correct Original-only labels.

### P2 — Control safety and UX

15. Validate/constrain Taubin parameter pairs and warn on excessive expansion.
16. Clear or explicitly reconcile experiment controls/messages on source switch.
17. Make the explanation/metric summary sticky with the viewer.
18. Add a real responsive stack breakpoint.

### P3 — Content and engineering polish

19. Correct README metric/method claims and rewrite the student/demo instructions for the live-preview workflow.
20. Consolidate repetitive educational sections and add method citations/provenance.
21. Disclose algorithm/metric assumptions: frozen cotangent weights, fan triangulation, winding, manifoldness, and scale.
22. Lazy-render heavy tab viewers and remove zero-size WebGL warning noise.
23. Add unit tests for algorithms/metrics and Playwright tests for every state transition listed in this audit.

## Screenshot index

- Fresh: [initial page before viewer iframe completion](screenshots/fresh_default_desktop.png), [fully loaded desktop](screenshots/fresh_default_desktop_loaded.png), [768 px](screenshots/narrow_viewport_768.png)
- Uniform: [1 iteration](screenshots/uniform_low_1_overlay.png), [14 iterations](screenshots/uniform_high_14_overlay.png), [20 iterations](screenshots/uniform_20_overlay.png)
- Noise/Taubin: [raw noise](screenshots/noisy_sphere_seed42_strength035.png), [false denoise](screenshots/broken_remove_noise_preset_rougher_larger.png), [Taubin expansion](screenshots/taubin_allowed_parameters_expand_177_percent.png)
- Boundary/local: [boundary on](screenshots/boundary_preservation_on.png), [boundary off](screenshots/boundary_preservation_off.png), [radius 1](screenshots/local_radius_1.png), [radius 3](screenshots/local_radius_3_smoothstep.png)
- Cotangent/inspector: [supported sphere](screenshots/cotangent_supported_sphere.png), [unsupported Cube](screenshots/cotangent_unsupported_cube.png), [pyramid upload](screenshots/cotangent_supported_uploaded_pyramid.png), [boundary mismatch](screenshots/step_inspector_boundary_mismatch_grid_vertex0.png)
- Comparison: [wrong clean input](screenshots/method_comparison_clean_despite_noisy_preset.png), [committed noisy input](screenshots/method_comparison_committed_noisy_input.png), [table/ranking](screenshots/method_comparison_table_ranking.png), [unsynced side-by-side](screenshots/before_after_side_by_side_unsynchronized_autofit.png)
- State/control failures: [reset crash](screenshots/broken_reset_streamlit_exception.png), [double noise after commit](screenshots/broken_commit_immediately_previews_second_noise.png), [manual noise ignores checkbox](screenshots/manual_noise_disabled_but_applied.png), [zero λ committable](screenshots/broken_zero_lambda_committable.png), [stale comparison](screenshots/method_comparison_stale_after_new_commit.png), [summary method mismatch](screenshots/download_summary_method_mismatch.png), [Overlay controls ignored](screenshots/overlay_points_and_normals_selected_no_effect.png), [Original-only mismatch](screenshots/original_only_but_preview_status_metrics.png), [explanation off-screen](screenshots/control_visible_explanation_scrolled_away.png)
- Content structure: [nested learning repetition](screenshots/guided_learning_nested_repetition.png)
- Upload: [invalid fallback](screenshots/invalid_obj_safe_fallback.png)

## Final answer to the six primary audit questions

1. **Is it visually good?** Partly. It has coherent styling and useful 3D visuals, but hierarchy, density, responsive behavior, and side-by-side scale trust are not good enough for presentation.
2. **Is all educational/technical information correct?** No. Uniform basics are strong, but the denoising preset, roughness interpretation, boundary inspector, Taubin generalizations, rankings, report attribution, and several simplifications are misleading or false.
3. **Does every control produce a meaningful correct result?** No. Reset crashes; several view controls, falloff settings, and zero-strength actions are no-ops; manual noise contradicts its checkbox; stored comparison can be stale.
4. **How much would it help a complete beginner?** It can establish the basic neighbor-average/shrinkage idea, but false results and broken recovery cap it at **4/10** without an instructor.
5. **Can the student see immediate change and nearby explanation?** Sometimes at the top of Playground. Lower controls retain the sticky viewer but lose the explanation and cards entirely.
6. **Is before/after clear and trustworthy?** Overlay is clear for source-original versus current. The overall comparison system is not trustworthy for noisy→smoothed or side-by-side scale comparison.
