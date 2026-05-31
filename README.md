# philiprehberger-file-organizer

[![Tests](https://github.com/philiprehberger/py-file-organizer/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-file-organizer/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-file-organizer.svg)](https://pypi.org/project/philiprehberger-file-organizer/)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-file-organizer)](https://github.com/philiprehberger/py-file-organizer/commits/main)

![philiprehberger-file-organizer](https://raw.githubusercontent.com/philiprehberger/py-file-organizer/main/package-card.webp)

Rule-based file sorting engine with pattern matching and dry run support.

## Installation

```bash
pip install philiprehberger-file-organizer
```

## Usage

```python
from philiprehberger_file_organizer import Organizer, Rule

organizer = Organizer(
    rules=[
        Rule(extensions=[".pdf", ".doc", ".docx"], destination="~/Documents"),
        Rule(extensions=[".jpg", ".png", ".gif"], destination="~/Pictures"),
        Rule(extensions=[".mp4", ".mkv"], destination="~/Videos"),
        Rule(pattern="invoice_*", destination="~/Documents/Invoices"),
    ]
)

# Preview what would happen (dry run)
report = organizer.preview("~/Downloads")
for action in report.actions:
    print(f"{action.source} -> {action.destination}")

# Execute
report = organizer.organize("~/Downloads")
print(f"Moved {report.total_moved} files ({report.total_size} bytes)")

# Undo
restored = Organizer.undo("~/Downloads")
```

### Testing rules and bulk-adding

Use `Rule.matches(path)` to evaluate a rule against any path in isolation — handy for unit tests, REPL exploration, or debugging why a file is (or isn't) matched. Name-based checks (`extensions`, `pattern`, `name_contains`) work on any path string without touching disk; size and age filters require the file to exist.

```python
rule = Rule(pattern="invoice_*.pdf", destination="~/Documents/Invoices")

rule.matches("invoice_2026.pdf")   # True
rule.matches("photo.jpg")          # False
```

Use `Organizer.add_rules([...])` to append rules in bulk. Returns the organizer so calls can be chained.

```python
organizer = Organizer(rules=[])
organizer.add_rules([
    Rule(extensions=[".pdf"], destination="~/Documents"),
    Rule(extensions=[".jpg", ".png"], destination="~/Pictures"),
]).add_rules([
    Rule(pattern="invoice_*", destination="~/Documents/Invoices"),
])
```

## Rule Options

| Option | Description |
|--------|-------------|
| `extensions` | Match by file extension |
| `pattern` | Match by glob pattern |
| `name_contains` | Match if filename contains string |
| `larger_than` | Minimum file size in bytes |
| `smaller_than` | Maximum file size in bytes |
| `older_than_days` | Match files older than N days |
| `newer_than_days` | Match files newer than N days |
| `predicate` | Custom matching function |

## Move Hooks

Register callbacks that fire after each successful move. Useful for logging, checksums, notifications, or kicking off downstream pipelines without subclassing.

```python
organizer = Organizer(rules=rules)

@organizer.on_move
def log_move(action, rule):
    print(f"moved {action.source.name} -> {action.destination} (rule #{action.rule_index})")
```

Hooks fire only on `organize()` (not `preview()`), and only after the file has actually moved. Hook exceptions are captured in `report.errors`.

## Conflict Resolution

```python
organizer = Organizer(rules=rules, conflict="rename")   # default: adds (1), (2)...
organizer = Organizer(rules=rules, conflict="skip")      # skip existing
organizer = Organizer(rules=rules, conflict="overwrite")  # overwrite existing
```

## API

| Function / Class | Description |
|------------------|-------------|
| `Organizer(rules, conflict, recursive)` | Rule-based file organizer with `preview()`, `organize()`, and `undo()` methods |
| `Organizer.on_move(hook)` | Register a `(action, rule) -> None` callback fired after each successful move |
| `Organizer.add_rules(rules)` | Append multiple rules at once; returns the organizer for chaining |
| `Rule(destination, extensions, pattern, ...)` | A rule that matches files by extension, pattern, size, or age |
| `Rule.matches(path)` | Return `True` if the rule matches the given path — useful for testing rules in isolation |
| `MoveAction` | Describes a planned or executed file move (source, destination, size) |
| `OrganizeReport` | Result of an organize operation with `actions`, `skipped`, `errors`, `total_moved`, `total_size` |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this project useful:

⭐ [Star the repo](https://github.com/philiprehberger/py-file-organizer)

🐛 [Report issues](https://github.com/philiprehberger/py-file-organizer/issues?q=is%3Aissue+is%3Aopen+label%3Abug)

💡 [Suggest features](https://github.com/philiprehberger/py-file-organizer/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

❤️ [Sponsor development](https://github.com/sponsors/philiprehberger)

🌐 [All Open Source Projects](https://philiprehberger.com/open-source-packages)

💻 [GitHub Profile](https://github.com/philiprehberger)

🔗 [LinkedIn Profile](https://www.linkedin.com/in/philiprehberger)

## License

[MIT](LICENSE)
