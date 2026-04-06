import pytest
import yaml
from pathlib import Path
from config import load_output_format
from config import load_models


def test_config_yaml_exists():
    assert Path("config.yaml").exists()


def test_config_yaml_has_output_format():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert "output" in cfg
    assert cfg["output"]["format"] in ("word", "html", "both")


def test_config_default_format_is_html():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["output"]["format"] == "html"


def test_load_output_format_default_when_missing(tmp_path):
    fmt = load_output_format(str(tmp_path / "nonexistent.yaml"))
    assert fmt == "word"


def test_load_output_format_reads_value(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("output:\n  format: both\n", encoding="utf-8")
    fmt = load_output_format(str(cfg_file))
    assert fmt == "both"


def test_load_models_returns_all_keys(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "models:\n"
        "  generator: claude-sonnet-4-6\n"
        "  validator: claude-haiku-4-5-20251001\n"
        "  writer: claude-opus-4-6\n"
        "  image: claude-sonnet-4-6\n",
        encoding="utf-8",
    )
    models = load_models(str(cfg_file))
    assert models["generator"] == "claude-sonnet-4-6"
    assert models["validator"] == "claude-haiku-4-5-20251001"
    assert models["writer"] == "claude-opus-4-6"
    assert models["image"] == "claude-sonnet-4-6"


def test_load_models_missing_file_returns_none_defaults(tmp_path):
    models = load_models(str(tmp_path / "nonexistent.yaml"))
    assert models == {"generator": None, "validator": None, "writer": None, "image": None}


def test_load_models_partial_config_fills_missing_with_none(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("models:\n  writer: claude-opus-4-6\n", encoding="utf-8")
    models = load_models(str(cfg_file))
    assert models["writer"] == "claude-opus-4-6"
    assert models["generator"] is None
    assert models["validator"] is None
    assert models["image"] is None


def test_load_models_no_models_section_returns_none_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("output:\n  format: word\n", encoding="utf-8")
    models = load_models(str(cfg_file))
    assert models == {"generator": None, "validator": None, "writer": None, "image": None}
