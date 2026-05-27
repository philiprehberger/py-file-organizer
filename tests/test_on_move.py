"""Tests for the Organizer.on_move hook."""

from __future__ import annotations

import tempfile
from pathlib import Path

from philiprehberger_file_organizer import MoveAction, Organizer, Rule


def _make_workspace(tmp: Path) -> tuple[Path, Path]:
    src = tmp / "src"
    dest = tmp / "dest"
    src.mkdir()
    dest.mkdir()
    return src, dest


def test_on_move_fires_for_each_moved_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, dest = _make_workspace(Path(tmp))
        (src / "a.txt").write_text("a")
        (src / "b.txt").write_text("b")

        organizer = Organizer(rules=[Rule(extensions=[".txt"], destination=str(dest))])

        captured: list[tuple[MoveAction, Rule]] = []
        organizer.on_move(lambda a, r: captured.append((a, r)))

        report = organizer.organize(src)
        assert report.total_moved == 2
        assert len(captured) == 2
        names = sorted(a.source.name for a, _ in captured)
        assert names == ["a.txt", "b.txt"]


def test_on_move_receives_matched_rule() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, dest = _make_workspace(Path(tmp))
        (src / "foo.txt").write_text("x")

        txt_rule = Rule(extensions=[".txt"], destination=str(dest))
        organizer = Organizer(rules=[txt_rule])

        seen_rules: list[Rule] = []
        organizer.on_move(lambda a, r: seen_rules.append(r))

        organizer.organize(src)
        assert seen_rules == [txt_rule]


def test_on_move_not_called_during_preview() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, dest = _make_workspace(Path(tmp))
        (src / "a.txt").write_text("a")

        organizer = Organizer(rules=[Rule(extensions=[".txt"], destination=str(dest))])
        calls: list[MoveAction] = []
        organizer.on_move(lambda a, r: calls.append(a))

        organizer.preview(src)
        assert calls == []


def test_on_move_decorator_usage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, dest = _make_workspace(Path(tmp))
        (src / "a.txt").write_text("a")

        organizer = Organizer(rules=[Rule(extensions=[".txt"], destination=str(dest))])
        triggered: list[str] = []

        @organizer.on_move
        def _hook(action: MoveAction, rule: Rule) -> None:
            triggered.append(action.source.name)

        organizer.organize(src)
        assert triggered == ["a.txt"]


def test_hook_exception_recorded_but_does_not_stop_moves() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src, dest = _make_workspace(Path(tmp))
        (src / "a.txt").write_text("a")
        (src / "b.txt").write_text("b")

        organizer = Organizer(rules=[Rule(extensions=[".txt"], destination=str(dest))])
        organizer.on_move(lambda a, r: (_ for _ in ()).throw(RuntimeError("boom")))

        report = organizer.organize(src)
        assert report.total_moved == 2
        assert len(report.errors) == 2
        assert all("on_move hook" in msg for _, msg in report.errors)
