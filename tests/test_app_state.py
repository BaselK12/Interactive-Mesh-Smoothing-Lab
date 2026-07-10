"""State-transition regression tests for the Streamlit app itself.

These run the real app script headlessly with streamlit.testing.v1.AppTest and
cover the audit blockers that live in UI/state wiring rather than in geometry
code: AUD-001 (reset crash), AUD-005 (comparison baseline), AUD-006 (post-commit
double preview), AUD-010 (stale comparison), AUD-012 (summary provenance),
AUD-015 (manual noise gating), AUD-016 (zero-effect commit), AUD-024 (source
switch policy).
"""

from __future__ import annotations

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP = "app.py"
TIMEOUT = 60


def _make() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception
    return at


def _button(at: AppTest, label: str):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"button not found: {label!r} (have {[b.label for b in at.button]})"
    return matches[0]


def _click(at: AppTest, label: str) -> AppTest:
    _button(at, label).click()
    at.run()
    assert not at.exception, f"exception after clicking {label!r}: {at.exception}"
    return at


def test_fresh_start_has_no_exception_and_neutral_state():
    at = _make()
    assert at.session_state["smoothing_steps"] == 0
    assert at.session_state["noise_enabled"] is False
    assert at.session_state["smoothing_iterations"] == 0


def test_reset_does_not_crash_and_restores_original():
    """AUD-001 regression: Reset used to raise StreamlitAPIException."""
    at = _make()
    _click(at, "See shrinkage")
    assert at.session_state["smoothing_iterations"] == 14
    _click(at, "Reset experiment")
    assert not at.exception
    assert at.session_state["smoothing_iterations"] == 0
    assert at.session_state["noise_enabled"] is False
    assert at.session_state["smoothing_steps"] == 0
    working = at.session_state["working_mesh"]
    original = at.session_state["original_mesh"]
    assert np.allclose(working.vertices, original.vertices)


def test_commit_does_not_immediately_reapply_the_operation():
    """AUD-006 regression: committing a noisy preview used to stack noise again."""
    at = _make()
    _click(at, "Remove noise")
    preview = at.session_state["preview_mesh"]
    assert preview is not None
    _click(at, "Commit preview as current mesh")
    committed = at.session_state["working_mesh"]
    assert np.allclose(committed.vertices, preview.vertices)
    # One-shot controls were cleared, so the next preview equals the commit.
    assert at.session_state["noise_enabled"] is False
    assert at.session_state["smoothing_iterations"] == 0
    assert at.session_state["preview_mesh"] is None


def test_zero_lambda_smoothing_is_not_committable():
    """AUD-016 regression: lambda=0 with positive iterations is a no-op."""
    at = _make()
    at.session_state["smoothing_iterations"] = 10
    at.session_state["smoothing_strength"] = 0.0
    at.run()
    assert not at.exception
    commit = _button(at, "Commit preview as current mesh")
    assert commit.disabled
    assert at.session_state["preview_mesh"] is None


def test_manual_add_noise_respects_the_noise_checkbox():
    """AUD-015 regression: manual Add noise used to ignore 'Noise enabled'."""
    at = _make()
    at.session_state["live_preview_enabled"] = False
    at.run()
    add_button = _button(at, "Add noise to current mesh")
    assert add_button.disabled  # noise checkbox is off
    before = at.session_state["working_mesh"].vertices.copy()
    # Enable the checkbox but set zero strength: still disabled.
    at.session_state["noise_enabled"] = True
    at.session_state["noise_strength"] = 0.0
    at.run()
    assert _button(at, "Add noise to current mesh").disabled
    assert np.allclose(at.session_state["working_mesh"].vertices, before)
    assert at.session_state["smoothing_history"] == []
    # With real strength the action works and is recorded once.
    at.session_state["noise_strength"] = 0.4
    at.run()
    _click(at, "Add noise to current mesh")
    assert len(at.session_state["smoothing_history"]) == 1
    assert not np.allclose(at.session_state["working_mesh"].vertices, before)


def test_comparison_defaults_to_noisy_stage_after_preset():
    """AUD-005 regression: the advertised noisy comparison must use noisy input."""
    at = _make()
    _click(at, "Uniform vs Taubin")
    noisy_stage = at.session_state["preview_noisy_stage"]
    assert noisy_stage is not None
    assert at.session_state["method_comparison_input_choice"] == (
        "Noisy preview stage (before smoothing)"
    )
    at.session_state["active_learning_section"] = "Method Comparison"
    at.run()
    assert not at.exception
    _click(at, "Run comparison from the selected input")
    stored = at.session_state["method_comparison_input_mesh"]
    assert np.allclose(stored.vertices, noisy_stage.vertices)
    rows = at.session_state["method_comparison_rows"]
    assert rows and all(row["Roughness before"] == pytest.approx(0.15686846967151227) for row in rows)


def test_comparison_flags_stale_results_after_commit():
    """AUD-010 regression: stored comparison must be flagged when input changes."""
    at = _make()
    at.session_state["active_learning_section"] = "Method Comparison"
    at.run()
    _click(at, "Run comparison from the selected input")
    assert at.session_state["method_comparison_rows"]
    # Mutate the working mesh via a manual smoothing action.
    at.session_state["active_learning_section"] = "Playground"
    at.session_state["live_preview_enabled"] = False
    at.session_state["smoothing_iterations"] = 5
    at.session_state["smoothing_strength"] = 0.5
    at.run()
    _click(at, "Apply smoothing")
    at.session_state["active_learning_section"] = "Method Comparison"
    at.run()
    warnings = " ".join(str(w.value) for w in at.warning)
    assert "earlier snapshot" in warnings


def test_summary_reports_committed_method_not_current_widget():
    """AUD-012 regression: the summary must describe committed actions only."""
    at = _make()
    at.session_state["smoothing_iterations"] = 5
    at.session_state["smoothing_strength"] = 0.5
    at.run()
    _click(at, "Commit preview as current mesh")
    # Change the method selector WITHOUT committing.
    at.session_state["smoothing_method"] = "Taubin"
    at.session_state["active_learning_section"] = "Advanced Metrics"
    at.run()
    assert not at.exception
    history = at.session_state["smoothing_history"]
    assert history[-1]["Method"] == "Uniform Laplacian"
    # The rendered summary table must show the committed method, and the
    # uncommitted Taubin selection must not appear anywhere in it.
    tables = [t.value for t in at.table]
    flat = "\n".join(str(t) for t in tables)
    assert "Uniform Laplacian" in flat
    assert "Taubin" not in flat.replace("Taubin mu", "")


def test_source_switch_resets_experiment_controls():
    """AUD-024 regression: a manual source switch starts neutral."""
    at = _make()
    at.session_state["noise_enabled"] = True
    at.session_state["noise_strength"] = 0.5
    at.session_state["smoothing_iterations"] = 8
    at.run()
    at.session_state["sample_mesh"] = "Low-poly sphere"
    at.run()
    assert not at.exception
    assert at.session_state["noise_enabled"] is False
    assert at.session_state["smoothing_iterations"] == 0
    working = at.session_state["working_mesh"]
    original = at.session_state["original_mesh"]
    assert np.allclose(working.vertices, original.vertices)


def test_preset_source_switch_keeps_preset_controls():
    """Presets carry their own controls across the source switch they trigger."""
    at = _make()
    _click(at, "Remove noise")
    assert at.session_state["sample_mesh"] == "Low-poly sphere"
    assert at.session_state["noise_enabled"] is True
    assert at.session_state["smoothing_iterations"] == 10
    assert at.session_state["smoothing_strength"] == 0.5


def test_taubin_unstable_pair_shows_warning():
    """AUD-009 regression: unstable lambda/mu pairs must warn."""
    at = _make()
    _click(at, "Remove noise")
    at.session_state["smoothing_strength"] = 0.2
    at.run()
    warnings = " ".join(str(w.value) for w in at.warning)
    assert "Unstable Taubin pair" in warnings
