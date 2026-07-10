# Runtime and Numerical Probe Trace

This file records compact reproduction data supporting `FULL_PROJECT_AUDIT.md`. It is not a substitute for the issue register or screenshots.

## Environment and launch

- Audit date: 2026-07-10 (Asia/Jerusalem)
- Python: 3.13.6
- Streamlit: 1.58.0
- NumPy: 2.5.0
- Trimesh: 4.12.2
- PyVista: 0.48.4
- Panel: 1.9.3
- Compile check: `python -m compileall .` passed.
- Runtime command: `python -m streamlit run app.py --server.headless true --server.port 8501 --server.address 127.0.0.1 --browser.gatherUsageStats false`
- Browser viewports: 1440×1000 and 768×900.
- Product source changes: none.

## Browser-state probes

| Probe | Observed result | Evidence |
| --- | --- | --- |
| Reset | Clicking **Reset experiment** raises `StreamlitAPIException`: `st.session_state.noise_enabled` cannot be modified after widget instantiation. | [UI](screenshots/broken_reset_streamlit_exception.png), [server log](streamlit_stdout.log) |
| Remove noise preset | Browser cards versus clean source: roughness +31.84%, AABB diagonal +33.20%, area +74.36%. | [Screenshot](screenshots/broken_remove_noise_preset_rougher_larger.png) |
| Commit with live controls left enabled | Noise-only commit is followed by a new noise preview: visible roughness change grows from +23.63% before commit to +101.72% after commit. | [Screenshot](screenshots/broken_commit_immediately_previews_second_noise.png) |
| Manual noise gating | With Live Preview off and **Noise enabled** unchecked, **Add noise to current mesh** still changes the mesh; Cube AABB diagonal +30.97%. | [Screenshot](screenshots/manual_noise_disabled_but_applied.png) |
| Comparison preset input | Uniform-vs-Taubin preset displays noisy preview, but comparison reads clean committed working mesh. Clean baseline roughness ≈0.1269; committed-noisy baseline ≈0.1569. | [Clean input](screenshots/method_comparison_clean_despite_noisy_preset.png), [noisy input](screenshots/method_comparison_committed_noisy_input.png) |
| Comparison invalidation | After a fresh comparison, a new smoothing commit on the same source leaves the old comparison baseline/results visible. | [Screenshot](screenshots/method_comparison_stale_after_new_commit.png) |
| Viewer control no-op | In Overlay, switching to Points/vertices and enabling face normals produced byte-for-byte identical iframe screenshots to the baseline Overlay. | [Selected no-effect controls](screenshots/overlay_points_and_normals_selected_no_effect.png) |
| Summary attribution | A committed Uniform history row remains visible while the Learning Summary reports current uncommitted method Taubin. | [Screenshot](screenshots/download_summary_method_mismatch.png) |
| Scroll proximity | At browser `scrollTop≈965`, sticky viewer top was ≈272 px, explanation top ≈-668 px, and metric-card top ≈-186 px. | [Screenshot](screenshots/control_visible_explanation_scrolled_away.png) |
| Narrow viewport | At 768×900, the three-column body remains, sidebar is hidden, and text wraps severely. | [Screenshot](screenshots/narrow_viewport_768.png) |

## Deterministic geometry probes

| Probe | Exact/representative result | Audit meaning |
| --- | --- | --- |
| Shipped Remove noise settings | Noisy sphere, Taubin λ=.35, μ=-.53, 10 iterations: roughness 0.156868→0.167281 (+6.64%); AABB +24.28% versus noisy and +33.20% versus clean. | Preset roughens and expands rather than denoising with limited shrinkage. |
| Roughness scaling | Low-poly sphere: 0.126881; the same shape and connectivity uniformly scaled by .5: 0.063441. | Metric has length units and rewards uniform shrinkage. |
| Roughness on flat mesh | Flat 5×5 grid: 0.136569. | Metric also responds to boundary valence/sampling, not only surface noise. |
| Inspector/pinned boundary | Grid vertex 0, λ=.5: Inspector predicts (-.875, -.875, 0); preserved-boundary smoother leaves (-1, -1, 0). | Inspector omits active boundary constraint. |
| Uniform shrinkage | Sphere, Uniform λ=.5, 14 iterations: AABB diagonal -71.36%. | Strong, correctly visible shrinkage demonstration. |
| Stable Taubin example | Sphere, λ=.5, μ=-.53, 10 iterations: AABB diagonal -3.14%. | Taubin can reduce contraction for a suitable pair. |
| Allowed unstable Taubin pair | Sphere, λ=.05, μ=-.95, 10 iterations: AABB +1952.90%, roughness +11515%. With λ=0, μ=-.95: AABB +4205.70%. | UI range contains severe expansion without validation. |
| Local radius/falloff | Bumped grid affected/movable counts: r1 1/1, r2 5/5, r3 13/9, r4 21/9. Linear and smoothstep geometry match at r1/r2. | Outer radius ring has zero weight; falloff selector is an effective no-op at the preset radius 2. |
| Noise reproducibility | Seed sequence 42→43→42 returns identical seed-42 vertices/cards; seed 43 differs. | Core deterministic seed behavior passes. |

### Exact volume-probe reproduction

The two pathological volume values in AUD-018 were produced with the following complete construction. Probe 1 reverses every face of a disjoint second tetrahedron. Probe 2 translates one tetrahedron and reverses exactly face index 2.

```powershell
@'
import numpy as np
import trimesh

F = np.array([
    [0, 2, 1],
    [0, 1, 3],
    [0, 3, 2],
    [1, 2, 3],
], dtype=np.int64)

V0 = np.array([
    [0., 0., 0.],
    [1., 0., 0.],
    [0., 1., 0.],
    [0., 0., 1.],
])

V_two = np.vstack([V0, V0 + np.array([3., 0., 0.])])
F_two = np.vstack([F, np.flip(F, axis=1) + 4])
m_two = trimesh.Trimesh(vertices=V_two, faces=F_two, process=False)
print("probe1", "watertight=", m_two.is_watertight,
      "winding=", m_two.is_winding_consistent,
      "signed_volume=", m_two.volume,
      "reported_abs=", abs(float(m_two.volume)),
      "physical_sum=", 2.0 / 6.0)

V_shift = V0 + np.array([2., 2., 2.])
F_bad = F.copy()
F_bad[2] = F_bad[2, ::-1]
m_bad = trimesh.Trimesh(vertices=V_shift, faces=F_bad, process=False)
print("probe2", "watertight=", m_bad.is_watertight,
      "winding=", m_bad.is_winding_consistent,
      "signed_volume=", m_bad.volume,
      "reported_abs=", abs(float(m_bad.volume)),
      "physical_tetra=", 1.0 / 6.0)
'@ | .\.venv\Scripts\python.exe -
```

Output:

```text
probe1 watertight= True winding= True signed_volume= 0.0 reported_abs= 0.0 physical_sum= 0.3333333333333333
probe2 watertight= True winding= False signed_volume= 2.1666666666666665 reported_abs= 2.1666666666666665 physical_tetra= 0.16666666666666666
```

Probe 1 also shows that a globally `True` winding-consistency result does not prevent cancellation between oppositely oriented disconnected components. The app preserves that cancellation by taking `abs(trimesh_mesh.volume)` only after Trimesh has summed the signed component volumes.

## Console classification

- Browser JavaScript errors during normal interactions: 0.
- Earlier console inspection observed unsupported feature-policy names and a Streamlit iframe sandbox warning; those non-blocking framework messages are not present in the later archived warning-level capture.
- The archived QA-session capture contains 198 warnings, all repeated zero-size WebGL framebuffer/texture operations from hidden tab iframes.
- Reset failure classification: Streamlit application/server exception, not a browser JavaScript error.
- Archived warning-level QA capture: [browser_console_warnings.log](browser_console_warnings.log).

## Coverage limitation created by the product failure

Reset-dependent follow-up combinations could not proceed because Reset itself crashes the app. All such cases are classified as failed coverage under AUD-001. They are not reported as passes. Source switching, post-noise, post-commit, manual/live, supported/unsupported, clean/noisy comparison, and desktop/narrow contexts were exercised independently.
