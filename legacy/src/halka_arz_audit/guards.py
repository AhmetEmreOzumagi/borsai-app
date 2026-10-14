"""Dosya, zaman kesiti ve model güncelleme güvenlik korumaları."""

from __future__ import annotations

import re
import tomllib
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PolicyViolation(RuntimeError):
    """Kalıcı proje güvenlik politikasının ihlal edildiğini bildirir."""


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def load_source_registry(path: Path) -> dict[str, dict[str, Any]]:
    """Sabit kaynak hash kaydını okur ve yapısal olarak doğrular."""
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if payload.get("hash_algorithm") != "sha256":
        raise PolicyViolation("Kaynak kaydı yalnızca sha256 kullanabilir")
    entries: dict[str, dict[str, Any]] = {}
    for item in payload.get("sources", []):
        name = item.get("file_name", "")
        digest = str(item.get("sha256", "")).lower()
        if not name or Path(name).name != name:
            raise PolicyViolation(f"Geçersiz kaynak dosya adı: {name!r}")
        if name in entries:
            raise PolicyViolation(f"Kaynak kaydında yinelenen dosya: {name}")
        if not SHA256_RE.fullmatch(digest):
            raise PolicyViolation(f"Geçersiz SHA-256: {name}")
        if item.get("immutable") is not True:
            raise PolicyViolation(f"Kayıtlı kaynak değişmez işaretlenmemiş: {name}")
        entries[name] = {**item, "sha256": digest}
    if not entries:
        raise PolicyViolation("Kaynak kaydı boş olamaz")
    return entries


def verify_registered_sources(
    sources: Iterable[Path],
    fingerprints: Mapping[Path, Mapping[str, Any]],
    registry: Mapping[str, Mapping[str, Any]],
    *,
    require_exact_set: bool,
    frozen_name_markers: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Keşfedilen kaynakları sabit kayıt ve dondurma kurallarıyla eşleştirir."""
    source_list = tuple(sources)
    source_by_name = {path.name: path for path in source_list}
    if len(source_by_name) != len(source_list):
        raise PolicyViolation("Aynı ada sahip birden fazla kaynak dosya var")
    discovered = set(source_by_name)
    registered = set(registry)
    if require_exact_set and discovered != registered:
        missing = sorted(registered - discovered)
        unknown = sorted(discovered - registered)
        raise PolicyViolation(
            f"Kaynak kümesi kayıtla eşleşmiyor; eksik={missing}, kayıtsız={unknown}"
        )

    markers = tuple(_normalized(marker) for marker in frozen_name_markers)
    results: dict[str, dict[str, Any]] = {}
    for name, path in source_by_name.items():
        if name not in registry:
            raise PolicyViolation(f"Kayıtsız kaynak reddedildi: {name}")
        entry = registry[name]
        fingerprint = fingerprints[path]
        actual_hash = str(fingerprint["sha256"]).lower()
        expected_hash = str(entry["sha256"]).lower()
        if actual_hash != expected_hash:
            raise PolicyViolation(
                f"Kaynak SHA-256 beklenen değerle eşleşmiyor: {name}; "
                f"beklenen={expected_hash}, bulunan={actual_hash}"
            )
        expected_size = entry.get("size_bytes")
        if expected_size is not None and int(fingerprint["size_bytes"]) != int(expected_size):
            raise PolicyViolation(f"Kaynak boyutu beklenen değerle eşleşmiyor: {name}")
        name_implies_frozen = any(marker in _normalized(name) for marker in markers)
        if name_implies_frozen and entry.get("frozen") is not True:
            raise PolicyViolation(
                f"Adı dondurulmuş içerik gösteren kaynak frozen=true değil: {name}"
            )
        results[name] = {
            "baseline_match": True,
            "immutable": True,
            "frozen": bool(entry.get("frozen")),
            "role": entry.get("role"),
            "expected_sha256": expected_hash,
        }
    return results


def assert_safe_output_path(
    path: Path,
    output_dir: Path,
    allowed_extensions: Iterable[str],
) -> None:
    """Türetilmiş çıktının güvenli klasör ve izinli uzantıda olduğunu zorlar."""
    resolved = path.resolve()
    output_dir = output_dir.resolve()
    allowed = {extension.lower() for extension in allowed_extensions}
    if not resolved.is_relative_to(output_dir) or resolved == output_dir:
        raise PolicyViolation(f"Çıktı güvenli klasörün dışında: {resolved}")
    if resolved.suffix.lower() not in allowed:
        raise PolicyViolation(f"İzin verilmeyen çıktı uzantısı: {resolved.suffix}")
    if resolved.suffix.lower() in {".xlsx", ".xlsm", ".xls", ".xlsb"}:
        raise PolicyViolation("Envanter hattı Excel çalışma kitabı yazamaz")


def _parse_aware_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PolicyViolation(f"{field} ISO-8601 metni olmalıdır")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PolicyViolation(f"Geçersiz {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise PolicyViolation(f"{field} saat dilimi içermelidir")
    return parsed


def enforce_temporal_cutoff(
    records: Iterable[Mapping[str, Any]],
    required_fields: Iterable[str],
) -> None:
    """Tahmin girdilerinde gelecek tarihli gözlem kullanımını reddeder."""
    required = tuple(required_fields)
    for index, record in enumerate(records, start=1):
        missing = [field for field in required if record.get(field) in {None, ""}]
        if missing:
            raise PolicyViolation(f"Kayıt {index} zorunlu alanları eksik: {missing}")
        observation = _parse_aware_timestamp(record["observation_timestamp"], "observation_timestamp")
        cutoff = _parse_aware_timestamp(record["data_cutoff_timestamp"], "data_cutoff_timestamp")
        prediction = _parse_aware_timestamp(record["prediction_timestamp"], "prediction_timestamp")
        if observation > cutoff:
            raise PolicyViolation(f"Kayıt {index} veri sızıntısı: gözlem kesim zamanından sonra")
        if cutoff > prediction:
            raise PolicyViolation(f"Kayıt {index} geçersiz zaman sırası: kesim tahminden sonra")


def enforce_model_update_boundary(
    *,
    enabled: bool,
    completed_frozen_predictions: int,
    minimum_frozen_predictions: int,
    old_weights: Mapping[str, float],
    new_weights: Mapping[str, float],
    maximum_relative_change: float,
) -> None:
    """Model güncellemesini kapalı tutar veya açıkken sınırları zorlar."""
    if not enabled:
        raise PolicyViolation("Model güncellemesi politika tarafından kapalı")
    if completed_frozen_predictions < minimum_frozen_predictions:
        raise PolicyViolation("Yeterli tamamlanmış dondurulmuş tahmin yok")
    if set(old_weights) != set(new_weights):
        raise PolicyViolation("Ağırlık anahtarları değiştirilemez")
    for name, old_value in old_weights.items():
        new_value = new_weights[name]
        if old_value == 0:
            if new_value != 0:
                raise PolicyViolation(f"Sıfır ağırlık otomatik değiştirilemez: {name}")
            continue
        relative_change = abs(new_value - old_value) / abs(old_value)
        if relative_change > maximum_relative_change:
            raise PolicyViolation(f"Ağırlık değişimi sınırı aşıldı: {name}")
