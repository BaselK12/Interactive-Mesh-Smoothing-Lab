# Latest Mesh Smoothing Lecture Lab Audit

Latest audit: [2026-07-10 full project audit](20260710-112622/FULL_PROJECT_AUDIT.md)

Evidence screenshots: [screenshots](20260710-112622/screenshots/)

Runtime and numerical trace: [RUNTIME_PROBES.md](20260710-112622/RUNTIME_PROBES.md)

Overall verdict: **Not ready**. Recommendation: **Fix high-priority UX issues first**.

Independent verification (second reviewer, 2026-07-10): blockers AUD-001 (Reset crash: widget key `noise_enabled` mutated after instantiation, `app.py:2388-2391` vs `app.py:1975`), AUD-002 ("Remove noise" preset numerically reproduced: roughness +31.84%, AABB diagonal +33.20% vs clean; λ=0.5/μ=-0.53 would have denoised at -19.4%), AUD-005 (Method Comparison reads committed `_working_mesh()` at `app.py:2851` while the preset only builds an uncommitted noisy preview), AUD-014 (linear and smoothstep falloff produce identical weights 1/0.5/0 at the shipped preset radius 2), and AUD-015 (`Add noise to current mesh` at `app.py:2383` never checks the Noise enabled checkbox) were all re-confirmed against source and numerical probes.

---

## Fix pass (2026-07-10)

Every issue in the full audit above was addressed. See
[FIX_REPORT.md](FIX_REPORT.md) for the complete issue-by-issue root cause,
fix, and test evidence (36 automated tests + real-browser Playwright
verification, including one additional live-UI bug found and fixed during
verification).

**Updated verdict: Ready after minor fixes.** All Blocker and High issues are
Resolved; two Medium-severity items are intentionally left as disclosed
partial/out-of-scope limitations (see the Fix Report's "Remaining
limitations" section).
