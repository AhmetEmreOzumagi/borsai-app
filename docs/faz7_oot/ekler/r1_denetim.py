"""R1 denetimi (BORSAI_FAZ7_OOT_RECORDS; yalnız sayı basar, hiçbir kod basılmaz). Kullanım: .venv/bin/python docs/faz7_oot/ekler/r1_denetim.py <repo kökü>"""
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from borsai import freeze as fz  # noqa: E402
from borsai import registry as reg  # noqa: E402
from borsai.provenance import canonical_sha256, pretty_json_bytes, sha256_file  # noqa: E402
from borsai.specs import FAZ7_MODEL_IDS, FAZ7C_MODEL_IDS  # noqa: E402

NEW = list(FAZ7_MODEL_IDS) + list(FAZ7C_MODEL_IDS)
rd = root / "registry" / "oot" / "records"
_, rows = reg.read_cohort(root / "registry" / "oot" / "cohort_pre_h99.csv")
members = reg.cohort_members(rows)
vault = {r["ticker"]: ("kasa" if r["vault"] == reg.VAULT_SEALED else "acik") for r in members}
index_sha = sha256_file(root / "models" / "INDEX.json")
counts = {"uye": len(members), "acik": sum(v == "acik" for v in vault.values()), "kasa": sum(v == "kasa" for v in vault.values())}
per_member_active = Counter()
deltas = []
for r in members:
    act = fz.active_records(r["ticker"], rd)
    per_member_active[len(act)] += 1
    for p, rec in act:
        if rec.get("record_scope") == fz.OOT_DELTA_SCOPE:
            deltas.append((p, rec))
print("uye sayilari", json.dumps(counts))
print("etkin kayit sayisi -> uye sayisi", dict(sorted(per_member_active.items())))
print("ek kayit dosyasi", len(deltas))
checks = Counter()
status = {m: {"acik": Counter(), "kasa": Counter()} for m in NEW}
codes = {m: {"acik": Counter(), "kasa": Counter()} for m in NEW}
new_keys = Counter()
git_heads, dirty = Counter(), Counter()
for p, rec in deltas:
    t = rec["ticker"]
    v = vault[t]
    first_path, first = fz.oot_base_record(t, rd)
    checks["8_model_sirasi_dogru"] += [c["model_id"] for c in rec["models"]] == NEW
    checks["girdiler_bayt_esit"] += fz.oot_delta_problems(first, rec) == []
    checks["delta_of_ilk_kayit"] += rec["delta_of"] == first_path.name and rec["delta_of_sha256"] == sha256_file(first_path)
    checks["ilk_kayit_19_model"] += len(first["models"]) == 19
    checks["models_index_sha_guncel"] += rec["models_index"]["sha256"] == index_sha
    checks["sonuc_alani_yok"] += not (set(reg.json_keys(rec)) & reg.OOT_OUTCOME_KEYS)
    checks["stage_OOT_PRE_LISTING"] += rec["record_stage"] == fz.OOT_STAGE
    checks["karsilastirici_bos"] += rec["comparators"] == {}
    checks["tufe_ay_T_eksi_2"] += rec["tufe"]["refusal"] is None and rec["tufe"]["month"] is not None
    checks["alloc_regime_kohort_etiketi"] += rec["model_inputs"]["alloc_regime"] == reg.parse_regime_tags(
        rec["cohort_row"]["regime_tags"])["ALLOC_REGIME"]
    new_keys[tuple(sorted(set(rec["model_inputs"]) - set(first["model_inputs"])))] += 1
    git_heads[rec["code"]["git_head"][:7]] += 1
    dirty[rec["code"]["borsai_dirty"]] += 1
    for c in rec["models"]:
        status[c["model_id"]][v][c["status"]] += 1
        if c["status"] == "REFUSED":
            codes[c["model_id"]][v][c["refusal"]["code"]] += 1
        elif c["status"] == "NOT_APPLICABLE_REGIME":
            codes[c["model_id"]][v]["NA:" + c["not_applicable"]["code"]] += 1
print("denetimler (her biri ek kayit sayisina esit olmali)", json.dumps(dict(checks), ensure_ascii=False))
print("model_inputs'a eklenen anahtarlar", {"|".join(k): n for k, n in new_keys.items()})
print("code.git_head", dict(git_heads), "borsai_dirty", dict(dirty))
print()
# Hijyen: rejimle uygulanamaz (NA) hücreler açık/kasa ayrımıyla BASILMAZ (tek MARGIN üyesinin adı belgelerde geçer; ayrım onun kasa
# durumunu çıkarsanabilir kılar). Ret kodları ayrımla basılır (şartname/KARARLAR belgelerinde zaten ayrımlı sayılar var).
print("model | toplam: PREDICTED / REFUSED / NA | acik: REFUSED | kasa: REFUSED | ret kodlari (acik; kasa) | NA kodlari (toplam)")
for m in NEW:
    a, k = status[m]["acik"], status[m]["kasa"]
    na = Counter({c: n for v in ("acik", "kasa") for c, n in codes[m][v].items() if c.startswith("NA:")})
    ref = lambda v: {c: n for c, n in codes[m][v].items() if not c.startswith("NA:")}  # noqa: E731
    print(f"{m} | {a['PREDICTED'] + k['PREDICTED']} / {a['REFUSED'] + k['REFUSED']} / "
          f"{a['NOT_APPLICABLE_REGIME'] + k['NOT_APPLICABLE_REGIME']} | {a['REFUSED']} | {k['REFUSED']} | "
          f"{ref('acik')}; {ref('kasa')} | {dict(na)}")
tot = Counter()
for m in NEW:
    for v in ("acik", "kasa"):
        tot.update(status[m][v])
print("toplam hucre", sum(tot.values()), dict(tot))
