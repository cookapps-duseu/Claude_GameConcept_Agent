import yaml


def load_output_format(config_path: str = "config.yaml") -> str:
    """config.yaml에서 output.format을 읽는다. 파일 없으면 'word' 반환."""
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("output", {}).get("format", "word")
    except FileNotFoundError:
        return "word"


def load_model(config_path: str = "config.yaml") -> str | None:
    """config.yaml에서 model을 읽는다. 없으면 None 반환."""
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("model") or None
    except FileNotFoundError:
        return None


def load_models(config_path: str = "config.yaml") -> dict:
    """역할별 모델을 dict로 반환. 키: generator, validator, writer, image.
    누락된 키는 None으로 채운다."""
    defaults = {
        "generator": None,
        "validator": None,
        "writer": None,
        "image": None,
    }
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        models = cfg.get("models", {}) or {}
        return {**defaults, **models}
    except FileNotFoundError:
        return defaults
