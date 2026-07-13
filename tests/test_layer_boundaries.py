# tests/test_layer_boundaries.py
"""Guards the layering itself.

Decoupling is easy to achieve once and easy to lose silently: one convenient import re-couples two
layers and nothing fails. This test reads every module's imports and checks them against the
dependency edges the architecture allows, so a leak breaks the build instead of rotting quietly.

The rules that matter, in the language of the design:
  - `realtime/` must not import `rules/`. What an arrival *means* is a rules decision; the arbiter
    only owns time. This is the edge that used to exist and must never come back.
  - `engine/`, `input/`, `text_io/` name no other layer either — they get their collaborators
    injected.
  - `model/` depends on nobody: it is the core.
  - only `composition/` (and main.py) may see across layers, because wiring is its entire job.
  - only `composition/` and main.py may read `config`; every other layer takes values injected.
"""
import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The layers, and the project modules each is allowed to import. A layer may always import itself.
ALLOWED_IMPORTS = {
    "model": {"model"},
    "rules": {"model", "rules"},
    "realtime": {"model", "realtime"},
    "engine": {"model", "engine"},
    "input": {"model", "input"},
    "text_io": {"model", "text_io"},
    "texttests": {"texttests"},
    # The composition root exists precisely to know everyone.
    "composition": {"composition", "config", "engine", "input", "model", "realtime", "rules",
                    "text_io", "texttests"},
}
MAIN_ALLOWED = {"composition", "config", "text_io", "texttests"}

PROJECT_MODULES = set(ALLOWED_IMPORTS) | {"config", "main"}


def imported_project_modules(path):
    """The project (non-stdlib) top-level modules a source file imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    return imported & PROJECT_MODULES


def source_files(layer):
    return sorted(p for p in (ROOT / layer).glob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("layer", sorted(ALLOWED_IMPORTS))
def test_layer_only_imports_what_it_is_allowed_to(layer):
    allowed = ALLOWED_IMPORTS[layer]
    for path in source_files(layer):
        forbidden = imported_project_modules(path) - allowed
        assert not forbidden, (
            f"{path.relative_to(ROOT)} imports {sorted(forbidden)}, which {layer}/ may not depend "
            f"on. Depend on an abstraction and have composition/app_factory inject it."
        )


def identifiers(path):
    """Every name the code actually uses — prose in docstrings and comments does not count."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


# Chess vocabulary the time model is not allowed to speak.
CHESS_VOCABULARY = {"KING", "QUEEN", "ROOK", "BISHOP", "KNIGHT", "PAWN",
                    "PieceKind", "promotion_kind", "king_captured"}


def test_realtime_does_not_know_what_a_king_is():
    """The headline invariant: the time model holds no chess.

    It may not import the rules, and its code may not name a piece kind, a promotion or a king —
    those are outcomes, and it only owns timing. It states the situation to the injected rule set
    and applies the effects it gets back.
    """
    for path in source_files("realtime"):
        assert "rules" not in imported_project_modules(path), (
            f"{path.name} imports rules/: changing the game's rules would force an edit here."
        )
        spoken = identifiers(path) & CHESS_VOCABULARY
        assert not spoken, (
            f"{path.name} names {sorted(spoken)} in its code: that is a rules decision, not a "
            f"timing one. Ask the injected rule set instead."
        )


def test_only_the_composition_root_reads_config():
    """Every other layer is handed its values. config is not ambient state to reach into."""
    for layer in ALLOWED_IMPORTS:
        if layer == "composition":
            continue
        for path in source_files(layer):
            assert "config" not in imported_project_modules(path), (
                f"{path.relative_to(ROOT)} imports config directly. Inject the value instead."
            )


def test_main_only_talks_to_the_composition_root():
    forbidden = imported_project_modules(ROOT / "main.py") - MAIN_ALLOWED
    assert not forbidden, f"main.py imports {sorted(forbidden)}; it should wire via composition/."
