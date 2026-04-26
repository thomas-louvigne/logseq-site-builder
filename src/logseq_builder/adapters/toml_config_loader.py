import tomllib
from pathlib import Path

from .edn_config_loader import load_edn_config

CONFIG_FILENAME = "logseq-site-builder.toml"


def load_toml_config(logseq_dir: Path) -> dict:
    """Load config from config.edn (base) then logseq-site-builder.toml (overrides).

    TOML values always win over EDN-derived values.
    """
    merged = load_edn_config(logseq_dir)

    toml_path = logseq_dir / CONFIG_FILENAME
    if not toml_path.exists():
        return merged

    with toml_path.open("rb") as f:
        toml = tomllib.load(f)

    for key, value in toml.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    return merged
