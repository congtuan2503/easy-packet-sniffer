# Phase 8 — Statistics and Conversations

**Estimated duration:** 1 week
**Prerequisite:** Phase 7 complete
**Outcome:** A Statistics dialog accessible from the menu, showing Protocol Hierarchy, Top Talkers (endpoints), and Conversations (src/dst pairs). Optional: a bar chart visualization.

---

## Relevant Knowledge

### What Statistics Mean in a Network Analyzer

Wireshark exposes a wide family of statistics under its Statistics menu. The three most useful for general analysis are:

1. **Protocol Hierarchy.** A tree showing how packets distribute across protocols, with counts and bytes at each layer. Reveals what dominates traffic and surfaces unexpected protocols.
2. **Endpoints (Top Talkers).** Per-IP-address counts of packets sent/received and total bytes. Identifies which host is causing the most traffic.
3. **Conversations.** Per-(src, dst) pair counts and byte totals. Reveals the flows between specific peers — e.g., your machine talking to a specific server.

These are diagnostic mainstays. An incident responder looks at endpoints first to find a noisy host; a network engineer looks at protocol hierarchy to spot unexpected protocols.

### Aggregation Strategy

There are two ways to compute statistics:

| Strategy | When to use | Trade-off |
|---|---|---|
| **Incremental** — update counters as each packet arrives | Live capture | Cheap per-packet, but every counter must be a thread-safe structure |
| **On-demand** — recompute from the full packet list when the user opens the dialog | After-the-fact analysis | Simple, but slow for large captures |

For this project, use **on-demand**. The packet list is already in memory; iterating over it once when the user clicks "Statistics" is fast enough for tens of thousands of packets. Avoid the complexity of incremental counters that update from the producer thread.

### Hierarchical Protocol Counters

The Protocol Hierarchy view is itself a tree:

```
Ethernet                       100% (10000 pkt, 12.3 MB)
  IPv4                          85% (8500 pkt, 11.0 MB)
    TCP                         70% (7000 pkt, 10.5 MB)
      HTTP                      30% (3000 pkt, 4.5 MB)
      HTTPS                     35% (3500 pkt, 5.8 MB)
    UDP                         15% (1500 pkt, 0.5 MB)
      DNS                       10% (1000 pkt, 0.1 MB)
  IPv6                          10% (1000 pkt, 0.8 MB)
  ARP                            5% (500 pkt, 0.5 MB)
```

For our scope, we only need to count down to the L4 protocol. Layer-7 dissection (HTTP, DNS, etc.) is out of scope.

### Charts in PyQt6

Two reasonable options:

1. **`PyQt6.QtCharts`** — official Qt charts. Requires an additional install (`pip install PyQt6-Charts`). Integrates well with Qt.
2. **`pyqtgraph`** — third-party, designed for high-performance plotting. Better for live updating charts.

For static statistics displayed in a dialog, either is fine. If you want to skip charts entirely (recommended for the first pass), a table with counts and percentages is sufficient.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Wireshark — Statistics menu documentation](https://www.wireshark.org/docs/wsug_html_chunked/ChStatMenu.html) | Reference for what statistics matter |
| [Qt — QTabWidget](https://doc.qt.io/qt-6/qtabwidget.html) | Container for multiple stat views in one dialog |
| [Qt — QDialog](https://doc.qt.io/qt-6/qdialog.html) | Modal/modeless dialog windows |
| [PyQt6-Charts (if you go the charts route)](https://pypi.org/project/PyQt6-Charts/) | Optional |
| [pyqtgraph documentation](https://pyqtgraph.readthedocs.io/) | Alternative chart library |

---

## Steps for Implementation

### Step 1 — Stats Computation

Create `src/eps/core/stats.py`:

```python
"""Domain-layer aggregation logic. No PyQt6 imports allowed."""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable
from eps.core.packet import Packet


@dataclass(frozen=True)
class EndpointStat:
    address: str
    packets_sent: int
    packets_received: int
    bytes_sent: int
    bytes_received: int

    @property
    def total_packets(self) -> int:
        return self.packets_sent + self.packets_received

    @property
    def total_bytes(self) -> int:
        return self.bytes_sent + self.bytes_received


@dataclass(frozen=True)
class ConversationStat:
    addr_a: str
    addr_b: str
    packets: int
    bytes_: int


def protocol_hierarchy(packets: Iterable[Packet]) -> dict:
    """Return {protocol_name: (count, total_bytes)}, ordered by count desc."""
    hier: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [count, bytes]
    for p in packets:
        hier["Ethernet"][0] += 1
        hier["Ethernet"][1] += p.length
        if p.src_ip and ":" not in p.src_ip:
            hier["IPv4"][0] += 1
            hier["IPv4"][1] += p.length
        elif p.src_ip and ":" in p.src_ip:
            hier["IPv6"][0] += 1
            hier["IPv6"][1] += p.length
        if p.ip_proto == 6:
            hier["TCP"][0] += 1; hier["TCP"][1] += p.length
        elif p.ip_proto == 17:
            hier["UDP"][0] += 1; hier["UDP"][1] += p.length
        elif p.ip_proto == 1:
            hier["ICMP"][0] += 1; hier["ICMP"][1] += p.length
    return dict(sorted(hier.items(), key=lambda kv: -kv[1][0]))


def endpoints(packets: Iterable[Packet]) -> list[EndpointStat]:
    sent_pkts: Counter = Counter()
    recv_pkts: Counter = Counter()
    sent_bytes: Counter = Counter()
    recv_bytes: Counter = Counter()
    for p in packets:
        if p.src_ip:
            sent_pkts[p.src_ip] += 1
            sent_bytes[p.src_ip] += p.length
        if p.dst_ip:
            recv_pkts[p.dst_ip] += 1
            recv_bytes[p.dst_ip] += p.length
    all_addrs = set(sent_pkts) | set(recv_pkts)
    return sorted(
        (EndpointStat(a, sent_pkts[a], recv_pkts[a], sent_bytes[a], recv_bytes[a])
         for a in all_addrs),
        key=lambda e: -e.total_packets,
    )


def conversations(packets: Iterable[Packet]) -> list[ConversationStat]:
    counters: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for p in packets:
        if not p.src_ip or not p.dst_ip:
            continue
        # canonicalize so (a,b) and (b,a) merge into one pair
        a, b = sorted([p.src_ip, p.dst_ip])
        counters[(a, b)][0] += 1
        counters[(a, b)][1] += p.length
    return sorted(
        (ConversationStat(a, b, c, B) for (a, b), (c, B) in counters.items()),
        key=lambda c: -c.packets,
    )
```

### Step 2 — Unit Tests for Stats

Create `tests/test_stats.py`. Test each function with a hand-crafted list of `Packet` instances. Verify counts and byte totals.

### Step 3 — Statistics Dialog

Create `src/eps/ui/stats_dialog.py`:

```python
"""Dialog showing protocol hierarchy, endpoints, and conversations."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from eps.core import stats
from eps.core.packet import Packet


class StatsDialog(QDialog):
    def __init__(self, packets: list[Packet], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Statistics")
        self.resize(800, 500)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._protocol_tab(packets), "Protocols")
        tabs.addTab(self._endpoints_tab(packets), "Endpoints")
        tabs.addTab(self._conversations_tab(packets), "Conversations")
        layout.addWidget(tabs)

    def _protocol_tab(self, packets) -> QTableWidget:
        hier = stats.protocol_hierarchy(packets)
        total = sum(v[0] for v in hier.values()) or 1
        tbl = QTableWidget(len(hier), 3)
        tbl.setHorizontalHeaderLabels(["Protocol", "Packets", "Percent"])
        for row, (proto, (count, _bytes)) in enumerate(hier.items()):
            tbl.setItem(row, 0, QTableWidgetItem(proto))
            tbl.setItem(row, 1, QTableWidgetItem(str(count)))
            tbl.setItem(row, 2, QTableWidgetItem(f"{count * 100 / total:.1f}%"))
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return tbl

    def _endpoints_tab(self, packets) -> QTableWidget:
        eps = stats.endpoints(packets)
        tbl = QTableWidget(len(eps), 5)
        tbl.setHorizontalHeaderLabels(
            ["Address", "Sent", "Received", "Bytes Sent", "Bytes Received"]
        )
        for row, e in enumerate(eps):
            tbl.setItem(row, 0, QTableWidgetItem(e.address))
            tbl.setItem(row, 1, QTableWidgetItem(str(e.packets_sent)))
            tbl.setItem(row, 2, QTableWidgetItem(str(e.packets_received)))
            tbl.setItem(row, 3, QTableWidgetItem(str(e.bytes_sent)))
            tbl.setItem(row, 4, QTableWidgetItem(str(e.bytes_received)))
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return tbl

    def _conversations_tab(self, packets) -> QTableWidget:
        convs = stats.conversations(packets)
        tbl = QTableWidget(len(convs), 4)
        tbl.setHorizontalHeaderLabels(["Address A", "Address B", "Packets", "Bytes"])
        for row, c in enumerate(convs):
            tbl.setItem(row, 0, QTableWidgetItem(c.addr_a))
            tbl.setItem(row, 1, QTableWidgetItem(c.addr_b))
            tbl.setItem(row, 2, QTableWidgetItem(str(c.packets)))
            tbl.setItem(row, 3, QTableWidgetItem(str(c.bytes_)))
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return tbl
```

Note: we use `QTableWidget` here (not `QTableView`) because the dataset is tiny (dozens to hundreds of rows max) and the data is static. This is the **one** legitimate place where `QTableWidget` is the right choice.

### Step 4 — Menu Action

In `MainWindow.__init__`, add a menu bar:

```python
menu = self.menuBar()
stats_menu = menu.addMenu("&Statistics")
act_show_stats = QAction("Show statistics", self)
act_show_stats.triggered.connect(self._on_show_stats)
stats_menu.addAction(act_show_stats)


def _on_show_stats(self) -> None:
    from eps.ui.stats_dialog import StatsDialog
    packets = self._model.all_packets()  # add this accessor to PacketTableModel
    dlg = StatsDialog(packets, self)
    dlg.exec()
```

Add `all_packets()` to `PacketTableModel`:

```python
def all_packets(self) -> list[Packet]:
    return list(self._packets)
```

### Step 5 — Optional Chart

If time permits, add a fourth tab to `StatsDialog` with a horizontal bar chart of the protocol distribution. Use `pyqtgraph` (easier) or `PyQt6.QtCharts` (official). Skip if behind schedule.

---

## Self-Administered Verification Gate

- [ ] `src/eps/core/stats.py` exists with `protocol_hierarchy`, `endpoints`, `conversations`.
- [ ] All three functions have passing unit tests.
- [ ] The Statistics dialog opens from the menu and shows three tabs.
- [ ] Counts and percentages match what Wireshark reports on the same capture (within rounding).
- [ ] `src/eps/core/stats.py` does not import `PyQt6` (verify with grep).
- [ ] `lint-imports` passes.

Once all boxes are checked, you may begin Phase 9.
