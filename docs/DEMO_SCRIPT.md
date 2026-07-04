# 2-3 Minute Demo Script

A tight walkthrough that hits the core learning points: what smoothing does, why
it shrinks, and how methods compare.

## Setup (before you start)
- Run `python -m streamlit run app.py`.
- Have the sidebar visible.

## 1. Show a clean mesh (~20s)
- Sidebar -> Sample mesh -> **Low-poly sphere**.
- Point at **Mesh statistics** (vertices/faces/edges, "triangle mesh").
- Scroll to **Smoothing Observation Metrics** and note the **roughness energy**
  of the clean mesh.

## 2. Add noise (~20s)
- Sidebar -> **Noisy mesh experiment** -> Noise mode "Along vertex normals",
  strength ~0.4, seed 42.
- Click **Add noise to current mesh**.
- Point out that roughness energy jumped and the surface looks rough in the
  viewer / before-after comparison.

## 3. Uniform smoothing shrinks (~30s)
- Smoothing method = **Uniform Laplacian**, iterations ~10, lambda ~0.5.
- Click **Apply smoothing**.
- In the metrics: roughness drops, but **bounding box** and **surface area**
  shrink a lot. State the key point: uniform smoothing removes roughness but
  shrinks the mesh.

## 4. Taubin preserves size (~30s)
- Click **Reset to clean original**, then **Add noise** again (same seed 42).
- Smoothing method = **Taubin** (leave the default mu). Apply ~10 iterations.
- Compare metrics: roughness still drops, but bounding-box change is far smaller.
  State: Taubin smooths while preserving size.

## 5. Compare all methods on one input (~30s)
- Open **Smoothing Method Comparison**.
- Click **Run comparison from current mesh**.
- Read the ranking notes: "least shrinkage" vs "largest roughness reduction",
  and that cotangent is supported here (triangle mesh).
- State: good smoothing is a tradeoff; lower roughness is not always better if
  the mesh shrinks too much.

## 6. Make the formula visible (~20s)
- Open **Smoothing Step Inspector**, pick a vertex.
- Show the neighbor list, neighbor average, displacement, and predicted one-step
  position.
- State: this is exactly what smoothing does to every vertex, each iteration.

## Closing line
"The lab turns one lecture topic — mesh smoothing — into measurable, comparable,
inspectable experiments: what it does, why it shrinks, and how methods differ."
