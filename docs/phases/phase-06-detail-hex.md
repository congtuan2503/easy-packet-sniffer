# Phase 6 — Packet Detail Tree and Hex Dump

**Estimated duration:** 1 week
**Prerequisite:** Phase 5 complete
**Outcome:** The middle and bottom panes of the main window are populated. Selecting a row in the packet table shows the hierarchical protocol breakdown in a `QTreeView` and the raw bytes in a hex+ASCII dump.

---

## Relevant Knowledge

### Why a Tree View?

A packet is naturally hierarchical: Ethernet contains IP contains TCP contains payload. Wireshark's middle pane is a tree because that hierarchy is the most natural way to browse a packet's fields.

```
> Ethernet II, Src: 00:11:22:33:44:55, Dst: aa:bb:cc:dd:ee:ff
    Destination: aa:bb:cc:dd:ee:ff
    Source: 00:11:22:33:44:55
    Type: IPv4 (0x0800)
> Internet Protocol Version 4, Src: 10.0.0.5, Dst: 142.250.80.46
    Version: 4
    Header Length: 20 bytes
    Time to Live: 64
    Protocol: TCP (6)
    ...
> Transmission Control Protocol, Src Port: 51234, Dst Port: 443
    Source Port: 51234
    Destination Port: 443
    Flags: 0x018 (PSH, ACK)
    ...
```

Each top-level node represents a protocol layer. Each child represents a field of that layer.

### `QStandardItemModel` vs Custom `QAbstractItemModel`

For hierarchical data, Qt provides two options:

| Model | Use when |
|---|---|
| `QStandardItemModel` | Simple. Each row is a `QStandardItem`. You build the tree imperatively. |
| Custom `QAbstractItemModel` | Hierarchical data backed by your own structure (e.g., a custom tree). Required for very large hierarchies. |

For a packet detail view, the hierarchy is small (a dozen items per packet) and ephemeral (rebuilt on every selection change). `QStandardItemModel` is the right choice. Save the custom-model exercise for a future project.

### Hex Dump Format — The Wireshark Convention

```
0000   ff ff ff ff ff ff 00 11 22 33 44 55 08 00 45 00   ........"3DU..E.
0010   00 3c 1c 46 40 00 40 06 b1 e6 c0 a8 00 64 0a 00   .<.F@.@......d..
0020   00 01 00 50 00 50 04 d2 16 2e 00 00 00 00 50 02   ...P.P........P.
0030   72 10 91 7c 00 00                                 r..|..
```

Format details:

- **Offset** (4 hex digits) on the left.
- **Hex bytes** in the middle, 16 per row, separated by spaces. Sometimes split into two groups of 8 for readability.
- **ASCII representation** on the right. Bytes 0x20–0x7E render as themselves; all others render as `.`.

The hex view is essential for verifying parser correctness and for understanding malformed or non-standard packets.

### Selection Model

`QTableView`'s selection model emits `selectionChanged(selected, deselected)` when the user clicks a row. You connect this to a slot that:

1. Reads the selected row index.
2. Looks up the corresponding `Packet` in the model.
3. Rebuilds the detail tree and refills the hex dump.

If multiple rows are selected, react to only the first (or the most recently clicked). For this project, configure `QTableView.SelectionMode.SingleSelection`.

### Monospace Font for the Hex Pane

Visual alignment matters in a hex dump. Use a monospace font (`QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)`) on the hex widget. Otherwise the columns will not align and the readout becomes unreadable.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Qt — QStandardItemModel docs](https://doc.qt.io/qt-6/qstandarditemmodel.html) | Tree model construction |
| [Qt — QTreeView class reference](https://doc.qt.io/qt-6/qtreeview.html) | View configuration |
| [Qt — Item Selection Tutorial](https://doc.qt.io/qt-6/model-view-programming.html#handling-selections-in-item-views) | Selection model usage |
| [Qt — QFontDatabase](https://doc.qt.io/qt-6/qfontdatabase.html) | Picking the right monospace font |
| Wireshark source: `ui/qt/byte_view_text.cpp` | Reference hex view implementation |
| Wireshark UI screenshots | Visual reference for what your output should look like |

---

## Steps for Implementation

### Step 1 — Implement `PacketDetailTreeView`

Create `src/eps/ui/packet_detail.py`:

```python
"""Hierarchical packet detail view, mirroring Wireshark's middle pane."""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QTreeView
from eps.core.packet import Packet


class PacketDetailTreeView(QTreeView):
    def __init__(self) -> None:
        super().__init__()
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Field", "Value"])
        self.setModel(self._model)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)

    def show_packet(self, pkt: Packet) -> None:
        self._model.removeRows(0, self._model.rowCount())

        # Ethernet layer
        eth_root = QStandardItem("Ethernet II")
        eth_root.appendRow([QStandardItem("Source MAC"), QStandardItem(pkt.src_mac or "")])
        eth_root.appendRow([QStandardItem("Destination MAC"), QStandardItem(pkt.dst_mac or "")])
        if pkt.ethertype is not None:
            eth_root.appendRow([
                QStandardItem("EtherType"),
                QStandardItem(f"0x{pkt.ethertype:04x}"),
            ])
        self._model.appendRow(eth_root)

        # Network layer
        if pkt.src_ip:
            label = "IPv6" if ":" in pkt.src_ip else "IPv4"
            ip_root = QStandardItem(label)
            ip_root.appendRow([QStandardItem("Source"), QStandardItem(pkt.src_ip)])
            ip_root.appendRow([QStandardItem("Destination"), QStandardItem(pkt.dst_ip or "")])
            ip_root.appendRow([
                QStandardItem("Protocol"),
                QStandardItem(_proto_name(pkt.ip_proto)),
            ])
            self._model.appendRow(ip_root)

        # Transport layer
        if pkt.src_port is not None:
            tx_label = "TCP" if pkt.ip_proto == 6 else "UDP"
            tx_root = QStandardItem(tx_label)
            tx_root.appendRow([
                QStandardItem("Source Port"),
                QStandardItem(str(pkt.src_port)),
            ])
            tx_root.appendRow([
                QStandardItem("Destination Port"),
                QStandardItem(str(pkt.dst_port)),
            ])
            if pkt.tcp_flags:
                tx_root.appendRow([
                    QStandardItem("Flags"),
                    QStandardItem(pkt.tcp_flags),
                ])
            self._model.appendRow(tx_root)

        # Metadata
        meta_root = QStandardItem("Frame")
        meta_root.appendRow([
            QStandardItem("Timestamp"),
            QStandardItem(f"{pkt.ts:.6f}"),
        ])
        meta_root.appendRow([
            QStandardItem("Length"),
            QStandardItem(f"{pkt.length} bytes"),
        ])
        self._model.appendRow(meta_root)

        self.expandAll()
        self.resizeColumnToContents(0)


def _proto_name(proto: int | None) -> str:
    names = {1: "ICMP", 6: "TCP", 17: "UDP", 58: "ICMPv6"}
    if proto is None:
        return "?"
    return f"{names.get(proto, '?')} ({proto})"
```

### Step 2 — Implement `HexDumpView`

Create `src/eps/ui/hex_view.py`:

```python
"""Hex + ASCII dump pane for raw packet bytes."""
from __future__ import annotations
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QPlainTextEdit


class HexDumpView(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def show_bytes(self, data: bytes) -> None:
        self.setPlainText(self._format(data))

    @staticmethod
    def _format(data: bytes) -> str:
        rows = []
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            hex_part = hex_part.ljust(16 * 3 - 1)  # pad short final row
            ascii_part = "".join(
                chr(b) if 0x20 <= b < 0x7F else "." for b in chunk
            )
            rows.append(f"{offset:04x}   {hex_part}   {ascii_part}")
        return "\n".join(rows)
```

### Step 3 — Wire into `MainWindow`

Update `src/eps/ui/main_window.py`:

1. Import `PacketDetailTreeView` and `HexDumpView`.
2. Replace the two placeholder widgets in the splitter with real instances.
3. Connect the table's selection signal:

```python
self._detail_view = PacketDetailTreeView()
self._hex_view = HexDumpView()
# ... splitter.addWidget(self._detail_view); splitter.addWidget(self._hex_view)
self._table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)


def _on_selection_changed(self, selected, deselected) -> None:
    indexes = selected.indexes()
    if not indexes:
        return
    row = indexes[0].row()
    pkt = self._model.packet_at(row)
    self._detail_view.show_packet(pkt)
    self._hex_view.show_bytes(pkt.raw)
```

You will need to add a `packet_at(row)` accessor to `PacketTableModel`:

```python
def packet_at(self, row: int) -> Packet:
    return self._packets[row]
```

Note: the `selectionModel()` is only valid **after** `setModel()` has been called. Make sure the order of construction is correct.

### Step 4 — Visual Polish

- Set initial splitter sizes proportionally (e.g., `splitter.setSizes([500, 250, 250])`).
- Configure the tree to auto-expand on update (already done in `show_packet`).
- Configure the hex view to highlight the byte range of the currently selected field in the tree. **Optional and advanced.** Skip if behind schedule.

### Step 5 — Manual QA

Click around. Verify:

- Selecting different rows updates both lower panes.
- ARP, ICMP, DNS, and HTTPS packets all render their layers correctly.
- The hex view aligns properly (monospace font working).
- Splitter handles work for resizing panes.

---

## Self-Administered Verification Gate

- [ ] Selecting a packet in the table populates both the detail tree and the hex dump.
- [ ] The hex dump is aligned (monospace font).
- [ ] The detail tree shows Ethernet, IP (v4 or v6), TCP/UDP, and a Frame metadata node where applicable.
- [ ] Splitters allow the user to resize panes.
- [ ] No PyQt6 imports leaked into `eps.core` (run `lint-imports`).
- [ ] I can explain why a custom `QAbstractItemModel` would be needed for very large hierarchies, even though `QStandardItemModel` suffices here.

Once all boxes are checked, you may begin Phase 7.
