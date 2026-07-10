# 2-3 Minute Demo Script

A tight walkthrough using the **current live-preview workflow**. Every step names
the exact control as it appears in the app.

## Setup (before you start)
- Run `python -m streamlit run app.py`.
- Stay on the **Playground** section (the default). Keep the sidebar visible.

## 1. Shrinkage in one click (~30s)
- Click the **See shrinkage** preset.
- The viewer switches to **Overlay**: the black wireframe is the source
  original; the blue shaded surface is the live preview after 14 Uniform
  Laplacian iterations.
- Point at the metric strip under the viewer: roughness change and the AABB
  diagonal change are both strongly negative. Key line: *uniform averaging
  smooths, but on closed shapes it also pulls the mesh inward.*

## 2. Denoising with Taubin (~40s)
- Click **Reset experiment**, then the **Remove noise** preset.
- Read the status line: it reports the roughness sequence
  *start -> noisy -> smoothed*. The smoothed value is well below the noisy one
  while the AABB change stays small.
- Optional: drag **Smoothing strength (lambda)** to 0.2 and show the instability
  warning. Explain that `lambda < |mu|` gives a positive pass-band but is not
  sufficient by itself; the app's sampled-gain check flags this pair.

## 3. Fair method comparison (~40s)
- Click **Reset experiment**, then **Uniform vs Taubin**.
- Open the **Method Comparison** section. The comparison input is preset to
  **Noisy preview stage (before smoothing)** — the exact seed-42 noisy sphere in
  the viewer.
- Click **Run comparison from the selected input**. Read the observation lines:
  they name the exact metric (AABB diagonal, roughness reduction) instead of
  declaring a "best" method. Mention that one Taubin iteration does two passes,
  so equal iterations are the same input, not equal work.

## 4. Boundary preservation (~20s)
- Back in **Playground**, click **Boundary preservation**, then toggle
  **Preserve boundary vertices** off and on.
- Off: the grid border slides inward. On: the border stays pinned while the
  bump relaxes. The **Boundary moved?** card flips between Yes and No.

## 5. The formula on one vertex (~20s)
- Open **Step Inspector** on Plane/grid; vertex 0 is a corner.
- Ensure **Preserve boundary vertices for this inspection** is on, then show the
  pinned-boundary banner. Switch to an interior vertex (e.g. 12) to show the
  neighbor average, displacement, lambda, and predicted position.

## Closing line
"The lab turns one lecture topic — mesh smoothing — into measurable, comparable,
inspectable experiments: what smoothing does, why it shrinks, and how methods
differ on the same input."
