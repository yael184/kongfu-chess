# tests/test_config.py
# Tests for the config access layer that loads values from an external TOML file.
import config


def test_config_exposes_expected_constants():
    # The values default to those in the repo's config.toml.
    assert config.CELL_SIZE == 100
    assert config.MS_PER_CELL == 1000
    assert config.JUMP_DURATION_MS == 1000
    assert config.EMPTY_TOKEN == "."


def test_load_reads_from_a_given_file(tmp_path):
    # Point load() at a custom TOML file; the module constants update in place.
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
    try:
        config.load(custom)
        assert config.CELL_SIZE == 50
        assert config.MS_PER_CELL == 250
        assert config.JUMP_DURATION_MS == 750
        assert config.EMPTY_TOKEN == "_"
    finally:
        # Restore the default values so other tests are unaffected (module is process-global).
        config.load()


def test_reload_restores_defaults():
    config.load()
    assert config.CELL_SIZE == 100
    assert config.MS_PER_CELL == 1000
