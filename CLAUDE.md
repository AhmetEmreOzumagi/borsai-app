# BorsAi — Claude Code çalışma notları

Amaç: Borsa İstanbul halka arzları için doğruluğu ölçülmüş tahmin modelleri ve onları gömülü çalıştıran bir masaüstü uygulaması.

Kurallar (dürüst doğruluk için en az set; kodla zorlanır):
1. Dondurma: resmi tahmin kaydı girdileri, kayıtlı TÜM modellerin çıktılarını ve her modelin parametre hash'ini birlikte içerir. İlk işlem gününden önce commit edilir ve uzak depoya push edilir; zaman kanıtı push'tur, yerel saat değil. Dondurulmuş kayıt silinmez; hatalıysa iptal kaydı düşülür. Her kayıt kendi aşamasının dizinindeki tüm modelleri içerir (listeleme öncesi: models/INDEX.json; POST_D1: models/INDEX_POST_D1.json). POST_D1 kaydının zaman sınırı D1'i izleyen ilk seans günü 09:40 (Europe/Istanbul), zaman kanıtı push kanıtıdır. Bir POST_D1 modeli, kendisinden sonra repoya giren her sonuç commit'inin atasıdır; ondan önce girmiş sonuçlar o model için RETRO'dur.
   POST_BREAK (kırılma akşamı) aşamasının kaydı makine sıralıdır: tahmin, dondurulmuş model JSON'u ile D_b'ye kadarki sha-pinli resmi bültenlerden ve listeleme öncesi girdi dosyasından skorlama anında deterministik üretilir, `registry/post_break/` altına append-only yazılır ve insan değer girmez. Bir arz bu aşamanın modeli için ancak modelin JSON'u, D_b'den sonraki ilk bülteni ya da h ≥ b + 1 sonucunu repoya sokan commit'in atası ve push kanıtlı ise prospektiftir; bu satırlar `MACHINE_SEQUENCED` sınıfıyla ayrı ölçekte (`live_break`) skorlanır, LIVE ile toplanmaz, kırılımı her zaman görünür. T_open'dan önce push kanıtlı bir insan kaydı varsa satır LIVE olur.
2. Payda: başlangıçtan sonra işlem görmeye başlayan her arz sicile girer. Dondurulmadıysa nedeniyle birlikte "atlandı" satırı olur.
3. Üç terazi, asla toplanmaz: backtest (retrospektif walk-forward), canlı (prospektif) ve zaman-dışı eski kohort (2023-09-22 öncesi arzlar; tahminler sonuç repoya girmeden push edilir). Bir arz bir model için ancak modelin JSON'u o arzın sonucu repoya girmeden önce dondurulduysa prospektiftir. Bu, tarihlerden hesaplanır; elle etiketlenmez.
4. Deney günlüğü: her backtest koşusu (model_id, spec hash, veri hash, metrikler, zaman) append-only günlüğe otomatik yazılır.
5. Değişiklik = yeni model_id: özellik, ön işleme, ızgara, eğitim kesimi ya da veri sürümü değişirse yeni kimlik verilir. Eskisi ve skorları listede kalır.
6. Skorlama: sonuç yalnız resmi THB/THM'den gelir. Tanımlar ilk skorlamadan önce kodda yazılıdır. Her model basit kurallarla (her zaman tavan, eğitim medyanı, taban oranı, son-10 taban oranı) aynı arzlarda eşleşik skorlanır. Doğruluk fark + aralık + n ile raporlanır; "geçiyor" denebilmesi için aralığın 0'ı dışlaması gerekir.

Sıra kuralı: 2026-08-19 sonrası THB/THM verisi ve 2026-08-06 sonrası listelenen arzların sonuçları, Faz 1 model JSON'ları dondurulmadan repoya alınmaz. Eski kohortun sonuç verisi, kohortun bütün listeleme öncesi tahmin kayıtları push edilmeden repoya alınmaz; kasadaki arzların sonuçları, doğrulanacak özellik önceden kaydedilip push edilmeden alınmaz.
Veri yalnız resmi kaynaklardan gelir (KAP, SPK, Borsa İstanbul); ikincil kaynak etiketlenir.
git push, tag ve amend yalnız proje sahibi tarafından yapılır.
legacy/ eski repodan birebir kopyadır; değiştirilmez.

Ortam: .venv (Python 3.12); bağımlılıklar pyproject.toml ve requirements.lock'ta. Testler: .venv/bin/pytest -q
Eski repo (arşiv, salt okunur): ~/Desktop/Halka_Arz_Modeli. Envanter: docs/checkup_20260921/CHECKUP.md; denetim: docs/fable_audit_20260921/AUDIT.md
