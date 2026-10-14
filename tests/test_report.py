"""docs/MODELS.md (K4) ve şartname beklentilerinin aynen alıntılanması; SPEC_V1_6 §10-9."""
from __future__ import annotations

import json

import pytest

from borsai import report
from borsai import report_faz1b as rf
from borsai.provenance import ROOT
from borsai.specs import FAZ1B_MODEL_IDS

MODELS_MD = ROOT / "docs" / "MODELS.md"


@pytest.fixture(scope="module")
def text():
    return MODELS_MD.read_text(encoding="utf-8")


def test_models_md_is_up_to_date(text):
    assert text == report.render()


@pytest.mark.parametrize("model_id", list(rf.EXPECTATIONS))
def test_expectations_are_verbatim_quotes(model_id, text):
    for source, quote in rf.EXPECTATIONS[model_id]:
        spec_file = ROOT / "docs" / "specs" / source.split(" ")[0]
        assert quote in spec_file.read_text(encoding="utf-8"), (source, quote)
        assert rf._cell(quote) in text


def test_every_new_model_has_a_section_and_expectations(text):
    for model_id in ("v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_hazard_v0", "pb_ceiling_v0"):
        assert f"### `{model_id}`" in text and model_id in rf.EXPECTATIONS and model_id in rf.PROSPECTIVE
    for rule in rf.OPERATIONAL_RULES:
        assert rule in text
    for model_id in FAZ1B_MODEL_IDS:
        assert f"| `{model_id}` |" in text


def test_ceiling_primary_metric_rps_against_rules(text):
    section = text.split("### `ceiling_hazard_v0`")[1].split("### `pb_ceiling_v0`")[0]
    assert "Birincil metrik RPS" in section
    for rule in ("ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling", "v1_5_p_up_as_ceiling"):
        assert f"`{rule}`" in section


def test_v1_6_selection_distribution_reported_and_logged(text):
    section = text.split("### `v1_6_h99`")[1].split("### `v1_5_market20_v0`")[0]
    assert "Ridge α seçim dağılımı" in section and "Logit C seçim dağılımı" in section
    assert "en sık sonlu uç değerin payı" in section
    entries = [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any(e["model_id"] == "v1_6_h99" and e["context"] == "faz1b_golden" for e in entries)
