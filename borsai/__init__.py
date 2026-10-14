"""BorsAi: Borsa İstanbul halka arz tahmin paketi.

Modüller:
  data       eğitim tablosu, seans tarihleri, PB girdileri ve sürüm doğrulaması (stdlib)
  features   f1–f5 ve pb1–pb4'ün tek tanımı (stdlib)
  market20   f6_market20 (XU100 20 seans getirisi) ve takvim sonu denetimi (stdlib)
  preprocess fold içi ön işleme ve tarifleri; parametreleri döndürür (stdlib)
  survival   tavan serisi kişi-dönem tablosu, Kaplan–Meier, S_k/P_L/P_close, RPS (stdlib)
  specs      kayıtlı model şartnameleri ve backtest planları (stdlib)
  rules      basit kurallar (stdlib)
  fit        fit(model_spec, training_rows) -> params (numpy, scikit-learn)
  hazard     ayrık zamanlı hazard modeli: Newton, λ seçimi (numpy)
  predict    predict(params, inputs); saf, yalnız stdlib (V1.5, V1.6)
  predict_market20, predict_pb, predict_hazard   diğer modellerin stdlib tahmini
  predict_post_d1  D1 sonrası güncelleme (post_d1_hazard_v0) tahmini; yalnız stdlib
  post_d1    D1 sonrası modelin D1 verisi, fit'i, walk-forward'u ve nihai fit önizlemesi (numpy)
  metrics    skorlama tanımları ve blok bootstrap (stdlib)
  backtest   walk-forward backtest ve deney günlüğü
  freeze     modelleri models/ altına dondurur; tahmin kaydı yazıcı (girdi JSON -> registry/records) (stdlib yolu)
  registry   payda (ipos.csv), girdi belgeleri ve inputs_pit_ok, legacy rolleri, birincil kayıt seçimi (stdlib)
  push_proof GitHub commit status ile push kanıtı (stdlib)
  outcomes   resmi BIST THB/THM indirici ve ayrıştırıcı, D_h / tavan etiketi, data/outcomes/<T>.csv, tamlık denetimi (stdlib)
  scoring    sınıf (LIVE/LATE_RECORD/RETRO), birincil kayıt, eşleşik metrik ve blok bootstrap, scores.json ve docs/SCORES.md
  report     docs/MODELS.md üreticisi (Faz 1B bölümü: report_faz1b; Faz 4: report_faz4; Faz 5: report_faz5)

Bu dosya bilerek hiçbir şey import etmez: `import borsai.predict` numpy yüklemez.
"""
