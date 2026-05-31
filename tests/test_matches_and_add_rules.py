"""Tests for Rule.matches and Organizer.add_rules."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from philiprehberger_file_organizer import Organizer, Rule


def test_matches_pattern_on_nonexistent_path() -> None:
    rule = Rule(destination="/tmp", pattern="*.txt")
    assert rule.matches("foo.txt") is True
    assert rule.matches("foo.md") is False


def test_matches_extensions_on_nonexistent_path() -> None:
    rule = Rule(destination="/tmp", extensions=[".pdf", ".docx"])
    assert rule.matches("report.pdf") is True
    assert rule.matches("Report.PDF") is True  # case-insensitive
    assert rule.matches("photo.jpg") is False


def test_matches_name_contains_on_nonexistent_path() -> None:
    rule = Rule(destination="/tmp", name_contains="invoice")
    assert rule.matches("2026-invoice-001.pdf") is True
    assert rule.matches("receipt.pdf") is False


def test_matches_accepts_path_object() -> None:
    rule = Rule(destination="/tmp", pattern="*.txt")
    assert rule.matches(Path("foo.txt")) is True
    assert rule.matches(Path("foo.md")) is False


def test_matches_size_filter_agrees_with_organizer() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        dest = Path(tmp) / "dest"
        src.mkdir()
        dest.mkdir()
        big = src / "big.bin"
        small = src / "small.bin"
        big.write_bytes(b"x" * 2048)
        small.write_bytes(b"x" * 10)

        rule = Rule(destination=str(dest), larger_than=1024)

        # matches() answers directly
        assert rule.matches(big) is True
        assert rule.matches(small) is False

        # organizer.preview() should agree
        organizer = Organizer(rules=[rule])
        report = organizer.preview(src)
        moved_sources = {a.source.name for a in report.actions}
        assert moved_sources == {"big.bin"}


def test_matches_newer_than_days_agrees_with_organizer() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        dest = Path(tmp) / "dest"
        src.mkdir()
        dest.mkdir()
        recent = src / "recent.log"
        old = src / "old.log"
        recent.write_text("r")
        old.write_text("o")
        # Set old file's mtime to 30 days ago
        thirty_days = 30 * 86400
        now = time.time()
        import os
        os.utime(old, (now - thirty_days, now - thirty_days))

        rule = Rule(destination=str(dest), newer_than_days=1)

        assert rule.matches(recent) is True
        assert rule.matches(old) is False

        organizer = Organizer(rules=[rule])
        report = organizer.preview(src)
        moved_sources = {a.source.name for a in report.actions}
        assert moved_sources == {"recent.log"}


def test_add_rules_appends_in_order() -> None:
    r1 = Rule(destination="/a", pattern="*.a")
    r2 = Rule(destination="/b", pattern="*.b")
    r3 = Rule(destination="/c", pattern="*.c")

    organizer = Organizer(rules=[])
    result = organizer.add_rules([r1, r2, r3])

    assert organizer.rules == [r1, r2, r3]
    assert result is organizer


def test_add_rules_extends_existing_rules() -> None:
    initial = Rule(destination="/init", pattern="*.init")
    organizer = Organizer(rules=[initial])

    r1 = Rule(destination="/a", pattern="*.a")
    r2 = Rule(destination="/b", pattern="*.b")
    returned = organizer.add_rules([r1, r2])

    assert organizer.rules == [initial, r1, r2]
    assert returned is organizer


def test_add_rules_supports_chaining() -> None:
    organizer = Organizer(rules=[])
    r1 = Rule(destination="/a", pattern="*.a")
    r2 = Rule(destination="/b", pattern="*.b")

    chained = organizer.add_rules([r1]).add_rules([r2])

    assert chained is organizer
    assert organizer.rules == [r1, r2]
