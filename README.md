# philiprehberger-file-organizer

Rule-based file sorting engine with pattern matching and dry run support.

## Install

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

## Conflict Resolution

```python
organizer = Organizer(rules=rules, conflict="rename")   # default: adds (1), (2)...
organizer = Organizer(rules=rules, conflict="skip")      # skip existing
organizer = Organizer(rules=rules, conflict="overwrite")  # overwrite existing
```

## License

MIT
