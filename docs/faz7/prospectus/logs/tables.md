## Alan başına kapsama (önce = Codex OK; sonra = doğrulanmış dolu)

| Alan | Codex OK (önce) | Sonra (dolu) | VERIFIED | CORRECTED | FILLED | MISSING | Codex UNVERIFIABLE |
|---|---|---|---|---|---|---|---|
| `distribution_method` | 85 | 135 | 80 | 5 | 50 | 0 | 0 |
| `price_stability_planned` | 99 | 135 | 99 | 0 | 36 | 0 | 0 |
| `price_stability_days` | 93 | 135 | 93 | 0 | 42 | 0 | 0 |
| `issuer_lockup_days` | 76 | 135 | 73 | 3 | 59 | 0 | 0 |
| `shareholder_lockup_days` | 83 | 135 | 80 | 3 | 52 | 0 | 0 |
| `sector` | 89 | 135 | 89 | 0 | 46 | 0 | 0 |
| `participation_index_eligible` | 7 | 31 | 7 | 0 | 24 | 104 | 0 |
| **toplam (945 hücre)** | 532 | 841 | 521 | 11 | 309 | 104 | 0 |

## Codex doğruluk oranı (Codex'in OK verdiği değerler)

| Alan | Codex OK | VERIFIED | CORRECTED | UNVERIFIABLE | doğruluk (VERIFIED/OK) |
|---|---|---|---|---|---|
| `distribution_method` | 85 | 80 | 5 | 0 | 94.1% |
| `price_stability_planned` | 99 | 99 | 0 | 0 | 100.0% |
| `price_stability_days` | 93 | 93 | 0 | 0 | 100.0% |
| `issuer_lockup_days` | 76 | 73 | 3 | 0 | 96.1% |
| `shareholder_lockup_days` | 83 | 80 | 3 | 0 | 96.4% |
| `sector` | 89 | 89 | 0 | 0 | 100.0% |
| `participation_index_eligible` | 7 | 7 | 0 | 0 | 100.0% |
| **toplam** | 532 | 521 | 11 | 0 | 97.9% |

Parti bazında (VERIFIED / CORRECTED / UNVERIFIABLE):

- B1 (34 arz): 101 / 2 / 0
- B2 (26 arz): 126 / 2 / 0
- B3 (38 arz): 183 / 2 / 0
- B4 (37 arz): 111 / 5 / 0

## Değer dağılımı (yalnız biçim kontrolü için)

- `distribution_method`: "Borsa İstanbul Birincil Piyasa; yatırımcı grubu bazında tahsisat ve dağıtım yapılmadı": 45, "Yurt içi bireysele eşit; kurumsala takdire bağlı dağıtım": 24, "Yurt içi bireysele oransal; kurumsala takdire bağlı dağıtım": 20, "Yurt içi bireysel ve çalışanlara eşit; kurumsala takdire bağlı dağıtım": 17, "Yurt içi bireysel ve yüksek başvuruluya oransal; kurumsala takdire bağlı dağıtım": 12, "Yurt içi bireysel ve çalışanlara oransal; kurumsala takdire bağlı dağıtım": 8, "Borsa'da satış; yatırımcı grubu tahsisatı yok; eşit dağıtım": 4, "Yurt içi bireysel, yüksek başvurulu ve çalışanlara oransal; kurumsala takdire bağlı dağıtım": 3, "Yurt içi bireysel ile Torunlar Grubu ve çalışanlara oransal; kurumsala takdire bağlı dağıtım": 1, "Yurt içi bireysele eşit; çalışanlara oransal; kurumsala takdire bağlı dağıtım": 1
- `price_stability_planned`: "TRUE": 80, "FALSE": 55
- `price_stability_days`: "30": 72, "0": 55, "15": 5, "10": 2, "20": 1
- `issuer_lockup_days`: "365": 88, "180": 40, "540": 3, "0": 2, "730": 2
- `shareholder_lockup_days`: "365": 72, "180": 52, "540": 6, "730": 3, "120": 1, "450": 1
- `sector`: "dolu": 135
- `participation_index_eligible`: null: 104, "TRUE": 31