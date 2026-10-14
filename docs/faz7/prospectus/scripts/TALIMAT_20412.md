# Görev: 20/412 (i-SPK.128.21) ortak kısıtı uyumlaştırması — yalnız `shareholder_lockup_days`

Çalışma dizini: `W=/Users/ahmet/Desktop/BorsAi_codex/verified_faz7/_tools` (`cd $W/scripts && ...`). Ağ YOK. Yalnız `$W/decisions/<T>.json` içindeki **`fields.shareholder_lockup_days`** ve **`codex_check.shareholder_lockup_days`** değişir; başka alana/dosyaya dokunma; repo `~/Desktop/BorsAi`'ye dokunma. Sonuç körlüğü kuralları geçerli (ilk işlem günü sonrası fiyat vb. yok).

## Arka plan
SPK'nın 30.03.2023 tarihli 20/412 sayılı ilke kararı (i-SPK.128.21): halka arzda mevcut ortakların payları (halka arz edilen kısım hariç) izahname onay tarihinden itibaren belirli süre (çoğunlukla 180 gün) "borsada satışı da kapsayacak şekilde" borsa dışında satılamaz / virmanlanamaz / özel emir-toptan satışa konu edilemez. İzahneler bunu §27.3 (a/b/c/e), §25 (tahsis/dağıtım), Özet ya da risk faktörlerinde yazar; ortaklar ayrıca kendi taahhütlerinde tekrarlayabilir.

## Kural (talimat AGENT_TALIMAT.md ile aynı, burada kesinleştirildi)
1. Belge, mevcut ortakların payları için N günlük kısıtın **borsada satışı da kapsadığını** söylüyorsa ("borsada satışı da kapsayacak şekilde", "borsada veya borsa dışında satmayacak", "Borsa İstanbul'da veya Borsa İstanbul dışında hiçbir şekilde satmayacak") → `components`'e `{"who": "<kimler / mevcut ortaklar>", "days": "N", "type": "MUTLAK", "basis": "MEVZUAT i-SPK.128.21 (20/412)" (ya da ortak kendi taahhüdüyse "GONULLU"), "start": "izahname onay tarihi"}` ekle ya da mevcut bileşenin `type`'ını `MUTLAK` yap. Alıntısını `extra_quotes`'a ekle (araç çıktısından birebir).
2. Metin yalnız "borsa dışında satmama, virmanlamama, özel emir/toptan satış" diyor ve borsada satıştan söz etmiyorsa → `DIGER` (değeri belirlemez).
3. Aynı kısıt birden fazla yerde yazılıysa tek bileşen yeter (en açık yerden alıntı).
4. `value` = `MUTLAK`/`FIYAT_ALTI` bileşenlerinin **en kısa** süresi. Değerin süre ifadesi alıntılarda (quote ya da extra_quotes) görünmeli.
5. `note`'a ekle: `[20/412 uyumlaştırma: <ne değişti>]`. Değer değiştiyse eski değeri yaz.
6. `codex_check.shareholder_lockup_days` varsa: Codex değeri yeni değerle aynıysa `FOUND_SAME`, değilse `FOUND_DIFFERENT` (note'a neden).
7. `python3 check.py <T>` OK olana kadar düzelt.

Arama: `python3 qfind.py <T> 'borsada satışı da kapsayacak|borsa dışında veya borsada|borsada veya borsa dışında|Borsa İstanbul.da (veya|ya da) Borsa İstanbul dışında|20/412|128\.21' 300`; sayfa için `python3 page.py <T> <SID> <sayfa>`.

Bitince her ticker için: `T: ort eski→yeni · bileşenler (tür/gün) · değişiklik yok/var · OK`.
