# Easy Packet Sniffer — Project Guide and Handoff Document

> **Purpose of this file.** This document is the single source of truth for the Easy Packet Sniffer project. It is intended to be pasted to any AI assistant (Claude, GPT, Gemini, etc.) so that the assistant can immediately understand the project's goals, technical stack, architecture, current progress, and the developer's preferred working style — without re-running calibration. Read this entire file before producing any response.

---

## 1. Project Overview

**Project name:** Easy Packet Sniffer
**Type:** Desktop application — Wireshark-style network analyzer
**Purpose:** A portfolio artifact for a 3rd-year Cybersecurity and Computer Science student. The project must (a) teach the developer networking and software engineering fundamentals deeply, and (b) be presentable to employers as evidence of competence.

**Functional scope at completion:**
- Live packet capture from a selectable network interface on Windows.
- Parsing of Ethernet, IPv4, IPv6, TCP, UDP, ARP, ICMP, and DNS protocols.
- Three-pane GUI in the Wireshark tradition: packet list (top), packet detail tree (middle), hex/ASCII dump (bottom).
- Capture filters (BPF, kernel-level) and display filters (post-capture).
- Save to and load from `.pcap` files, with interoperability with Wireshark.
- Basic statistics: protocol hierarchy, top talkers, conversation summary.

**Non-goals:**
- TLS decryption.
- Active scanning, injection, or any traffic generation.
- Cross-platform release engineering. Windows is the primary target. The architecture is portable but no Linux/macOS packaging will be produced.

---

## 2. Developer Profile

The developer is a **3rd-year Cybersecurity + Computer Science student** working on Windows 11.

**Strong areas:**
- C++ (extensively studied).
- Web frontend: React, Tailwind CSS, Node.js. Has built a restaurant table-management application.

**Adequate areas:**
- Python OOP basics. Familiar with the C++ analogy for `__new__`/`__init__`.
- Prior single exposure to `threading.Thread` in an Operating Systems lab.

**Gaps to address explicitly:**
- Has not used `@staticmethod` vs `@classmethod`, type hints, `queue.Queue`, or `asyncio`.
- Unaware of raw sockets and why packet capture requires elevated privileges.
- Limited intuition for multi-threaded GUI architecture and the GIL.

**Misconceptions corrected during initial calibration (must remain corrected):**

1. **Encapsulation direction.** Initially believed Ethernet is wrapped by IP wrapped by TCP. Correct order on the wire: `[Ether | IP | TCP | Payload]` — TCP wraps payload, IP wraps TCP, Ethernet wraps IP.
2. **Ethernet layer.** Initially placed at L1 (Physical). Correct: L2 (Data Link). L1 is voltages and signaling, not framed structures.
3. **TCP three-way handshake flags.** Initially identified the third handshake packet as `[P.]`. Correct sequence: `[S]` (SYN), `[S.]` (SYN+ACK), `[.]` (ACK). `[P.]` is PSH+ACK, a data-carrying segment, not part of the handshake.
4. **MVC pattern.** Initially described as a UX dashboard. Correct: a separation-of-concerns architectural pattern where the Model (data + business logic) is forbidden from knowing anything about the View (presentation), and the Controller translates user intent into model operations.

**Tooling and environment:**
- OS: Windows 11.
- Python: 3.14.2 (bleeding edge — pin dependencies carefully).
- Npcap: installed in WinPcap API-compatible Mode (required for Scapy on Windows).
- Has used Wireshark in coursework; has seen tcpdump demonstrated but not used it hands-on.

---

## 3. Mentoring Protocol (REQUIRED — How to Communicate)

Any AI assistant working with this developer must follow these rules. Deviation produces a poor experience and wastes the developer's credits.

1. **No emojis. Anywhere. Ever.** This is non-negotiable.
2. **Enterprise-grade tone.** Professional, academic, technical. Match the standard of Wireshark's documentation, not a hobby tutorial.
3. **Minimal Socratic questioning.** The developer has **limited AI credits**. Ask at most one consolidated check-in per phase, only when verification is truly necessary. Front-load explanations. Deliver dense content per turn rather than drawing out dialogue across many turns.
4. **Strict code review.** When the developer submits code, point out mistakes plainly and without softening. Letting errors slide is worse than catching them — it wastes more credits later. Deliver corrections in batched, dense form.
5. **Self-administered verification gates.** Provide checklists the developer runs on their own. Intervene only when they get stuck or report a blocker. Do not quiz them turn-by-turn.
6. **Honest calibration over flattery.** When the developer is wrong, name it as "Misconception" or "Critical misconception" and correct it before proceeding.
7. **Frame Python via C++ analogies where useful, but flag where the analogy breaks** (data model, decorators, GIL).
8. **Bridge Qt's signal/slot model to the developer's existing React mental model.** They will find Qt's imperative event model unfamiliar after React's declarative reconciliation.
9. **Mandatory reading is the developer's homework between sessions.** Do not re-explain content covered in the reading list. Refer them back to the source.

---

## 4. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.14.2 | Fast development, large ecosystem, accessible to the developer. |
| Packet capture | Scapy (>=2.6, <3.0) | High-level packet dissection; mirrors Wireshark's parsing approach. Allows optional drop-down to raw sockets for educational segments. |
| Capture driver | Npcap (Windows) | Required by Scapy on Windows. Installed in WinPcap API-compatible Mode. |
| GUI toolkit | PyQt6 (>=6.8, <7.0) | Same toolkit family used by Wireshark's frontend. Enterprise-grade. Mature Model/View architecture. |
| Test framework | pytest (>=8.0, <9.0) | Standard. Headless. |
| Architecture enforcement | `import-linter` (added in Phase 4) | Enforces that the core layer never imports PyQt6. |
| Packaging (Phase 9) | PyInstaller | Produces a Windows executable for portfolio demonstration. |

**Alternatives that were considered and rejected:**
- C/C++ + libpcap + Qt — too long a development cycle for the available time.
- Go + gopacket + Fyne — weaker UI ecosystem.
- Pure raw sockets in Python — too low-level for a UI-heavy project, but retained as an optional Phase 2 educational track.

---

## 5. Software Architecture — Three-Layer Separation

The project uses a strict three-layer separation of concerns, enforced by directory boundaries and by `import-linter` rules. The core/domain layer is **forbidden from importing PyQt6**; this is the single most important architectural rule.

```
+============================================================+
|                  PRESENTATION LAYER (View)                 |
|                       PyQt6 widgets                        |
|                                                            |
|  MainWindow                                                |
|    +-- Toolbar (Start, Stop, Open, Save, Filter input)     |
|    +-- PacketTableView      (live packet list)             |
|    +-- PacketDetailTreeView (selected packet, hierarchy)   |
|    +-- HexDumpView          (raw bytes pane)               |
|    +-- StatusBar            (counts, drops, errors)        |
|                                                            |
|  Imports allowed:  PyQt6, app.controllers, app.viewmodels  |
|  Forbidden:        scapy, raw sockets, pcap I/O            |
+============================================================+
              ^                                  |
              |  Qt signals (PacketCaptured,     | UI events
              |  CaptureStopped, ErrorRaised)    | (button.clicked)
              |                                  v
+============================================================+
|              APPLICATION LAYER (Controller)                |
|                                                            |
|  CaptureController                                         |
|    - start_capture(iface, bpf_filter)                      |
|    - stop_capture()                                        |
|    - save_to_pcap(path)                                    |
|    - load_pcap(path)                                       |
|                                                            |
|  Bridges worker-thread capture events to Qt signals via    |
|  QThread + pyqtSignal.                                     |
|                                                            |
|  Imports allowed:  app.core, PyQt6.QtCore (signals only)   |
|  Forbidden:        any PyQt6 widget                        |
+============================================================+
              ^                                  |
              |  Packet objects via Queue        | commands
              |                                  v
+============================================================+
|                    DOMAIN / CORE LAYER (Model)             |
|                                                            |
|  capture_engine.py   CaptureEngine                         |
|                       - sniff loop (Scapy AsyncSniffer)    |
|                       - emits domain Packet objects        |
|                                                            |
|  packet.py           Packet (frozen dataclass)             |
|                       ts, src_mac, dst_mac,                |
|                       src_ip, dst_ip, proto,               |
|                       src_port, dst_port, length, flags    |
|                                                            |
|  parser.py           parse(raw_scapy_pkt) -> Packet        |
|                                                            |
|  pcap_io.py          PcapWriter / PcapReader               |
|                                                            |
|  filters.py          BpfFilter (capture-level)             |
|                      DisplayFilter (post-capture)          |
|                                                            |
|  Imports allowed:  scapy, stdlib                           |
|  Forbidden:        PyQt6 — anything at all                 |
+============================================================+
                              |
                              v
+============================================================+
|             INFRASTRUCTURE / OS LAYER                      |
|                                                            |
|  Npcap (Windows) -> Scapy -> raw socket -> NIC             |
|  in promiscuous mode                                       |
+============================================================+
```

### Directory Layout

```
easy-packet-sniffer/
├── pyproject.toml
├── README.md
├── PROJECT_GUIDE.md            # This file
├── .gitignore
├── src/
│   └── eps/
│       ├── __init__.py
│       ├── core/               # Domain layer — no PyQt6 imports allowed
│       │   ├── __init__.py
│       │   ├── capture_engine.py
│       │   ├── packet.py
│       │   ├── parser.py
│       │   ├── pcap_io.py
│       │   └── filters.py
│       ├── controllers/        # Application layer — Qt signals only
│       │   ├── __init__.py
│       │   └── capture_controller.py
│       ├── ui/                 # Presentation layer
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── packet_table.py
│       │   ├── packet_detail.py
│       │   ├── hex_view.py
│       │   └── widgets/
│       └── main.py             # Entry point: composes the layers
├── tests/
│   ├── test_parser.py          # Must run with no display server
│   ├── test_capture_engine.py
│   └── fixtures/
│       └── sample.pcap
└── docs/
    └── architecture.md
```

**Invariant:** `pytest tests/test_parser.py` must succeed on a headless machine with no Qt installed. The day this stops working is the day the architecture has been violated.

---

## 6. Ten-Phase Development Roadmap

Total expected duration: **10–12 weeks** at sustainable student pace.

### Phase 0 — Foundations and Environment Repair (1 week)

**Objective:** Repair the four misconceptions listed in Section 2. Establish a reproducible environment.

**Tasks:**
1. Complete mandatory reading list (Section 10).
2. Create directory tree exactly as in Section 5.
3. Initialize a Python virtual environment: `python -m venv .venv` then `.venv\Scripts\activate`.
4. Create `pyproject.toml` with pinned dependencies.
5. Verify Scapy capture works (run as Administrator on Windows):
   ```
   python -c "from scapy.all import sniff; sniff(count=3, prn=lambda p: print(p.summary()))"
   ```
6. Initialize git repo with `.gitignore` (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `*.pcap`).

**Self-check gate (no AI required):**
- Can you draw the encapsulation order from memory? (`[Ether | IP | TCP | Payload]`)
- Can you list the three handshake flags correctly? (`[S]`, `[S.]`, `[.]`)
- Did the Scapy one-liner print three packet summaries?
- Does `tests/` exist and is it ready for headless unit tests?

### Phase 1 — Terminal Capture Loop (1 week)

**Objective:** Implement `CaptureEngine` with start/stop semantics and a packet callback.

**Concepts:**
- Berkeley Packet Filter (BPF): kernel-level filtering for performance.
- Scapy's `AsyncSniffer` (background thread) vs synchronous `sniff()` (blocks).
- Promiscuous mode: capturing frames not addressed to your NIC.
- Capture statistics, especially drops.

**Code skeleton — `src/eps/core/capture_engine.py`:**
```python
from __future__ import annotations
from typing import Callable, Optional
from scapy.all import AsyncSniffer
from scapy.packet import Packet as ScapyPacket


class CaptureEngine:
    """Thread-managed packet capture using Scapy's AsyncSniffer.

    Domain-layer class. Forbidden from importing anything from PyQt6.
    """

    def __init__(self, iface: str, bpf_filter: str = "") -> None:
        self._iface = iface
        self._bpf_filter = bpf_filter
        self._sniffer: Optional[AsyncSniffer] = None
        self._on_packet: Optional[Callable[[ScapyPacket], None]] = None

    def set_packet_callback(self, fn: Callable[[ScapyPacket], None]) -> None:
        self._on_packet = fn

    def start(self) -> None:
        if self._sniffer is not None:
            raise RuntimeError("Capture already running")
        self._sniffer = AsyncSniffer(
            iface=self._iface,
            filter=self._bpf_filter or None,
            prn=self._on_packet,
            store=False,  # Do not retain packets in memory — we hand them off
        )
        self._sniffer.start()

    def stop(self) -> dict:
        if self._sniffer is None:
            raise RuntimeError("Capture not running")
        results = self._sniffer.stop()
        stats = {
            "captured": len(results) if results else 0,
            # Scapy exposes drop counters via the underlying socket
        }
        self._sniffer = None
        return stats
```

**Throwaway CLI driver:** write a small `scripts/cli_capture.py` that instantiates `CaptureEngine`, attaches a `print(pkt.summary())` callback, and runs for 10 seconds.

**Self-check gate:**
- Does `CaptureEngine` work without importing PyQt6? (Verify by running the CLI driver.)
- Can you explain in writing why `store=False` is correct? (Hint: memory pressure during long captures.)

### Phase 2 — Packet Parsing and Domain Object (1–2 weeks)

**Objective:** Convert Scapy's verbose object into a lean immutable domain object.

**Concepts:**
- Header field offsets for Ethernet (14 B, or 18 B with VLAN), IPv4 (20+ B), IPv6 (40 B), TCP (20+ B), UDP (8 B).
- `@dataclass(frozen=True)` — immutability for thread-safety.
- Why immutability matters when objects are passed between a producer thread and a consumer thread.
- Optional rigorous track: re-implement the Ethernet + IPv4 + TCP parser using `struct.unpack` on raw bytes from a `.pcap` fixture. This is the segment that produces the deepest learning.

**Code skeleton — `src/eps/core/packet.py`:**
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Packet:
    """Immutable domain representation of a single captured packet.

    Fields are populated on a best-effort basis. Unparseable layers
    yield None for the corresponding fields.
    """
    ts: float                          # capture timestamp (UNIX epoch)
    src_mac: Optional[str]
    dst_mac: Optional[str]
    ethertype: Optional[int]
    src_ip: Optional[str]
    dst_ip: Optional[str]
    ip_proto: Optional[int]            # 6 = TCP, 17 = UDP, 1 = ICMP
    src_port: Optional[int]
    dst_port: Optional[int]
    tcp_flags: Optional[str]           # e.g. "S", "S.", "."
    length: int                        # total bytes on the wire
    summary: str                       # human-readable one-liner
    raw: bytes                         # original bytes for hex dump
```

**Code skeleton — `src/eps/core/parser.py`:**
```python
from __future__ import annotations
from scapy.packet import Packet as ScapyPacket
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from .packet import Packet


def parse(scapy_pkt: ScapyPacket) -> Packet:
    """Convert a Scapy packet into a frozen domain Packet."""
    ts = float(scapy_pkt.time)
    raw = bytes(scapy_pkt)
    length = len(raw)

    src_mac = dst_mac = ethertype = None
    src_ip = dst_ip = ip_proto = None
    src_port = dst_port = tcp_flags = None

    if Ether in scapy_pkt:
        eth = scapy_pkt[Ether]
        src_mac, dst_mac = eth.src, eth.dst
        ethertype = eth.type

    if IP in scapy_pkt:
        ip = scapy_pkt[IP]
        src_ip, dst_ip, ip_proto = ip.src, ip.dst, ip.proto
    elif IPv6 in scapy_pkt:
        ip6 = scapy_pkt[IPv6]
        src_ip, dst_ip, ip_proto = ip6.src, ip6.dst, ip6.nh

    if TCP in scapy_pkt:
        tcp = scapy_pkt[TCP]
        src_port, dst_port = tcp.sport, tcp.dport
        tcp_flags = str(tcp.flags)
    elif UDP in scapy_pkt:
        udp = scapy_pkt[UDP]
        src_port, dst_port = udp.sport, udp.dport

    return Packet(
        ts=ts, src_mac=src_mac, dst_mac=dst_mac, ethertype=ethertype,
        src_ip=src_ip, dst_ip=dst_ip, ip_proto=ip_proto,
        src_port=src_port, dst_port=dst_port, tcp_flags=tcp_flags,
        length=length, summary=scapy_pkt.summary(), raw=raw,
    )
```

**Deliverable:** `tests/test_parser.py` with at least 10 cases using captured `.pcap` fixtures. **No live capture in tests.**

### Phase 3 — Persistence (`.pcap` Read/Write) (3–5 days)

**Objective:** Read and write `.pcap` files. Round-trip with Wireshark.

**Code skeleton — `src/eps/core/pcap_io.py`:**
```python
from __future__ import annotations
from pathlib import Path
from scapy.utils import wrpcap, rdpcap
from scapy.packet import Packet as ScapyPacket


def write_pcap(path: Path, packets: list[ScapyPacket]) -> None:
    wrpcap(str(path), packets)


def read_pcap(path: Path) -> list[ScapyPacket]:
    return list(rdpcap(str(path)))
```

**Round-trip test:** capture N packets, write, read back, assert equal count and equal summaries.

### Phase 4 — Threading and Controller (1 week)

**Objective:** Producer-consumer pattern. `CaptureEngine` runs in a worker thread; UI receives packets via Qt signals.

**Concepts:**
- The Global Interpreter Lock (GIL): only one Python bytecode at a time, but I/O releases the GIL — so Python threading is useful for I/O-bound work like packet capture.
- Qt is not thread-safe for GUI objects: only the main thread may touch widgets.
- `pyqtSignal` provides a safe queued cross-thread bridge.

**Code skeleton — `src/eps/controllers/capture_controller.py`:**
```python
from __future__ import annotations
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from eps.core.capture_engine import CaptureEngine
from eps.core.parser import parse
from eps.core.packet import Packet


class CaptureController(QObject):
    packet_received = pyqtSignal(object)   # emits Packet
    capture_stopped = pyqtSignal(dict)     # emits stats
    error_raised = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine: CaptureEngine | None = None

    def start(self, iface: str, bpf_filter: str = "") -> None:
        if self._engine is not None:
            self.error_raised.emit("Capture already running")
            return
        self._engine = CaptureEngine(iface, bpf_filter)
        self._engine.set_packet_callback(self._on_packet)
        try:
            self._engine.start()
        except Exception as e:
            self.error_raised.emit(str(e))
            self._engine = None

    def stop(self) -> None:
        if self._engine is None:
            return
        stats = self._engine.stop()
        self._engine = None
        self.capture_stopped.emit(stats)

    def _on_packet(self, scapy_pkt) -> None:
        # Runs in Scapy's worker thread. pyqtSignal.emit is thread-safe.
        try:
            self.packet_received.emit(parse(scapy_pkt))
        except Exception as e:
            self.error_raised.emit(f"Parse error: {e}")
```

**Add `import-linter` configuration to `pyproject.toml` to enforce that `eps.core` cannot import `PyQt6`.**

### Phase 5 — Minimum Viable PyQt6 UI (2 weeks)

**Objective:** Three-pane UI with live-updating packet table.

**Concepts:**
- Qt's Model/View architecture: separate the data (`QAbstractTableModel`) from the rendering (`QTableView`). Do NOT use `QTableWidget` — it does not scale.
- Qt's event loop. Comparison to React's reconciliation loop.
- Code-driven UI (not `.ui` files): easier to diff in version control.

**Code skeleton — `src/eps/ui/packet_table.py`:**
```python
from __future__ import annotations
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from eps.core.packet import Packet


COLUMNS = ("Time", "Source", "Destination", "Proto", "Length", "Info")


class PacketTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._packets: list[Packet] = []

    def append(self, pkt: Packet) -> None:
        row = len(self._packets)
        self.beginInsertRows(QModelIndex(), row, row)
        self._packets.append(pkt)
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._packets)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or not index.isValid():
            return None
        pkt = self._packets[index.row()]
        col = index.column()
        if col == 0: return f"{pkt.ts:.6f}"
        if col == 1: return pkt.src_ip or pkt.src_mac or ""
        if col == 2: return pkt.dst_ip or pkt.dst_mac or ""
        if col == 3: return _proto_name(pkt.ip_proto)
        if col == 4: return pkt.length
        if col == 5: return pkt.summary
        return None


def _proto_name(proto: int | None) -> str:
    return {6: "TCP", 17: "UDP", 1: "ICMP"}.get(proto or -1, "?")
```

**Connect the controller signal to the model:**
```python
controller.packet_received.connect(table_model.append)
```

**Self-check gate:** capture must run live, the table must update in real time, and scrolling at 1000 pkt/s must not stutter.

### Phase 6 — Packet Detail and Hex Dump (1 week)

**Objective:** When a row in the table is selected, populate a `QTreeView` showing the collapsible Ethernet > IP > TCP > Payload hierarchy, and a hex+ASCII dump pane below.

### Phase 7 — Capture and Display Filters (1 week)

**Concepts:** Capture filter is BPF, applied in the kernel before packets reach user space — fast but cannot be changed retroactively. Display filter is applied after capture — slower but flexible. Provide both.

### Phase 8 — Statistics (1 week)

Protocol hierarchy view, top talkers table, packet/byte counters. Optional: `pyqtgraph` charts.

### Phase 9 — Production Hygiene (3–5 days)

Structured logging via the `logging` module, configuration via `tomllib`, graceful error surfacing, PyInstaller packaging to produce a single Windows executable.

### Phase 10 — Portfolio Presentation (3–5 days)

README with architecture diagram, animated capture demo (GIF), a labeled architecture diagram in `docs/`, and a technical write-up of one non-obvious engineering decision (recommended: why `QAbstractTableModel` instead of `QTableWidget`).

---

## 7. The `pyproject.toml` Template

```toml
[project]
name = "easy-packet-sniffer"
version = "0.1.0"
description = "Wireshark-style packet sniffer with a PyQt6 frontend"
requires-python = ">=3.13"
dependencies = [
    "scapy>=2.6,<3.0",
    "PyQt6>=6.8,<7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "import-linter>=2.0,<3.0",
]

[project.scripts]
eps = "eps.main:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.importlinter]
root_package = "eps"

[[tool.importlinter.contracts]]
name = "Core layer must not import PyQt6"
type = "forbidden"
source_modules = ["eps.core"]
forbidden_modules = ["PyQt6"]

[[tool.importlinter.contracts]]
name = "Controllers must not import Qt widgets"
type = "forbidden"
source_modules = ["eps.controllers"]
forbidden_modules = ["PyQt6.QtWidgets"]
```

---

## 8. Critical Concepts Reference Card

These are the corrections that must remain corrected. Any AI assistant should refer back to these when relevant.

**Encapsulation on the wire (outermost first):**
```
[ Ethernet header | IPv4 header | TCP header | Payload ]
       L2               L3            L4         L7
       14 B          20+ B         20+ B
```

**TCP three-way handshake:**
```
Client ----SYN  [S]----> Server
Client <---SYN+ACK [S.]- Server
Client ----ACK  [.]----> Server
```

`[P.]` is PSH+ACK — a data segment, **not** part of the handshake.

**MVC enforcement in Python:**
There is no language-level enforcement. The rule is upheld by:
1. Directory boundaries as policy.
2. `import-linter` configured to fail the build on violation.
3. Unit tests that run with `PyQt6` not installed in the test environment.

**Why packet capture needs Administrator privileges:**
Raw sockets bypass the kernel's normal socket abstraction (which delivers only packets destined for your process's bound ports). Capturing all traffic on an interface requires direct access to the network driver — a privileged operation. On Windows, this is mediated by Npcap.

**Why `store=False` on `AsyncSniffer`:**
By default Scapy retains every captured packet in memory. For a long-running capture, this exhausts RAM. We hand each packet off to the controller via callback and let Scapy discard the in-memory copy.

**GIL one-liner:**
The GIL prevents two threads from executing Python bytecode simultaneously. **But** I/O operations (including socket reads via Scapy/Npcap) release the GIL, so threading is genuinely useful for I/O-bound workloads. Packet capture is I/O-bound.

**`QTableView` vs `QTableWidget`:**
`QTableWidget` stores data inside the view — every row is a heap-allocated `QTableWidgetItem`. At 10,000+ packets, this becomes slow and memory-heavy. `QTableView` with a custom `QAbstractTableModel` lets the view request only the visible rows, scaling to millions of packets.

---

## 9. Reading List (Developer Homework)

Mandatory before writing Phase 1 code:

| # | Resource | Purpose |
|---|---|---|
| 1 | Kurose & Ross, *Computer Networking: A Top-Down Approach*, Ch. 1.5 (Protocol Layers) and Ch. 4.3 (IPv4) | Encapsulation, layer model |
| 2 | RFC 791 — IPv4 header section | First-hand exposure to header layout |
| 3 | RFC 9293 — sections 3.1 (header) and 3.4 (connection establishment) | TCP semantics |
| 4 | Python docs — `struct` module | Prep for optional raw-socket parser |
| 5 | Python docs — `socket` module overview | Same |
| 6 | Qt for Python docs — "Signals & Slots" tutorial | Bridge React mental model to Qt |
| 7 | Martin Fowler — "GUI Architectures" article (martinfowler.com/eaaDev/uiArchs.html) | MVC and Separated Presentation |

**Reference implementations to study but not copy:**
- Wireshark source — `ui/qt/` for the frontend, `epan/dissectors/` for parsing patterns.
- Scapy source — `scapy/sendrecv.py` for the `sniff`/`AsyncSniffer` implementation.

---

## 10. Current Project Status

**As of 2026-06-17:** Phase 2 Completed.

- Environment and repository scaffold setup completed (Phase 0).
- Asynchronous `CaptureEngine` implemented with callback support, tested via throwaway CLI capture utility (Phase 1).
- Immutable `Packet` domain object defined (`frozen=True`) and parser implementation complete, handling Ethernet, VLAN, ARP, IPv4, IPv6, TCP, UDP, ICMP, and LLDP (Phase 2).
- Unit tests written in `tests/test_parser.py` (9 tests passing).

**Immediate next actions for the developer:**
1. Proceed to Phase 3: Persistence (`.pcap` Read/Write). Implement `pcap_io.py` and write round-trip tests.
2. Advance to Phase 4: Threading and Controller. Establish `capture_controller.py` with PyQt6 signals.

**Immediate next actions for any AI assistant resuming this project:**
1. Initiate Phase 3: provide specifications for `pcap_io.py` and explain Wireshark-compatible PCAP parsing/writing.
2. Provide verification steps for Phase 3 before proceeding to Phase 4.

---

## 11. How to Use This Document

**For the developer:**
- Treat this as the canonical project specification. When in doubt about architecture, structure, or rules, this file overrides any contradicting AI response.
- Update Section 10 ("Current Project Status") after completing each phase. Commit the update.

**For any AI assistant:**
- Read this entire file before producing any response.
- Apply Section 3 (Mentoring Protocol) to your output style.
- Respect Section 5 (Architecture) — never propose code that violates the import boundaries.
- Refer to Section 8 (Concepts Reference Card) when explaining concepts; do not re-derive them from scratch.
- Update Section 10 in your response when the developer reports phase completion.

End of document.
