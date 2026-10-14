"""Metin çıkarımı (eksikse) + dossier. codex python ile çalıştır: prep.py T [T ...]"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from pdftext import extract
import blib, dossier
for t in sys.argv[1:]:
    d=blib.tick(t)
    for doc in d['docs']:
        for p in [doc['pdf']]+[a['path'] for a in doc['attachments'] if a.get('path')]:
            extract(Path(p))
    blib._TEXT=None
    n=dossier.build(t)
    miss=(dossier.OUT/f"{t}.md").read_text().count('METİN YOK')
    print(t,n,'METİN YOK' if miss else 'ok')
