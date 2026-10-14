"""Eşleşen KAP satırlarından indirilecek bildirimleri seçer (ek/annex görünümlü izahname parçaları hariç)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import T  # noqa: E402
from match import fold  # noqa: E402

ANNEX = re.compile(r"(\bek(ler|leri|i)?\b|\bek[-_ ]?\d|ekleri|denetim|degerleme|hukukcu|rodovans|esas sozlesme|"
                   r"fiyat tespit|bilanco|mali tablo|finansal|ekspertiz|sozlesme|rapor)")
SPECIAL = re.compile(r"verilen taahhut|taahhut belge|taahhutname|katilim finans|katilim endeks|faizsiz|islami|icazet|"
                     r"satis duyuru|tasarruf sahip|fiyat istikrar")
KEEP = re.compile(r"(araci notu|ozet|ihracci bilgi|bolum|kisim|izahname\s*[-(]?\s*\d|\d+\s*-\s*\d+|/\d)")


def classify(h):
    s = h["subject"]
    if "Tasarruf Sahiplerine" in s:
        return "TSSD"
    if "Birincil Piyasada Halka Arzı" in s:
        return "BIST_BIRINCIL"
    if "Değişiklik" in s and "zahname" in s:
        return "IZAHNAME_DEGISIKLIK"
    if "zahname" in s:
        f = fold(h.get("summary") or "")
        if SPECIAL.search(f):
            return "IZAHNAME"
        if ANNEX.search(f) and not KEEP.search(f):
            return "IZAHNAME_EK"
        return "IZAHNAME"
    return None


if __name__ == "__main__":
    m = json.loads((T / "cache" / "matched.json").read_text())
    out = {}
    import collections
    c = collections.Counter()
    for t, v in m.items():
        out[t] = []
        for h in v:
            k = classify(h)
            c[k] += 1
            if k:
                out[t].append({**h, "role": k})
    (T / "cache" / "classified.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(c)
