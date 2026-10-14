"""Faz 6 S6 (BORSAI_FAZ6_S6_SCORING_20260925): `python -m borsai.scoring --oot` (T1), docs/SCORES_OOT.md (T2) ve EXPOSURE.md
§3 ayrıştırıcısı (T3, F5). Sentetik: geçici git deposu (`test_faz6_oot` kalıbı), sentetik maruziyet metni. Gerçek kümeye bakan
tek test yalnız sayıyı ve alt küme koşulunu denetler; kümenin elemanları hiçbir çıktıya düşmez."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from borsai import outcomes_oot as oo
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, pretty_json_bytes, sha256_file

import faz6_support as f6
import test_faz6_oot as t6

NOW = datetime(2026, 9, 25, 9, 0, 0, tzinfo=timezone.utc)
SYN_CODE = re.compile(r"\bSYN[A-Z]{1,2}\b")
READ_ONLY_SCORES = ("scores/scores.json", "scores/scores_post_d1.json", "docs/SCORES.md")

EXPOSURE_TEXT = """# Maruziyet kaydı (sentetik)

## 2. Başka bölüm
| Kohort üyesi | Bülten | Dosya |
|---|---|---|
| SYND | 2021/1 | a |

## 3. Bülten kesitleri (sentetik)
Açıklama satırı SYNE adını da geçirir.

| Kohort üyesi | Bülten | Kesitin ait olduğu inceleme dosyası |
|---|---|---|
| SYNA | 2021/10 | x, y |
| SYNB | 2021/11 | z |
| SYNZ | 2021/12, 2022/1 | w |

Değerlendirme notu.

## 4. Sonraki bölüm
| Kohort üyesi | Bülten | Dosya |
|---|---|---|
| SYNC | 2021/2 | b |
"""
EXPOSURE_SET = {"SYNA", "SYNB", "SYNZ"}          # SYNZ kasada (MEMBER); açık kümede 2


@pytest.fixture(scope="module")
def cal():
    return oo.load_calendar_oot()


@pytest.fixture(scope="module")
def oot_repo(tmp_path_factory, cal):
    """`test_faz6_oot.scored_repo` kalıbı: S1 + S2 + S5 commit'li, kanıtlı sentetik depo; öbür skor dosyaları ve sentetik
    maruziyet kaydı da yerinde."""
    tmp = tmp_path_factory.mktemp("s6")
    root = t6._pipeline_repo(tmp, cal, t6.SCORE_MEMBERS)
    files = f6.market(t6._window(cal, "2021-02-26", 80), t6._paths_for(cal, t6.SCORE_MEMBERS))
    oo.extract_open_members(root=root, qdir=tmp / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False,
                            calendar=cal)
    f6.make_proof(root, f6.commit(root, "S5", "data"), "2026-09-25T10:20:00Z")
    for rel in READ_ONLY_SCORES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(f"öbür terazi: {rel}\n".encode("utf-8"))
    exp = root / sc.SPK_EXPOSURE_REL
    exp.parent.mkdir(parents=True)
    exp.write_text(EXPOSURE_TEXT, encoding="utf-8")
    return root


def _snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def _real_state() -> dict[str, object]:
    paths = [ROOT / rel for rel in READ_ONLY_SCORES] + [sc.OOT_SCORES_PATH, sc.OOT_DOC_PATH]
    return {p.name: (p.read_bytes() if p.exists() else None) for p in paths}


# ================================================================ T3: EXPOSURE.md §3 ayrıştırıcısı (F5, KARARLAR D8-1)

def _exposure(tmp_path, text=EXPOSURE_TEXT):
    p = tmp_path / "EXPOSURE.md"
    p.write_text(text, encoding="utf-8")
    return p


def _cohort(tmp_path, cal):
    members = [{"ticker": t, "ftd": "2021-03-01"} for t in ("SYNA", "SYNB", "SYNC", "SYND", "SYNE")]
    members.append({"ticker": "SYNZ", "ftd": "2021-03-02", "vault": "SEALED"})
    f6.write_members(tmp_path, members, sessions=cal.sessions)             # + kapsam dışı SYNOS
    return tmp_path / "registry" / "oot" / "cohort_pre_h99.csv"


def test_spk_exposure_parser_reads_only_section_3_first_column(tmp_path, cal, capsys):
    cohort = _cohort(tmp_path, cal)
    got = sc.spk_corporate_action_members(_exposure(tmp_path), cohort_path=cohort, expected_n=3)
    assert isinstance(got, frozenset) and got == EXPOSURE_SET            # §2/§4 tabloları ve düz metindeki ad okunmaz
    assert capsys.readouterr() == ("", "")                                # küme basılmaz


@pytest.mark.parametrize("change, message", [
    (lambda t: t, "3 kod var, 4 olmalı"),                                                   # sayı (expected 4)
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| SYNQ | 2021/11 | z |"), "MEMBER'ı değil"),  # kohortta yok
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| SYNOS | 2021/11 | z |"), "MEMBER'ı değil"),  # kapsam dışı
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| SYNA | 2021/11 | z |"), "birden çok satırda"),
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| `SYNB` | 2021/11 | z |"), "satır beklenen biçimde değil"),
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| Synb | 2021/11 | z |"), "satır beklenen biçimde değil"),
    (lambda t: t.replace("| SYNB | 2021/11 | z |", "| SYNB | 2021/11 |"), "satır beklenen biçimde değil"),
    (lambda t: t.replace("## 3. Bülten", "## 3b. Bülten"), "başlığı 0 kez"),
    (lambda t: t + "\n## 3. İkinci\n", "başlığı 2 kez"),
    (lambda t: t.replace("| Kohort üyesi | Bülten | Kesitin", "| Üye | Bülten | Kesitin"), "tablo başlığı"),
])
def test_spk_exposure_parser_stops_with_numbers_only(tmp_path, cal, change, message):
    cohort = _cohort(tmp_path, cal)
    expected = 4 if "4 olmalı" in message else 3
    with pytest.raises(sc.ScoringError, match=message) as e:
        sc.spk_corporate_action_members(_exposure(tmp_path, change(EXPOSURE_TEXT)), cohort_path=cohort, expected_n=expected)
    assert not SYN_CODE.search(str(e.value))                              # ileti kod taşımaz


def test_spk_exposure_default_count_is_registry_constant(tmp_path, cal, monkeypatch):
    cohort = _cohort(tmp_path, cal)
    with pytest.raises(sc.ScoringError, match="28 olmalı"):
        sc.spk_corporate_action_members(_exposure(tmp_path), cohort_path=cohort)
    monkeypatch.setattr(reg, "N_SPK_CORPORATE_ACTION_ROW_SEEN", 3)
    n = len(sc.spk_corporate_action_members(_exposure(tmp_path), cohort_path=cohort))
    assert n == 3


def test_real_exposure_section_3_is_28_cohort_members_count_only(capsys):
    """Gerçek dosya: yalnız sayı ve alt küme koşulu (elemanlar ne assert ifadesinde ne çıktıda)."""
    got = sc.spk_corporate_action_members()
    n = len(got)
    inside = got <= {r["ticker"] for r in reg.cohort_members(reg.read_cohort()[1])}
    del got
    assert n == reg.N_SPK_CORPORATE_ACTION_ROW_SEEN == 28
    assert inside
    assert capsys.readouterr() == ("", "")


# ================================================================ T1: --oot yalnız iki dosya yazar

def test_oot_cli_writes_only_scores_oot_and_doc(oot_repo, monkeypatch, capsys):
    monkeypatch.setattr(reg, "N_SPK_CORPORATE_ACTION_ROW_SEEN", len(EXPOSURE_SET))
    for rel in ("scores/scores_oot.json", "docs/SCORES_OOT.md"):          # test sırasından bağımsız: iki dosya yeni yazılır
        (oot_repo / rel).unlink(missing_ok=True)
    before, real_before = _snapshot(oot_repo), _real_state()
    assert sc.main_oot(oot_repo, now=NOW) == 0
    after = _snapshot(oot_repo)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"scores/scores_oot.json", "docs/SCORES_OOT.md"}
    assert all(before[rel] == after[rel] for rel in READ_ONLY_SCORES)
    assert _real_state() == real_before                                  # gerçek repoya hiçbir şey yazılmadı
    out = capsys.readouterr().out
    assert out.split() == [str(oot_repo / "scores" / "scores_oot.json"), str(oot_repo / "docs" / "SCORES_OOT.md")]
    s = json.loads((oot_repo / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    b = s["oot_pre_h99"]
    assert (b["n_spk_corporate_action_seen"], b["n_spk_corporate_action_seen_cohort_total"]) == (2, 3)
    text = (oot_repo / "scores" / "scores_oot.json").read_text(encoding="utf-8")
    assert text.count("spk") == 2                                        # yalnız iki sayaç; üye başına bayrak yok


def test_main_dispatches_oot_flag_and_bare_main_is_unchanged(monkeypatch):
    calls = []
    monkeypatch.setattr(sc, "main_oot", lambda: calls.append("oot") or 0)
    for name in ("build_scores", "build_post_d1_scores", "write_scores", "write_post_d1_scores", "write_doc"):
        monkeypatch.setattr(sc, name, lambda *a, _n=name, **k: calls.append(_n) or {})
    monkeypatch.setattr(sc, "pretty_json_bytes", lambda x: b"{}")
    assert sc.main(["--oot"]) == 0 and calls == ["oot"]
    calls.clear()
    assert sc.main([]) == 0
    assert calls == ["build_scores", "build_post_d1_scores", "write_scores", "write_post_d1_scores", "write_doc"]


# ================================================================ T2: SCORES_OOT.md = yazılmış JSON'un render'ı

def test_scores_oot_doc_is_render_of_written_json(oot_repo, monkeypatch):
    monkeypatch.setattr(reg, "N_SPK_CORPORATE_ACTION_ROW_SEEN", len(EXPOSURE_SET))
    sc.main_oot(oot_repo, now=NOW)
    written = json.loads((oot_repo / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    doc = (oot_repo / "docs" / "SCORES_OOT.md").read_text(encoding="utf-8")
    assert doc == sc.render_oot_doc(written)
    mem = sc.build_oot_scores(root=oot_repo, now=NOW, spk_corporate_action_seen=EXPOSURE_SET)
    assert sc.render_oot_doc(mem) == sc.render_oot_doc(json.loads(pretty_json_bytes(mem)))   # sözlük sırasından bağımsız
    assert doc.startswith(f"# {sc.OOT_TITLE}\n") and f"## 6. {sc.OOT_POST_D1_TITLE}" in doc
    assert not SYN_CODE.search(doc)                                      # üye kodu yok (satırlar JSON'da)
    assert "`v1_5_h99` | return D5 MAE | `base_train_median` | 12 (" in doc
    for word in ("LIVE", "LATE_RECORD", "backtest.cells", "live.cells"):
        assert word not in doc


def _cell(label, diffs, *, rule="base_train_median", blocks=None):
    blocks = blocks or [f"2021-{1 + i % 12:02d}" for i in range(len(diffs))]
    obs = [sc.PairedObs(sc.SCALE_OOT, f"T{i}", blocks[i], 0.5 + x, 0.5, sc.CLASS_OOT_BLIND) for i, x in enumerate(diffs)]
    return {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_id": rule, **sc.paired_metric(obs), "label": label}


def test_render_oot_verdict_language():
    """SPEC_SCORING §8 dili: aralık 0'ın altında "geçiyor (zaman-dışı terazide)", üstünde "geçemiyor", içeriyorsa
    "ayırt edilemiyor"; 10 ≤ n < 30 "yetersiz örnek"; n < 10 metrik yok."""
    cases = {"pass": ([-0.1 - 0.001 * i for i in range(40)], sc.OOT_V_PASS),
             "fail": ([0.1 + 0.001 * i for i in range(40)], "geçemiyor"),
             "neutral": ([(-1) ** i * 0.1 for i in range(40)], "ayırt edilemiyor"),
             "small": ([-0.1] * 15, "yetersiz örnek"),
             "tiny": ([-0.1] * 5, "metrik yok (n < 10)")}
    for name, (diffs, want) in cases.items():
        c = _cell("birincil", diffs)
        assert sc._oot_verdict(c) == want, name
    assert sc.OOT_V_PASS == "geçiyor (zaman-dışı terazide)"
    assert sc._oot_verdict(_cell("birincil", [-0.1] * 40, blocks=["2021-01"] * 40)) == sc.V_NO_CI   # < 6 blok


def test_render_oot_doc_sections_and_labels(oot_repo):
    s = sc.build_oot_scores(root=oot_repo, now=NOW, spk_corporate_action_seen=EXPOSURE_SET)
    v15 = next(m for m in s["oot_pre_h99"]["models"] if m["model_id"] == "v1_5_h99")
    v15["cells"] = [_cell("birincil", [-0.1 - 0.001 * i for i in range(40)]), _cell("keşif", [0.2] * 40, rule="base_zero")]
    v15["by_year"] = [{"subset": "2021", **_cell("ikincil", [-0.1] * 5)}]
    doc = sc.render_oot_doc(json.loads(pretty_json_bytes(s)))
    sec = {h: doc.split(h, 1)[1].split("\n## ", 1)[0] for h in ("## 2.", "## 4.", "## 5.", "## 6.")}
    assert f"| `v1_5_h99` | return D5 MAE | `base_train_median` | 40 (12) |" in sec["## 2."] and sc.OOT_V_PASS in sec["## 2."]
    assert "`base_zero`" not in sec["## 2."] and "`base_zero`" in sec["## 5."] and "(keşif)" in sec["## 5."]
    assert "| `v1_5_h99` | 2021 | `base_train_median` | 5 (5) | — | — | — | — | — | metrik yok (n < 10) |" in sec["## 4."]
    assert "### 4.1 İlk işlem yılı (ikincil)" in doc and "### 4.2 Rejim alt kümeleri (keşif)" in doc
    assert "OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED" in sec["## 6."] and "MACHINE_SEQUENCED" in sec["## 6."]
