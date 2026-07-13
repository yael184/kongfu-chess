# tests/test_config.py
# Tests for the config access layer that loads values from an external TOML file.
import config


def test_load_returns_the_values_from_the_repo_config():
    cfg = config.load()
    assert cfg.cell_size == 100
    assert cfg.ms_per_cell == 1000
    assert cfg.jump_duration_ms == 1000
    assert cfg.empty_token == "."


def test_load_reads_from_a_given_file(tmp_path):
    custom = tmp_path / "custom.toml"
    custom.write_text(
        "[board]\n"
        "cell_size = 50\n"
        "[timing]\n"
        "ms_per_cell = 250\n"
        "jump_duration_ms = 750\n"
        "[tokens]\n"
        'empty = "_"\n'
    )
    cfg = config.load(custom)
    assert cfg.cell_size == 50
    assert cfg.ms_per_cell == 250
    assert cfg.jump_duration_ms == 750
    assert cfg.empty_token == "_"


def test_a_custom_config_does_not_disturb_the_default_one(tmp_path):
    # A config is a value, not module-global state: loading one leaves every other one alone,
    # so a test (or a second game in the same process) can use its own settings safely.
    custom = tmp_path / "custom.toml"
    custom.write_text(
        "[board]\ncell_size = 50\n"
        "[timing]\nms_per_cell = 250\njump_duration_ms = 750\n"
        '[tokens]\nempty = "_"\n'
    )
    config.load(custom)
    assert config.load().cell_size == 100


def test_config_is_immutable():
    cfg = config.load()
    try:
        cfg.cell_size = 999
    except Exception:
        return
    raise AssertionError("GameConfig must be frozen")
