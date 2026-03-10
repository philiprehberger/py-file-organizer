"""Rule-based file sorting engine with pattern matching and dry run support."""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Literal

__all__ = ["Rule", "Organizer", "MoveAction", "OrganizeReport"]


@dataclass
class Rule:
    """A rule that matches files and specifies where to move them."""

    destination: str
    extensions: list[str] | None = None
    pattern: str | None = None
    larger_than: int | None = None
    smaller_than: int | None = None
    older_than_days: int | None = None
    newer_than_days: int | None = None
    name_contains: str | None = None
    predicate: Callable[[Path], bool] | None = None

    def matches(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if self.extensions and path.suffix.lower() not in [e.lower() for e in self.extensions]:
            return False
        if self.pattern and not fnmatch.fnmatch(path.name, self.pattern):
            return False
        if self.name_contains and self.name_contains.lower() not in path.name.lower():
            return False
        try:
            stat = path.stat()
        except OSError:
            return False
        if self.larger_than is not None and stat.st_size < self.larger_than:
            return False
        if self.smaller_than is not None and stat.st_size > self.smaller_than:
            return False
        now = datetime.now().timestamp()
        if self.older_than_days is not None:
            threshold = now - (self.older_than_days * 86400)
            if stat.st_mtime > threshold:
                return False
        if self.newer_than_days is not None:
            threshold = now - (self.newer_than_days * 86400)
            if stat.st_mtime < threshold:
                return False
        if self.predicate and not self.predicate(path):
            return False
        return True


@dataclass
class MoveAction:
    """Describes a planned or executed file move."""

    source: Path
    destination: Path
    size: int
    rule_index: int


@dataclass
class OrganizeReport:
    """Result of an organize operation."""

    actions: list[MoveAction] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total_moved(self) -> int:
        return len(self.actions)

    @property
    def total_size(self) -> int:
        return sum(a.size for a in self.actions)


ConflictStrategy = Literal["skip", "rename", "overwrite"]


def _resolve_conflict(dest: Path, strategy: ConflictStrategy) -> Path | None:
    if not dest.exists():
        return dest
    if strategy == "skip":
        return None
    if strategy == "overwrite":
        return dest
    # rename: add (1), (2), etc.
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1
    while True:
        new_dest = parent / f"{stem} ({counter}){suffix}"
        if not new_dest.exists():
            return new_dest
        counter += 1


class Organizer:
    """Rule-based file organizer."""

    def __init__(
        self,
        rules: list[Rule],
        conflict: ConflictStrategy = "rename",
        recursive: bool = False,
    ):
        self.rules = rules
        self.conflict = conflict
        self.recursive = recursive

    def _iter_files(self, directory: str | Path) -> list[Path]:
        root = Path(directory).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")
        if self.recursive:
            return [p for p in root.rglob("*") if p.is_file()]
        return [p for p in root.iterdir() if p.is_file()]

    def preview(self, directory: str | Path) -> OrganizeReport:
        """Dry run — returns what would happen without moving anything."""
        report = OrganizeReport()
        files = self._iter_files(directory)

        for file_path in files:
            matched = False
            for i, rule in enumerate(self.rules):
                if rule.matches(file_path):
                    dest_dir = Path(rule.destination).expanduser().resolve()
                    dest = dest_dir / file_path.name
                    resolved = _resolve_conflict(dest, self.conflict)
                    if resolved is None:
                        report.skipped.append((file_path, "conflict: skip"))
                    else:
                        try:
                            size = file_path.stat().st_size
                        except OSError:
                            size = 0
                        report.actions.append(MoveAction(
                            source=file_path,
                            destination=resolved,
                            size=size,
                            rule_index=i,
                        ))
                    matched = True
                    break
            if not matched:
                report.skipped.append((file_path, "no matching rule"))

        return report

    def organize(self, directory: str | Path) -> OrganizeReport:
        """Move files according to rules. Returns a report of actions taken."""
        report = OrganizeReport()
        files = self._iter_files(directory)
        move_log: list[dict] = []

        for file_path in files:
            matched = False
            for i, rule in enumerate(self.rules):
                if rule.matches(file_path):
                    dest_dir = Path(rule.destination).expanduser().resolve()
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / file_path.name
                    resolved = _resolve_conflict(dest, self.conflict)

                    if resolved is None:
                        report.skipped.append((file_path, "conflict: skip"))
                        matched = True
                        break

                    try:
                        size = file_path.stat().st_size
                        shutil.move(str(file_path), str(resolved))
                        action = MoveAction(
                            source=file_path,
                            destination=resolved,
                            size=size,
                            rule_index=i,
                        )
                        report.actions.append(action)
                        move_log.append({
                            "source": str(file_path),
                            "destination": str(resolved),
                        })
                    except OSError as e:
                        report.errors.append((file_path, str(e)))
                    matched = True
                    break
            if not matched:
                report.skipped.append((file_path, "no matching rule"))

        # Write undo log
        if move_log:
            log_dir = Path(directory).expanduser().resolve()
            log_path = log_dir / ".organize_log.json"
            try:
                existing = json.loads(log_path.read_text()) if log_path.exists() else []
                existing.extend(move_log)
                log_path.write_text(json.dumps(existing, indent=2))
            except OSError:
                pass

        return report

    @staticmethod
    def undo(directory: str | Path) -> int:
        """Undo the last organize operation using the move log."""
        log_path = Path(directory).expanduser().resolve() / ".organize_log.json"
        if not log_path.exists():
            return 0

        entries = json.loads(log_path.read_text())
        restored = 0
        for entry in reversed(entries):
            src = Path(entry["destination"])
            dst = Path(entry["source"])
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                restored += 1

        log_path.unlink(missing_ok=True)
        return restored


def parse_size(size_str: str) -> int:
    """Parse a human-readable size string like '100MB' into bytes."""
    size_str = size_str.strip().upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, multiplier in sorted(units.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            return int(float(size_str[:-len(suffix)].strip()) * multiplier)
    return int(size_str)
