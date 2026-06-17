# Phase 9 — Production Hygiene

**Estimated duration:** 3–5 days
**Prerequisite:** Phase 8 complete
**Outcome:** Structured logging with rotation, TOML-based configuration, graceful error handling throughout the app, and a working PyInstaller build producing a single Windows executable.

---

## Relevant Knowledge

### Why Logging Matters

In a hobby project, `print()` is fine. In an enterprise codebase or any tool a stranger will run:

- You need to know what happened when a user reports a bug.
- You cannot ask the user to reproduce in front of you.
- Stdout may be redirected, swallowed, or unavailable (e.g., in a GUI app launched from a shortcut).

A proper logger writes timestamped, leveled messages to a rotating file. The user (or you, debugging their issue) can read the log post-mortem.

### Python's `logging` Module — The Right Way

The standard `logging` module is configured once at startup. From then on, modules just call `logger.info(...)`, `logger.error(...)`, etc., and the global configuration decides where to send the output.

Best practices:

1. Each module declares `logger = logging.getLogger(__name__)` at the top. The dunder name produces hierarchical logger names like `eps.core.capture_engine`.
2. Configuration happens **once**, in `main.py`, before any other code runs.
3. Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Default to `INFO` in production, `DEBUG` while developing.
4. Use `RotatingFileHandler` to bound disk usage. Without rotation, a long-running process can fill the disk.
5. Format your records with a clear template: timestamp, level, logger name, message.

### Configuration: `tomllib`

Python 3.11+ includes `tomllib` in the standard library — TOML parsing without an external dependency. Keep your config in `config.toml` at the project root or in a user data directory.

Useful settings:

```toml
[capture]
default_interface = ""           # empty = let Scapy pick
snaplen = 65535
promiscuous = true

[ui]
table_max_rows = 100000          # cap to avoid runaway memory

[logging]
level = "INFO"
file = "logs/eps.log"
max_size_mb = 10
backup_count = 5
```

Read it once in `main.py` and pass relevant sections into the components that need them.

### Graceful Error Handling

Three classes of errors to handle distinctly:

1. **User errors** (bad filter, invalid file path). Show a clear message in the UI. Do not log as ERROR; INFO or WARNING is appropriate.
2. **Recoverable system errors** (interface disappeared, pcap save failed). Log at ERROR. Show a dialog. Continue running.
3. **Unrecoverable errors** (corrupted state, programming bugs). Log at CRITICAL with a full traceback. Show a dialog explaining the app must close. Then exit gracefully.

A top-level `sys.excepthook` catches anything that escapes a slot. Without it, exceptions in Qt slots are sometimes swallowed silently — a notorious source of "the app froze and I don't know why."

### PyInstaller for Windows Packaging

PyInstaller bundles a Python interpreter and your code into a single executable. For Scapy-based apps it requires special handling because Scapy uses runtime imports that PyInstaller's static analysis misses.

The standard solution: a `.spec` file with explicit `hiddenimports=['scapy.layers.l2', 'scapy.layers.inet', ...]`.

The output is roughly 50–80 MB (Python runtime + Scapy + PyQt6 are large). That is normal. It is a portfolio artifact, not a Slim app.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Python — Logging HOWTO](https://docs.python.org/3/howto/logging.html) | Beginner-level introduction |
| [Python — Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html) | Recipes for common patterns |
| [Python — tomllib](https://docs.python.org/3/library/tomllib.html) | TOML parsing |
| [PyInstaller documentation](https://pyinstaller.org/en/stable/) | Bundling |
| [PyInstaller + Scapy notes (community)](https://github.com/secdev/scapy/issues?q=pyinstaller) | Known issues |
| [The Twelve-Factor App — Logs](https://12factor.net/logs) | Conceptual framing |

---

## Steps for Implementation

### Step 1 — Configure Logging

Create `src/eps/logging_config.py`:

```python
"""Centralized logging configuration."""
from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path


def configure_logging(
    *,
    level: str = "INFO",
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
        )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        handlers=handlers,
    )
```

Then in every module that does interesting work, replace `print` with:

```python
import logging
logger = logging.getLogger(__name__)
# logger.info("Capture started on interface %s", iface)
```

### Step 2 — Config File

Create `config.toml` at the project root with the sample contents shown above.

Create `src/eps/config.py`:

```python
"""Read config.toml and expose typed access."""
from __future__ import annotations
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaptureConfig:
    default_interface: str
    snaplen: int
    promiscuous: bool


@dataclass(frozen=True)
class UIConfig:
    table_max_rows: int


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    file: str
    max_size_mb: int
    backup_count: int


@dataclass(frozen=True)
class Config:
    capture: CaptureConfig
    ui: UIConfig
    logging: LoggingConfig


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Config(
        capture=CaptureConfig(**raw["capture"]),
        ui=UIConfig(**raw["ui"]),
        logging=LoggingConfig(**raw["logging"]),
    )
```

### Step 3 — Wire Config into `main.py`

```python
from __future__ import annotations
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from eps.config import load_config
from eps.logging_config import configure_logging
from eps.ui.main_window import MainWindow


def main() -> int:
    cfg = load_config(Path("config.toml"))
    configure_logging(
        level=cfg.logging.level,
        log_file=Path(cfg.logging.file),
        max_bytes=cfg.logging.max_size_mb * 1024 * 1024,
        backup_count=cfg.logging.backup_count,
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Easy Packet Sniffer")
    window = MainWindow(cfg)   # MainWindow now accepts the config
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

Update `MainWindow.__init__` to accept and store the config.

### Step 4 — Global Exception Handler

In `main()`, before creating `QApplication`:

```python
import traceback

def excepthook(exc_type, exc, tb) -> None:
    logging.getLogger("eps").critical(
        "Unhandled exception:\n%s",
        "".join(traceback.format_exception(exc_type, exc, tb)),
    )
    sys.__excepthook__(exc_type, exc, tb)

sys.excepthook = excepthook
```

This guarantees every escaping exception lands in your log file.

### Step 5 — PyInstaller Build

Create `eps.spec` at the project root:

```python
# eps.spec — generated for PyInstaller
# Build with: pyinstaller eps.spec --clean
block_cipher = None

a = Analysis(
    ['src/eps/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('config.toml', '.')],
    hiddenimports=[
        # Scapy registers layers dynamically; PyInstaller needs hints
        'scapy.layers.l2',
        'scapy.layers.inet',
        'scapy.layers.inet6',
        'scapy.layers.dns',
        'scapy.arch.windows',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='easy-packet-sniffer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app, no console window
    icon=None,
)
```

Install PyInstaller and build:

```
pip install pyinstaller
pyinstaller eps.spec --clean
```

The resulting executable lives in `dist/easy-packet-sniffer.exe`. Test by running it from an Administrator command prompt.

### Step 6 — Verify the Build

- The exe launches without a Python install on the test machine (try copying it to a fresh user account).
- Live capture works.
- pcap files open and save.
- Statistics dialog works.

If any of these fail in the built executable but work from source, the most common cause is a missing `hiddenimports` entry. Re-check Scapy import errors in the log.

---

## Self-Administered Verification Gate

- [ ] `config.toml` exists and is loaded at startup.
- [ ] `logs/eps.log` is created on first run and rotates after 10 MB.
- [ ] At least 5 modules emit structured log lines (capture engine, controller, parser, pcap_io, main).
- [ ] An unhandled exception in any slot is logged at CRITICAL and the user sees a dialog.
- [ ] `pyinstaller eps.spec --clean` produces a working `.exe`.
- [ ] The exe runs on a machine without Python installed.
- [ ] `lint-imports` still passes.

Once all boxes are checked, you may begin Phase 10.
