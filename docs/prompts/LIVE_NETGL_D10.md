# TASK_ID: BORSAI_LIVE_NETGL_D10_20260930

Model: Sonnet 5 · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ: yalnız `www.borsaistanbul.com` THB/THM bülten URL'leri** (`outcomes.source_url`; HEAD probu + zip indirme). push/tag/amend yok.

## Rol
NETGL'nin (ilk işlem günü 2026-09-17) D4…D10 sonuçlarını resmi bültenden alır, canlı skorları yeniden üretir ve kısa bir rapor yazar. Kalıp: `docs/prompts/FAZ2B_OUTCOMES_SCORING.md` (adım 6 sonrası) ve `docs/prompts/FAZ5_LIVE_B_APPFIX.md`.

## Bağlam
- `data/outcomes/NETGL.csv`: h = 1…3 `OK` (2026-09-17, 18, 21), h = 4…10 `PENDING`. D10 beklenen tarih 2026-09-30 (takvime göre ölç).
- Sonuç yalnız resmi THB/THM'den gelir (CLAUDE.md kural 6). Proje sahibinin ekranda gördüğü fiyat yalnız etikettir; hiçbir dosyaya yazılmaz.
- NETGL, v1 ve (C) modelleri için RETRO'dur (kayıt dondurmadan önce). `post_d1_hazard_v0` için de RETRO'dur (HANDOFF). Canlı n'i abartma.
- Skor dosyaları değişince uygulama testlerinde skor içeriğini sayan pinler kırılabilir. J31 kalıbında asgari yeniden pin **önceden onaylıdır**:
  - ayrı commit;
  - yalnız sayı/sha/fikstür satırları.
  
  Rust ya da UI mantığı değişmesi gerekirse DUR.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görev hiçbir model, kod ya da şartnameyi değiştirmez.
- **Test komutları** (`docs/ENV.md`): ara koşular `.venv/bin/pytest -q -n 6 --dist loadgroup`; her commit'ten önceki son kabul koşusu sıralı `.venv/bin/pytest -q`.

## İzinli izlenmeyen
Yalnız bu görev dosyası. Başka bir şey varsa DUR.

## ÖNCE OKU
CLAUDE.md; `docs/specs/SPEC_SCORING.md` §2–§5; `docs/prompts/FAZ2B_OUTCOMES_SCORING.md`; `borsai/outcomes.py` (CLI: `update`, `completeness`); `docs/ENV.md`.

## Adımlar
0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` = `origin/main`; ağaçta yalnız bu görev dosyası.
   - `data/outcomes/*.csv` dosyalarının sha256'larını `/tmp/borsai_netgl/before/`'a kaydet.
1. **Yayın denetimi (ilk ağ işi).** D10 tarihinin THB'sine HEAD at (`borsai.outcomes_oot.head_status(borsai.outcomes.source_url(<D10>, "thb"))`).
   - 200 değilse **hiçbir şey indirmeden DUR**: "D10 bülteni henüz yayımlanmadı". Proje sahibi sonra aynı cümleyle yeniden başlatır.
2. **Sonuçlar:** `.venv/bin/python -m borsai.outcomes update --through <D10>`. Beklenen:

   | Denetim | Beklenen |
   |---|---|
   | `data/outcomes/NETGL.csv` | h = 1…3 bayt-eşit; h = 4…10 dolu (`OK`, ya da nedenli `NA_LIMIT`/`TARGET_UNAVAILABLE`); `PENDING` 0 |
   | diğer canlı arzların sonuç dosyaları | bayt-eşit (adım 0 sha'ları) |
   | `data/raw/bist/` | yalnız yeni seansların zip'leri (THB+THM); MANIFEST yalnız ekleme; her yeni sha dosyayla eşit |

   Tutmazsa commit etme, DUR.
3. **Payda denetimi:** `.venv/bin/python -m borsai.outcomes completeness --through <D10>`.
   - `data/outcomes/COMPLETENESS.csv` değişirse yalnız ekleme olmalı.
   - Yeni satırlardan `registry/ipos.csv`'de olmayan bir halka arz varsa DUR ve raporla: yeni arz = öncelikli iş, orkestratör karar verir.
   - Kasa bekçisi (`KNOWN_COMPLETENESS_SEALED_ROWS`) kırmızı olursa DUR.
4. **Commit O** (sonuç satırları + zip'ler + MANIFEST + varsa COMPLETENESS).
   - Yalnız bu yeni dosyalar yüzünden kırmızı olan temizlik bekçileri deselect edilir; sıra kuralı ve kasa bekçileri deselect edilmez.
   - Deselect'li sıralı koşu yeşil → commit O → deselect'siz sıralı koşu yeşil.
5. **Skorlar:** `.venv/bin/python -m borsai.scoring` (bayraksız; `--oot` DEĞİL).
   - `scores.json`, `scores_post_d1.json`, `SCORES.md` değişir. `scores_oot.json` ve `SCORES_OOT.md` bayt-eşit kalmalı.
   - `as_of_session` = D10.
   - Farkı özetle: hangi hücre ve sayaç değişti. Beklenen: yalnız NETGL satırları ve bunlardan türeyen hücreler/sayaçlar, `as_of_session`, kod/zaman damgaları.
   - `bash app/scripts/test.sh` ve `gen_golden --check`. Pin kırılırsa önceden onaylı APPPIN (ayrı commit).
   - Son sıralı pytest + test.sh yeşil → **commit S** (+ gerekirse **APPPIN**).
6. **Rapor** `docs/live/NETGL_D10_RAPOR.md` (commit R). İçerik:
   - hash'ler;
   - NETGL'nin D1…D10 kapanışları, tavan etiketleri ve gerçekleşen seri uzunluğu L;
   - D3/D5/D10 getirileri; D10 kapanışı arz fiyatının altında mı (y4);
   - donmuş kayıttaki (listeleme öncesi) `ceiling_hazard_v0` tahmini: medyan L, P(L ≥ 3), P(L ≥ 5) ve gerçekleşen;
   - V1.5 D5/D10 medyan getiri tahmini ve gerçekleşen;
   - canlı sicilin yeni sayaçları. Terazi adı "canlı"; n küçük, hüküm yok.
   - Push bloğu (sonuç satırları sıra iddiası taşır, kanıt gerekir):
   ```
   cd ~/Desktop/BorsAi
   git push origin main
   .venv/bin/python -m borsai.push_proof <O>
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: NETGL D4-D10 outcomes (<O>)" -- registry/push_proofs
   git push origin main
   git --no-pager log --oneline -3 origin/main
   ```

## Kurallar
- **Yazılabilir:**
  - yalnız CLI ile: `data/outcomes/`, `data/raw/bist/` (yeni seanslar), `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`;
  - `app/` yalnız önceden onaylı pin satırları;
  - `docs/live/`, bu görev dosyası.
- **Salt okunur:** `borsai/`, `models/`, `registry/`, `tests/`, `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/specs*`, `CLAUDE.md`, `legacy/`.
- Sonuç dosyaları elle düzenlenmez.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler (değişmeyen yolu pathspec'ten çıkar):
  ```
  git add data/outcomes data/raw/bist docs/prompts/LIVE_NETGL_D10.md
  git commit -m "BORSAI_LIVE_OUTCOMES: NETGL D4-D10 official THB/THM outcomes" -- data/outcomes data/raw/bist docs/prompts/LIVE_NETGL_D10.md
  git add scores/scores.json scores/scores_post_d1.json docs/SCORES.md
  git commit -m "BORSAI_LIVE_SCORES: live scores regenerated through NETGL D10" -- scores/scores.json scores/scores_post_d1.json docs/SCORES.md
  git add docs/live
  git commit -m "BORSAI_LIVE_NETGL_REPORT: NETGL realized path vs frozen predictions" -- docs/live
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** D10 bülteni yayımlanmıştı. NETGL h = 4…10 dolu; diğer sonuç dosyaları bayt-eşit; MANIFEST yalnız ekleme.
- **K2** Payda denetimi temiz ya da yeni arz raporlandı (DUR).
- **K3** Skorlar yeniden üretildi; `scores_oot.json` bayt-eşit; son sıralı pytest + test.sh + `gen_golden --check` yeşil.
- **K4** Commit'ler yalnız izinli yollarda; push yok.
