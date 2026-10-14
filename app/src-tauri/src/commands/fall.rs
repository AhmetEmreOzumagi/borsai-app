//! "Düşüş (D10) — arz fiyatının altına düşme olasılığı" kartı (SPEC_APP EK 3 §8.4; K-P4-1, K-P4-2). Tavan serisi
//! kartının hemen altında, aynı genişlikte ikinci özet kart; `CeilingSummary.fall` olarak derlenir (senaryo: `predict_all`
//! çıktıları; resmi görünüm: YALNIZ dondurulmuş kaydın hücreleri, model yeniden çalıştırılmaz).
//!
//! Bütün sayılar burada: P(D_h kapanışı ≤ arz fiyatı) = 1 − p_up (Python `predict_fall.fall_probability`) ve gösterim
//! yüzdeleri (k = 100 · (1 − p_up)'un en yakın tamsayısı, tamamlayan 100 − k). Terazi sütunları dosyalardan: yakın dönem
//! `scores.json` `backtest.near_era` (etiket + karşılaştırıcı), zaman-dışı `scores_oot.json` `oot_pre_h99_sealed` birincil
//! hücresi (verdict + karşılaştırıcı), canlı `scores.json` `live` (n < 10 → hüküm yok). Değerler toplanmaz. Öne çıkarma
//! `scores::featured_fall` (SPEC_C_V0 §5.5; dosyadaki alanların karşılaştırması). Hiçbir model listeden kalkmaz; V1.5'in
//! p_up sütunu Grup A'da olduğu gibi kalır.
use serde::Serialize;
use serde_json::Value;

use super::ceiling::{vault_of, ScoresSourceInfo, SummaryModel, VaultView};
use super::predict::TufeInfo;
use super::scores::{featured_fall, live_of, near_era_of, FeaturedFall, IntegrityProblem, LiveView, NearEraView, FALL_CANDIDATES};
use super::scores_oot::{info_of, ScoresOotDoc, ScoresOotInfo};

/// Kural satırı ("basit kural: havuz oranı") ve karşılaştırıcılar (Grup A'daki p_up'tan; "karşılaştırıcı" rozeti).
pub const FALL_RULE: &str = "fall_d10_v0_pooled@ZERO";
pub const FALL_COMPARATORS: [&str; 2] = ["base_rate", "v1_5_h99"];
/// Kartın ufukları: birincil D10, ikincil D5 (KARARLAR_C C3).
pub const FALL_HORIZONS_SHOWN: [&str; 2] = ["D10", "D5"];

/// Bir ufukta gösterilecek değerler (Rust'ta türetilir; ön uç yalnız biçimlendirir).
#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct FallCell {
    /// P(kapanış > arz) (modelin çıktısı).
    pub p_up: Option<f64>,
    /// P(D_h kapanışı ≤ arz fiyatı) = 1 − p_up.
    pub p_fall: Option<f64>,
    /// round(100 · p_fall) ve 100 − o değer ("%k" ve "%(100 − k)"; EK 3 §8.4-2).
    pub pct_fall: Option<i64>,
    pub pct_up: Option<i64>,
}

fn cell_of(output: &Value, h: &str) -> FallCell {
    let Some(p_up) = output.get(h).and_then(|c| c.get("p_up")).and_then(Value::as_f64).filter(|x| x.is_finite()) else {
        return FallCell::default();
    };
    let p_fall = 1.0 - p_up;
    let k = (p_fall * 100.0).round() as i64;
    FallCell { p_up: Some(p_up), p_fall: Some(p_fall), pct_fall: Some(k), pct_up: Some(100 - k) }
}

/// Model kartı satırı (EK 3 §8.4-4): "ne yapar" (parametre dosyasının `description`'ı), eğitim n ve kesim, sha ilk 8, varyant
/// sayısı (`scores.json` `card`), birincil hücre (`primary_cell`).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FallCard {
    pub description: Option<String>,
    pub training_n: Option<Value>,
    pub training_cutoff: Option<Value>,
    pub params_sha256_8: Option<String>,
    pub n_variants_same_data: Option<Value>,
    pub primary_cell: Option<Value>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FallRow {
    pub model_id: String,
    /// FEATURED | CANDIDATE | RULE | COMPARATOR
    pub role: &'static str,
    /// Resmi görünüm: kayıt bu modeli içermiyor (kayıt INDEX'ten eski) → false.
    pub in_record: bool,
    pub status: Option<String>,
    pub refused: Option<Value>,
    pub d10: FallCell,
    pub d5: FallCell,
    pub near_era: Option<NearEraView>,
    pub vault: VaultView,
    pub live: LiveView,
    /// Adayda sağlanmayan ilk koşul (`k1` | `k2` | `k3`; kasa kapalıyken ya da uygun adayda null).
    pub first_failed: Option<&'static str>,
    pub card: Option<FallCard>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FallSummary {
    pub featured: FeaturedFall,
    pub official: bool,
    pub record_file: Option<String>,
    pub rows: Vec<FallRow>,
    /// Fail-closed: (C) modelinin yakın dönem bloğu sözleşmeye aykırı → kart yerine ihlal.
    pub integrity: Option<IntegrityProblem>,
    pub scores: Option<ScoresSourceInfo>,
    pub oot: Option<ScoresOotInfo>,
    pub tufe: Option<TufeInfo>,
}

fn card_of(scores: Option<&Value>, params: Option<&Value>, model_id: &str) -> FallCard {
    let m = scores
        .and_then(|d| d.get("models"))
        .and_then(Value::as_array)
        .and_then(|a| a.iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id)));
    let card = m.and_then(|m| m.get("card"));
    FallCard {
        description: params.and_then(|p| p.get("description")).and_then(Value::as_str).map(str::to_string),
        training_n: card.and_then(|c| c.get("training_n")).cloned(),
        training_cutoff: card.and_then(|c| c.get("training_cutoff")).cloned(),
        params_sha256_8: card.and_then(|c| c.get("params_sha256_8")).and_then(Value::as_str).map(str::to_string),
        n_variants_same_data: card.and_then(|c| c.get("n_variants_same_data")).cloned(),
        primary_cell: m.and_then(|m| m.get("primary_cell")).filter(|p| !p.is_null()).cloned(),
    }
}

/// Kartı derler (saf; testler doğrudan çağırır). `refs`: gömülü model kümesi (INDEX sırası); (C) modeli gömülü değilse `None`.
pub fn fall_summary_value(
    models: &[SummaryModel],
    official: bool,
    record_file: Option<String>,
    refs: &[borsai_predict::ModelRef],
    scores: Option<(&Value, &'static str, &str)>,
    oot: Option<&ScoresOotDoc>,
    tufe: Option<TufeInfo>,
) -> Option<FallSummary> {
    let ids: Vec<String> = refs.iter().map(|m| m.model_id.clone()).collect();
    let params = |id: &str| refs.iter().find(|m| m.model_id == id).map(|m| m.params.clone());
    if !FALL_CANDIDATES.iter().chain([&FALL_RULE]).any(|c| ids.iter().any(|x| x == c)) {
        return None;
    }
    let sdoc = scores.map(|(d, ..)| d);
    let featured = featured_fall(sdoc, oot.and_then(ScoresOotDoc::usable), &ids);
    let mut integrity = None;
    let mut order: Vec<(&str, &'static str)> = Vec::new();
    if let Some(f) = featured.model_id.as_deref() {
        order.push((f, "FEATURED"));
    }
    for c in FALL_CANDIDATES {
        if featured.model_id.as_deref() != Some(c) {
            order.push((c, "CANDIDATE"));
        }
    }
    order.push((FALL_RULE, "RULE"));
    order.extend(FALL_COMPARATORS.iter().map(|c| (*c, "COMPARATOR")));
    let by_id = |id: &str| models.iter().find(|m| m.model_id == id);
    let mut rows = Vec::new();
    for (id, role) in order {
        if !ids.iter().any(|x| x == id) {
            continue;
        }
        let m = by_id(id);
        let comparator = role == "COMPARATOR";
        let near_era = match (comparator, sdoc.map(|d| near_era_of(d, id))) {
            (false, Some(Ok(v))) => v,
            (false, Some(Err(p))) => {
                integrity.get_or_insert(p);
                None
            }
            _ => None,
        };
        let output = m.filter(|m| m.status == "PREDICTED").map(|m| &m.output);
        let none_vault = VaultView { status: "NONE", verdict: None, diff: None, ci95: None, n: None, rule_id: None };
        rows.push(FallRow {
            model_id: id.to_string(),
            role,
            in_record: m.is_some(),
            status: m.map(|m| m.status.clone()),
            refused: m.filter(|m| m.status != "PREDICTED").map(|m| m.refusal.clone()),
            d10: output.map(|o| cell_of(o, "D10")).unwrap_or_default(),
            d5: output.map(|o| cell_of(o, "D5")).unwrap_or_default(),
            near_era,
            vault: if comparator { none_vault } else { vault_of(oot, id) },
            live: if comparator { LiveView::default() } else { sdoc.map(|d| live_of(d, id)).unwrap_or_default() },
            first_failed: featured.candidates.iter().find(|c| c.model_id == id).and_then(|c| c.first_failed),
            card: (!comparator).then(|| card_of(sdoc, params(id).as_ref(), id)),
        });
    }
    Some(FallSummary {
        featured,
        official,
        record_file,
        rows,
        integrity,
        scores: scores.map(|(d, source, sha)| ScoresSourceInfo {
            source,
            sha12: sha.to_string(),
            generated_at_utc: d.get("generated_at_utc").and_then(Value::as_str).map(str::to_string),
        }),
        oot: oot.map(info_of),
        tufe,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn fall_cell_complement() {
        let c = cell_of(&json!({"D10": {"p_up": 0.8371493107629145}}), "D10");
        assert_eq!(c.p_fall, Some(1.0 - 0.8371493107629145));
        assert_eq!((c.pct_fall, c.pct_up), (Some(16), Some(84)));
        // %k + %(100 − k) = 100 her zaman
        let c = cell_of(&json!({"D5": {"p_up": 0.835}}), "D5");
        assert_eq!(c.pct_fall.unwrap() + c.pct_up.unwrap(), 100);
        assert_eq!(cell_of(&json!({"D10": null}), "D10"), FallCell::default());
    }
}
