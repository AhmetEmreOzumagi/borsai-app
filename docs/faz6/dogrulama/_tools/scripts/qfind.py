"""Belge metninde düzenli ifade arar, normalize edilmiş birebir alıntı adaylarını basar.
Kullanım: python3 qfind.py TICKER SOURCE_ID 'regex'   (SOURCE_ID: KAP_<id>, KAP_<id>_EK<n>, SPK)"""
import re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from blib import fulltext
from check_decision import doc_map
t,sid,pat=sys.argv[1:4]
dm=doc_map(t)
if sid not in dm: sys.exit(f"yok: {sid}; mevcut: {sorted(dm)}")
tx=fulltext(dm[sid])
for m in re.finditer(pat,tx,re.I):
    print(repr(tx[max(0,m.start()-int(sys.argv[4]) if len(sys.argv)>4 else m.start()):m.end()]))
