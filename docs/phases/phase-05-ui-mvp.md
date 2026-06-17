# Phase 5 — Minimum Viable PyQt6 UI

**Estimated duration:** 2 weeks
**Prerequisite:** Phase 4 complete
**Outcome:** A working three-pane window with a live-updating packet table, Start/Stop/Save/Open toolbar, and a status bar. Smooth scrolling at 1000+ packets per second.

---

## Relevant Knowledge

### Qt's Model/View Architecture — The Core Idea

Qt separates the data (model) from the rendering (view). This is different from naive frameworks where a widget stores its own data internally.

```
  Data lives here              Rendering lives here
+----------------+   data()   +-----------------+
|   QAbstractTable| <---------|   QTableView    |
|     Model       |           |                 |
|                 |---------->|                 |
|                 |  signals  |                 |
+-----------------+           +-----------------+
```

The view asks the model "what's the value for row 5, column 2?" only when it needs to render that cell. When the model changes, it emits `dataChanged`, `rowsInserted`, etc., and the view updates only the affected cells.

This scales. A million-row table is fine because only 30 visible rows are ever requested at one time.

### Why Not `QTableWidget`?

`QTableWidget` is a convenience class that stores data **inside** the view as `QTableWidgetItem` instances. Every cell allocates a heap object. At 10,000+ rows this becomes slow and memory-heavy. At 100,000+ it is unusable.

**Use `QTableView` with a `QAbstractTableModel` subclass. Do not use `QTableWidget`.**

### The Five Required Overrides for `QAbstractTableModel`

When subclassing `QAbstractTableModel`, you must implement:

1. `rowCount(parent=QModelIndex())` — how many rows.
2. `columnCount(parent=QModelIndex())` — how many columns.
3. `data(index, role)` — the value at (row, col) for the given role.
4. `headerData(section, orientation, role)` — column and row headers.
5. (When appending rows) wrap insertions in `beginInsertRows(...)` / `endInsertRows()`.

The most common roles:

- `Qt.ItemDataRole.DisplayRole` — the string shown in the cell.
- `Qt.ItemDataRole.ToolTipRole` — tooltip on hover.
- `Qt.ItemDataRole.BackgroundRole` — cell background color (useful for highlighting flagged packets).
- `Qt.ItemDataRole.TextAlignmentRole` — right-align numbers, left-align text.

### Qt's Event Loop vs React's Render Cycle

| Concept | React | Qt |
|---|---|---|
| State update | `setState` triggers re-render | `pyqtSignal.emit` triggers slot |
| Render | Virtual DOM diff, reconciliation | View polls model for new data |
| Lifecycle | Component mount/unmount/update | QObject parent-child ownership |
| Effects | `useEffect` | `QTimer`, signal connections |
| Memoization | `useMemo`, `React.memo` | Model emits granular signals to avoid full repaint |

The key mental shift: in Qt, the view does not re-render proactively. It re-renders only when the model signals that data has changed. **You** are responsible for emitting the right signal at the right time.

### `QMainWindow` Structure

A `QMainWindow` has predefined regions:

```
+----------------------------------------+
| Menu Bar                               |
+----------------------------------------+
| Toolbar (Start, Stop, Open, Save, ...) |
+----------------------------------------+
| Dock Widget (optional)  | Central      |
|                         | Widget       |
|                         | (your        |
|                         |  splitter)   |
+----------------------------------------+
| Status Bar (capture count, errors)     |
+----------------------------------------+
```

The central widget is where your three-pane layout lives (table on top, detail tree middle, hex dump bottom — via `QSplitter` for resizable panes).

### Code-Driven UI vs Qt Designer

You can design Qt UIs with the `.ui` XML format (Qt Designer) and compile them. **Avoid this for this project.** Code-driven UIs are easier to diff, easier to test, and easier to refactor. Enterprise codebases overwhelmingly prefer code-driven.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Qt for Python — Model/View Tutorial](https://doc.qt.io/qtforpython-6/tutorials/modelviewprogramming.html) | The canonical reference |
| [Qt — Model/View Programming](https://doc.qt.io/qt-6/model-view-programming.html) | Deeper concepts (C++ docs, but apply directly) |
| [PyQt6 — QMainWindow examples](https://www.pythonguis.com/tutorials/pyqt6-creating-your-first-window/) | Practical patterns |
| Mark Summerfield, *Rapid GUI Programming with Python and Qt* | Older (PyQt4) but conceptually still gold |
| [Qt — Signal/Slot connection types](https://doc.qt.io/qt-6/qt.html#ConnectionType-enum) | Auto, Direct, Queued — understand the distinction |
| Wireshark source: `ui/qt/packet_list_model.cpp` | Reference implementation of a packet table model |

---

## Steps for Implementation

### Step 1 — Entry Point

Create `src/eps/main.py`:

```python
"""Application entry point. Composes the layers."""
from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from eps.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Easy Packet Sniffer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

### Step 2 — `PacketTableModel`

Create `src/eps/ui/packet_table.py` using the skeleton from `PROJECT_GUIDE.md` Section 6, Phase 5. Then extend it:

- Add `Qt.ItemDataRole.TextAlignmentRole` handling for the Length column (right-align).
- Add `Qt.ItemDataRole.BackgroundRole` to color TCP RST packets red and SYN packets light blue (useful visual cue).
- Add a `clear()` method that uses `beginResetModel()` / `endResetModel()` to wipe the table when a new capture starts.

### Step 3 — `MainWindow`

Create `src/eps/ui/main_window.py`:

```python
"""The main window. Composes the toolbar, table, detail panes, and status bar."""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QTableView, QSplitter, QToolBar, QLineEdit,
    QWidget, QLabel, QFileDialog, QMessageBox,
)
from eps.controllers.capture_controller import CaptureController
from eps.ui.packet_table import PacketTableModel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Easy Packet Sniffer")
        self.resize(1280, 800)

        self._controller = CaptureController(self)
        self._model = PacketTableModel()

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._wire_signals()

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        self.addToolBar(tb)
        self._act_start = QAction("Start", self)
        self._act_stop = QAction("Stop", self)
        self._act_open = QAction("Open .pcap", self)
        self._act_save = QAction("Save .pcap", self)
        self._bpf_input = QLineEdit()
        self._bpf_input.setPlaceholderText("BPF filter (e.g. tcp port 443)")
        self._bpf_input.setFixedWidth(320)
        tb.addAction(self._act_start)
        tb.addAction(self._act_stop)
        tb.addSeparator()
        tb.addWidget(QLabel("Filter: "))
        tb.addWidget(self._bpf_input)
        tb.addSeparator()
        tb.addAction(self._act_open)
        tb.addAction(self._act_save)

        self._act_stop.setEnabled(False)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical)
        self._table_view = QTableView()
        self._table_view.setModel(self._model)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        splitter.addWidget(self._table_view)
        # Phase 6 adds the detail tree and hex dump below this.
        splitter.addWidget(QWidget())  # placeholder
        splitter.addWidget(QWidget())  # placeholder
        splitter.setSizes([400, 200, 200])
        self.setCentralWidget(splitter)

    def _build_statusbar(self) -> None:
        self._status_count = QLabel("0 packets")
        self.statusBar().addPermanentWidget(self._status_count)

    def _wire_signals(self) -> None:
        self._act_start.triggered.connect(self._on_start)
        self._act_stop.triggered.connect(self._on_stop)
        self._act_open.triggered.connect(self._on_open)
        self._act_save.triggered.connect(self._on_save)

        self._controller.packet_received.connect(self._on_packet)
        self._controller.capture_stopped.connect(self._on_capture_stopped)
        self._controller.error_raised.connect(self._on_error)

    def _on_start(self) -> None:
        self._model.clear()
        self._controller.start(
            iface=None,
            bpf_filter=self._bpf_input.text().strip(),
        )
        self._act_start.setEnabled(False)
        self._act_stop.setEnabled(True)

    def _on_stop(self) -> None:
        self._controller.stop()

    def _on_packet(self, pkt) -> None:
        self._model.append(pkt)
        self._status_count.setText(f"{self._model.rowCount()} packets")

    def _on_capture_stopped(self, stats: dict) -> None:
        self._act_start.setEnabled(True)
        self._act_stop.setEnabled(False)
        self._status_count.setText(
            f"{self._model.rowCount()} packets | drops: {stats.get('drops', 'n/a')}"
        )

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open .pcap", "", "pcap files (*.pcap *.pcapng)"
        )
        if not path:
            return
        # Phase 5 stub: just read and parse all packets into the table
        from eps.core.pcap_io import read_pcap
        from eps.core.parser import parse
        self._model.clear()
        for sp in read_pcap(path):
            self._model.append(parse(sp))
        self._status_count.setText(f"{self._model.rowCount()} packets (file)")

    def _on_save(self) -> None:
        QMessageBox.information(self, "Save", "Save not implemented in Phase 5.")

    def _on_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Capture error", msg)
        self._act_start.setEnabled(True)
        self._act_stop.setEnabled(False)
```

### Step 4 — Run and Verify

```
python -m eps.main
```

(From an Administrator terminal, venv activated.)

Click Start. Packets should populate the table live. Stop. Open a `.pcap` from Phase 2's fixtures. The table should populate from the file.

### Step 5 — Performance Test

Generate heavy traffic (download a large file or run `iperf`). Capture for 30 seconds with no filter. Verify:

- Table scrolling does not stutter.
- Memory usage grows linearly but not pathologically (a few hundred MB at 100k packets is acceptable).
- The status bar count updates without freezing the UI.

If the UI freezes, the most likely cause is too many `dataChanged` signals firing per second. Throttle by batching: collect packets into a list with a `QTimer` flushing once every 100 ms.

### Step 6 — Run `import-linter` Again

```
lint-imports
```

Must still pass. The new UI code in `eps.ui` is free to import PyQt6, but verify `eps.core` and `eps.controllers` are still clean.

---

## Self-Administered Verification Gate

- [ ] `python -m eps.main` opens a window with toolbar, table, and status bar.
- [ ] Start captures packets live; Stop terminates cleanly.
- [ ] Open loads a `.pcap` file and populates the table.
- [ ] At 1000+ packets/second the UI remains responsive (no stutter when scrolling).
- [ ] Status bar shows correct packet count and drop count.
- [ ] `lint-imports` still passes.
- [ ] I can explain why `QAbstractTableModel` scales but `QTableWidget` does not.

Once all boxes are checked, you may begin Phase 6.
