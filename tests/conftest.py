from __future__ import annotations

import functools
import json
import subprocess

import pytest

from borsai import backtest as bt
from borsai.data import load_dataset
from borsai.provenance import ROOT


# Herkese açık ayna (AhmetEmreOzumagi/borsai-app; FAZ9_PUBLIC_MIRROR K-MIR-3, proje sahibi kararı 2026-10-13). Ayna ham bültenleri
# ve resmi belgeleri içermez ve tek commit'tir. Bunları isteyen testler aynada açıkça atlanır; yalnız atlama koşulu eklenir, test
# iddiaları değişmez. Özel repoda iki koşul da sağlanır: hiçbir test atlanmaz.
RAW_SOURCES_REASON = "ham bülten ve resmi belgeler herkese açık aynada yeniden dağıtılmaz"
GIT_HISTORY_REASON = "zaman kanıtı ve commit geçmişi özel repodadır; herkese açık ayna tek commit'tir"
PRIVATE_ROOT_COMMIT = "ff3eee64eadd70c61e8b2eff657fd98cb94a0d04"     # özel reponun ilk commit'i (BORSAI_V2_SKELETON)


@functools.cache
def raw_sources_present() -> bool:
    """`data/raw/bist/**.zip` (THB/THM bültenleri) ve `registry/**/source_docs/**/*.pdf` (KAP/SPK belgeleri) var mı."""
    return any((ROOT / "data" / "raw" / "bist").rglob("*.zip")) and any(ROOT.glob("registry/**/source_docs/**/*.pdf"))


@functools.cache
def git_history_present() -> bool:
    """Özel reponun commit geçmişi (ilk commit'ten bu yana) bu depoda var mı."""
    res = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{PRIVATE_ROOT_COMMIT}^{{commit}}"], capture_output=True)
    return res.returncode == 0


def pytest_configure(config):
    config.addinivalue_line("markers", f"requires_raw_sources: ham bülten zip'i ya da KAP/SPK PDF'i ister ({RAW_SOURCES_REASON})")
    config.addinivalue_line("markers", f"requires_git_history: özel reponun commit geçmişini ister ({GIT_HISTORY_REASON})")


# default_workers() süreçlik (9) havuz açan test modülleri. Sıralı koşuda ölçüldü (havuz açılışları test kimliğiyle kaydedildi);
# yeni bir modül havuz açıyorsa buraya eklenmezse yalnız paralel koşu yavaşlar, sonuç değişmez.
POOL_MODULES = frozenset({
    "tests/test_acceptance_backtest.py",
    "tests/test_faz5_golden.py",
    "tests/test_faz5_post_d1.py",
    "tests/test_faz7_golden.py",
    "tests/test_faz7c_golden.py",
    "tests/test_market20.py",
})


def xdist_group_of(item) -> str:
    module = item.nodeid.split("::", 1)[0]
    return "backtest_pool" if "backtest_results" in item.fixturenames or module in POOL_MODULES else module


@pytest.hookimpl(tryfirst=True)  # xdist işçisi grup adını düğüm kimliğine bu kancadan sonra yazar; işaret ondan önce eklenmeli
def pytest_collection_modifyitems(items):
    """Paralel koşu (`pytest -n N --dist loadgroup`) için gruplama; sıralı koşuda etkisizdir.

    Aynı gruptaki testler tek işçide, sıralı koşudaki sırayla koşar; test mantığı ve iddialar değişmez.
    - Oturum ve modül kapsamlı pahalı fixture'lar her xdist işçisinde baştan kurulur; bu yüzden testler modüllerine göre gruplanır.
    - Backtest havuzu (`bt.run_all`, `default_workers()` = 9 süreç) zaten bütün çekirdekleri ve belleği kullanır; havuzlar aynı
      anda koşarsa (ölçüm: 10 işçide 44 dk, sıralı 15 dk) çekirdek ve bellek aşırı yüklenir. `backtest_results` kullanan ve
      `POOL_MODULES` içindeki testler tek grupta koşar: aynı anda en çok bir havuz.
    - Herkese açık aynada `requires_raw_sources` / `requires_git_history` işaretli testlere, koşul sağlanmıyorsa gerekçeli atlama
      eklenir (K-MIR-3). Özel repoda iki koşul da sağlanır; etkisizdir.
    """
    for item in items:
        item.add_marker(pytest.mark.xdist_group(xdist_group_of(item)))
        # herkese açık ayna: koşul sağlanmıyorsa açık atlama (yukarıda; özel repoda etkisiz)
        if item.get_closest_marker("requires_raw_sources") and not raw_sources_present():
            item.add_marker(pytest.mark.skip(reason=RAW_SOURCES_REASON))
        if item.get_closest_marker("requires_git_history") and not git_history_present():
            item.add_marker(pytest.mark.skip(reason=GIT_HISTORY_REASON))


@pytest.fixture(scope="session")
def dataset():
    return load_dataset()


@pytest.fixture(scope="session")
def test_log_path(tmp_path_factory):
    """Test paketinin backtest koşuları bu geçici günlüğe yazılır (experiments/README.md)."""
    return tmp_path_factory.mktemp("experiment_log") / "log.jsonl"


@pytest.fixture(scope="session")
def backtest_results(dataset, test_log_path):
    """Tüm modellerin H99 walk-forward backtest'i; oturumda bir kez koşar."""
    return bt.run_all(dataset, log_path=test_log_path, context="pytest")


@pytest.fixture(scope="session")
def frozen_models():
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    return {
        e["model_id"]: json.loads((ROOT / "models" / e["file"]).read_text(encoding="utf-8"))
        for e in index["models"]
    }
