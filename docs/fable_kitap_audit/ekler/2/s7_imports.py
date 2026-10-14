"""Adım 7: predict*.py ve kullandığı borsai modüllerinin import kapanışı (AST; çalıştırmadan)."""
import ast, sys
from pathlib import Path
ROOT = Path('/Users/ahmet/Desktop/BorsAi/borsai')
STDLIB = set(sys.stdlib_module_names)
def imports(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names: out.append((a.name, node.lineno, False))
        elif isinstance(node, ast.ImportFrom):
            out.append((('.' * node.level) + (node.module or ''), node.lineno, True))
    return out
starts = sorted(p.name for p in ROOT.glob('predict*.py'))
for start in starts:
    seen, queue, third, local, inner = set(), [start], set(), set(), {}
    while queue:
        name = queue.pop()
        if name in seen: continue
        seen.add(name)
        for mod, line, isfrom in imports(ROOT / name):
            if mod.startswith('.'):
                sub = mod.lstrip('.')
                if sub:
                    fn = sub + '.py'
                    local.add(fn); queue.append(fn)
                else:
                    # from . import x, y
                    tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None and node.lineno == line:
                            for a in node.names:
                                fn = a.name + '.py'
                                if (ROOT / fn).exists(): local.add(fn); queue.append(fn)
            elif mod.split('.')[0].startswith('borsai'):
                fn = mod.split('.')[1] + '.py' if '.' in mod else None
                if fn: local.add(fn); queue.append(fn)
            else:
                top = mod.split('.')[0]
                (inner.setdefault(name, set())).add(top)
                if top not in STDLIB: third.add((name, top, line))
    print(f"== {start}: kapanış = {sorted(seen)}")
    print(f"   stdlib dışı: {sorted(third) if third else 'YOK'}")
    allmods = sorted({m for s in inner.values() for m in s})
    print(f"   kullanılan stdlib modülleri: {allmods}")
# eğitim tarafı
for f in ('fit.py', 'hazard.py', 'ceiling_path.py', 'backtest.py', 'freeze.py'):
    th = sorted({m.split('.')[0] for m, l, _ in imports(ROOT / f) if not m.startswith('.') and not m.startswith('borsai') and m.split('.')[0] not in STDLIB})
    print(f"eğitim {f}: stdlib dışı = {th}")
