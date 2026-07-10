# Repository Cleanup Report

Prepared while getting **Mesh Smoothing Lecture Lab** ready for final submission
and public use. No commits or pushes were made; all changes are in the working
tree for review.

## 1. Files deleted

**Internal QA / audit reports and logs (obsolete or internal):**

| Path | Reason | Category |
| --- | --- | --- |
| `docs/audit/FIX_REPORT.md` | Internal issue-by-issue fix log (AUD-xxx) from an earlier bug-fixing pass; all issues resolved and superseded by the current app + docs | Obsolete |
| `docs/audit/LATEST_AUDIT.md` | Pointer file into the audit folder | Obsolete |
| `docs/audit/20260710-112622/FULL_PROJECT_AUDIT.md` | Historical bug audit describing defects that are now fixed | Obsolete |
| `docs/audit/20260710-112622/RUNTIME_PROBES.md` | Numerical trace supporting the old audit; useful facts (versions, verified behaviors) retained in README §25 | Obsolete |
| `docs/audit/20260710-112622/downloaded_summary.md` | A one-off exported experiment summary | Temporary |
| `docs/audit/20260710-112622/*.log` (4 files) | Streamlit stdout/stderr capture from QA runs | Temporary |
| `docs/audit/20260710-112622/browser_console_warnings.log` | Browser console capture from QA runs | Temporary |
| `docs/final_qa/FINAL_QA_REPORT.md` | Internal final-QA report with audit cross-references; QA outcome folded into README §25 | Obsolete (internal) |
| `docs/final_qa/*.log` (2 files) | Streamlit run logs | Temporary |

**Screenshots showing already-fixed bugs or superseded by the new set:**

| Path | Reason | Category |
| --- | --- | --- |
| `docs/audit/20260710-112622/screenshots/*` (~30 PNGs, incl. `broken_*`) | Screenshots of defects that are fixed (reset crash, wrong denoise preset, stale comparison, etc.) — misleading for a public repo | Misleading / obsolete |
| `docs/audit/fix_verification/screenshots/*` (~12 PNGs) | Verification shots of the fix pass; superseded by the curated `docs/screenshots/` set | Duplicated / superseded |
| `docs/audit/fix_verification/console_log.txt` | Console capture from the fix-verification run | Temporary |
| `docs/final_qa/screenshots/*` (16 PNGs) | Prior QA screenshot set (mixed naming); replaced by the curated, consistently-named `docs/screenshots/` set | Duplicated / superseded |

**Python caches (also removed from git tracking and now git-ignored):**

| Path | Reason | Category |
| --- | --- | --- |
| `src/__pycache__/` (6 `.pyc`, was tracked) | Compiled bytecode; should never be tracked | Temporary |
| `__pycache__/` (repo root) | Compiled bytecode | Temporary |
| `tests/__pycache__/` | Compiled bytecode | Temporary |
| `.pytest_cache/` | Pytest run cache | Temporary |

## 2. Folders deleted

- `docs/audit/` (entire tree — reports, logs, and bug-state screenshots).
- `docs/final_qa/` (entire tree — internal report, logs, superseded screenshots).
- `src/__pycache__/`, `__pycache__/`, `tests/__pycache__/`, `.pytest_cache/`.

## 3. Files kept and why

| Path | Why kept |
| --- | --- |
| `app.py` | Application source |
| `src/*.py` | Core mesh library (mesh_core, sample_meshes, mesh_ops, mesh_metrics, visualization) |
| `tests/*.py` | Useful automated tests (49 passing) — algorithm, metrics, app-state, and release-QA |
| `requirements.txt` | Runtime dependencies |
| `examples/pyramid.obj` | Sample triangle OBJ used by the upload workflow and cotangent demo |
| `docs/METHODS.md` | Technical smoothing methods and implementation assumptions (accurate, current) |
| `docs/STUDENT_GUIDE.md` | Step-by-step learning exercises (accurate, current) |
| `docs/DEMO_SCRIPT.md` | 2–3 minute presentation flow (accurate, current) |
| `assets/.gitkeep` | Keeps the runtime `assets/` directory present |

## 4. Files moved or renamed

- No source files were moved. The final screenshot set was created fresh in
  `docs/screenshots/` (the previous QA screenshots under `docs/final_qa/` were
  deleted, not moved).

## 5. Documentation rewritten / added

- **`README.md`** — fully rewritten as the public-facing project document
  (29 sections: purpose, learning goals, per-feature explanations with
  screenshots, method support matrix, state model, metrics, learning paths,
  install/run, structure, technical implementation, testing, limitations, and
  course/author attribution).
- **`docs/PROJECT_STRUCTURE.md`** — new: architecture, module responsibilities,
  and data flow.
- **`docs/CLEANUP_REPORT.md`** — this file.
- **`.gitignore`** — new: ignores `__pycache__/`, `*.pyc`, `.venv/`, logs, and
  editor/OS cruft so caches are never tracked again.
- `docs/METHODS.md`, `docs/STUDENT_GUIDE.md`, `docs/DEMO_SCRIPT.md` were reviewed
  and confirmed accurate and consistent with the current app; no rewrite needed.

Useful technical information from the deleted audit reports was **preserved**
before deletion: the smoothing formulas and implementation assumptions live in
`docs/METHODS.md`, and the testing/QA outcome (49 passing tests, verified
behaviors, dependency versions) is captured in **README §25**.

## 6. Screenshots created

16 curated screenshots in `docs/screenshots/`, captured from the current running
app (fully rendered 3D viewer, no errors, consistent 1440×1024 viewport):

`01_home_playground`, `02_mesh_display_modes`, `03_face_vertex_normals`,
`04_noise_experiment`, `05_uniform_smoothing`, `06_taubin_smoothing`,
`07_cotangent_smoothing`, `08_method_comparison`, `09_before_after_overlay`,
`10_boundary_preservation`, `11_local_soft_smoothing`, `12_step_inspector`,
`13_guided_learning`, `14_student_exercises`, `15_advanced_metrics`,
`16_learning_summary`.

## 7. Screenshots deleted / replaced

- ~30 bug-state audit screenshots and ~12 fix-verification screenshots removed
  (fixed defects / superseded).
- 16 prior QA screenshots under `docs/final_qa/screenshots/` replaced by the new
  curated set.

## 8. Remaining repository structure

```
README.md
requirements.txt
app.py
.gitignore
src/            mesh_core, sample_meshes, mesh_ops, mesh_metrics, visualization
examples/       pyramid.obj
tests/          test_mesh_ops, test_presets_and_metrics, test_app_state, test_release_qa
docs/           METHODS.md, STUDENT_GUIDE.md, DEMO_SCRIPT.md,
                PROJECT_STRUCTURE.md, CLEANUP_REPORT.md, screenshots/ (01–16)
assets/         .gitkeep
```

## 9. Tests run

- `python -m compileall .` — passed.
- `python -m pytest` — **49 passed**.
- `python -m streamlit run app.py` — launched successfully; all 16 screenshots
  were captured from the live app, and a Playwright walkthrough reported no
  console or server errors.

## 10. Uncertain files left untouched

- **`assets/.gitkeep`** — the `assets/` directory is currently empty and not
  referenced by code, but it is part of the intended structure; kept as a
  placeholder rather than removed.
- Nothing else was ambiguous; every deleted item was a cache, a log, or a
  superseded/obsolete audit artifact whose useful content was preserved
  elsewhere.
