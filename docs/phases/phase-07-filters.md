# Phase 7 — Capture and Display Filters

**Estimated duration:** 1 week
**Prerequisite:** Phase 6 complete
**Outcome:** A working BPF capture filter (kernel-level, set before capture starts) and a display filter (post-capture, applied via a `QSortFilterProxyModel`).

---

## Relevant Knowledge

### Capture Filter vs Display Filter — The Distinction

These two concepts are easy to confuse, but they are fundamentally different:

| | Capture Filter (BPF) | Display Filter |
|---|---|---|
| When applied | Before the packet reaches user space | After capture, on stored packets |
| Where applied | In the kernel via libpcap/BPF | In your application |
| Syntax | pcap-filter (`tcp port 443`) | Your own DSL (`ip.src == 192.168.1.1`) |
| Effect | Drops packets — they are gone forever | Hides packets in the UI — data preserved |
| Can change mid-capture? | No, must restart capture | Yes, applied lazily |
| Performance | Free (kernel handles it) | Costs CPU per displayed row |

**When to use which:**

- **Capture filter:** when you know in advance you only want certain traffic (e.g., debugging an HTTPS issue → `tcp port 443`). Drops the rest at the kernel boundary, reducing CPU and memory.
- **Display filter:** when you want to keep everything but show a subset. Useful for exploratory analysis when you do not yet know what is relevant.

Wireshark exposes both, with different syntaxes, for exactly this reason. We will follow the same convention.

### BPF Filter Syntax (Refresher)

| Expression | Meaning |
|---|---|
| `tcp` | All TCP packets |
| `udp` | All UDP packets |
| `port 80` | Either source or destination port is 80 |
| `src port 80` | Source port is 80 |
| `dst host 1.2.3.4` | Destination IP is 1.2.3.4 |
| `host 1.2.3.4 and port 80` | To/from 1.2.3.4 on port 80 |
| `not arp` | Everything except ARP |
| `tcp[tcpflags] & tcp-syn != 0` | Packets with SYN flag set |
| `ip6` | IPv6 only |

Full reference: pcap-filter(7) man page.

### Display Filter Design

You have two options:

1. **String matching only.** Simple: parse expressions like `tcp.port == 443` or `ip.src == 10.0.0.1` with a regex. Fast to implement, limited.
2. **Expression parser with AST.** Build a tiny grammar that supports `and`, `or`, `not`, comparisons. More work, but extensible.

For this project, start with option 1. Support these operators:

- `eq` or `==`
- `ne` or `!=`
- `contains` (substring match for `summary` field)

Supported field names:

- `ip.src`, `ip.dst`
- `tcp.port`, `tcp.srcport`, `tcp.dstport`
- `udp.port`, `udp.srcport`, `udp.dstport`
- `proto` (string: TCP, UDP, ICMP)
- `len` (numeric)
- `info` (substring match against summary)

Example filters:

```
ip.src == 10.0.0.5
tcp.dstport == 443
proto == TCP
len > 1000          (optional — supports numeric comparisons)
info contains "GET /"
```

### `QSortFilterProxyModel`

Qt provides `QSortFilterProxyModel` to add filtering and sorting on top of any source model without modifying it. You subclass it and override `filterAcceptsRow(source_row, source_parent)`. The view is set to the proxy; the proxy reads from the source model.

This means the table view shows only the filtered rows, but the underlying data (the source `PacketTableModel`) retains everything. Toggle the display filter on/off and rows reappear instantly without re-capture.

### Validating BPF Filters Before Use

A BPF filter with bad syntax causes `AsyncSniffer.start()` to fail. To give the user immediate feedback, validate the filter before starting capture:

```python
from scapy.arch.common import compile_filter

def is_valid_bpf(filter_str: str) -> tuple[bool, str]:
    if not filter_str:
        return True, ""
    try:
        compile_filter(filter_str)
        return True, ""
    except Exception as e:
        return False, str(e)
```

If invalid, show an error in the status bar and refuse to start.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [tcpdump pcap-filter(7)](https://www.tcpdump.org/manpages/pcap-filter.7.html) | Authoritative BPF syntax |
| [Wireshark display filter reference](https://www.wireshark.org/docs/dfref/) | Inspiration for your display filter |
| [Qt — QSortFilterProxyModel](https://doc.qt.io/qt-6/qsortfilterproxymodel.html) | Proxy model API |
| [Python re module](https://docs.python.org/3/library/re.html) | For parsing display filter strings |
| Wireshark source: `epan/dfilter/` | Reference (very advanced) display filter implementation |

---

## Steps for Implementation

### Step 1 — BPF Filter Validation

Add a helper in `src/eps/core/filters.py`:

```python
"""Capture and display filter logic."""
from __future__ import annotations
from dataclasses import dataclass
from eps.core.packet import Packet


def validate_bpf(filter_str: str) -> tuple[bool, str]:
    if not filter_str.strip():
        return True, ""
    try:
        from scapy.arch.common import compile_filter
        compile_filter(filter_str)
        return True, ""
    except Exception as e:
        return False, str(e)
```

### Step 2 — Display Filter

In the same `filters.py`:

```python
import re


@dataclass(frozen=True)
class DisplayFilter:
    """A simple, single-expression display filter.

    Supported syntax: <field> <op> <value>
        field: ip.src, ip.dst, tcp.port, tcp.srcport, tcp.dstport,
               udp.port, udp.srcport, udp.dstport, proto, len, info
        op:    ==, !=, contains, >, <, >=, <=
    """
    field: str
    op: str
    value: str

    _PATTERN = re.compile(
        r"^\s*(?P<field>[a-zA-Z_.]+)\s*"
        r"(?P<op>==|!=|>=|<=|>|<|contains)\s*"
        r"(?P<value>.+?)\s*$"
    )

    @classmethod
    def parse(cls, text: str) -> "DisplayFilter | None":
        if not text.strip():
            return None
        m = cls._PATTERN.match(text)
        if not m:
            raise ValueError(f"Invalid filter: {text!r}")
        value = m.group("value").strip().strip('"').strip("'")
        return cls(m.group("field"), m.group("op"), value)

    def matches(self, p: Packet) -> bool:
        actual = self._extract(p)
        if actual is None:
            return False
        return self._compare(actual, self.op, self.value)

    def _extract(self, p: Packet):
        if self.field == "ip.src":   return p.src_ip
        if self.field == "ip.dst":   return p.dst_ip
        if self.field == "tcp.srcport": return p.src_port if p.ip_proto == 6 else None
        if self.field == "tcp.dstport": return p.dst_port if p.ip_proto == 6 else None
        if self.field == "tcp.port":
            return [p.src_port, p.dst_port] if p.ip_proto == 6 else None
        if self.field == "udp.srcport": return p.src_port if p.ip_proto == 17 else None
        if self.field == "udp.dstport": return p.dst_port if p.ip_proto == 17 else None
        if self.field == "udp.port":
            return [p.src_port, p.dst_port] if p.ip_proto == 17 else None
        if self.field == "proto":
            return {6: "TCP", 17: "UDP", 1: "ICMP"}.get(p.ip_proto or -1, "")
        if self.field == "len":      return p.length
        if self.field == "info":     return p.summary
        return None

    @staticmethod
    def _compare(actual, op: str, expected: str) -> bool:
        if isinstance(actual, list):
            return any(DisplayFilter._compare(a, op, expected) for a in actual)
        if op == "contains":
            return expected in str(actual)
        if op in ("==", "!="):
            equal = str(actual) == expected
            return equal if op == "==" else not equal
        try:
            actual_n, expected_n = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
        return {
            ">":  actual_n >  expected_n,
            "<":  actual_n <  expected_n,
            ">=": actual_n >= expected_n,
            "<=": actual_n <= expected_n,
        }[op]
```

Write unit tests:

```python
# tests/test_filters.py
from eps.core.filters import DisplayFilter, validate_bpf
from eps.core.packet import Packet


def make_packet(**kw) -> Packet:
    defaults = dict(
        ts=0.0, src_mac=None, dst_mac=None, ethertype=None,
        src_ip=None, dst_ip=None, ip_proto=None,
        src_port=None, dst_port=None, tcp_flags=None,
        length=0, summary="", raw=b"",
    )
    defaults.update(kw)
    return Packet(**defaults)


def test_parse_simple():
    f = DisplayFilter.parse("ip.src == 10.0.0.1")
    assert f.field == "ip.src" and f.op == "==" and f.value == "10.0.0.1"


def test_matches_src_ip():
    f = DisplayFilter.parse("ip.src == 10.0.0.1")
    assert f.matches(make_packet(src_ip="10.0.0.1"))
    assert not f.matches(make_packet(src_ip="10.0.0.2"))


def test_proto():
    f = DisplayFilter.parse("proto == TCP")
    assert f.matches(make_packet(ip_proto=6))
    assert not f.matches(make_packet(ip_proto=17))


def test_validate_bpf_good():
    ok, err = validate_bpf("tcp port 443")
    assert ok and not err


def test_validate_bpf_bad():
    ok, _ = validate_bpf("this is not valid")
    assert not ok
```

### Step 3 — `PacketProxyModel`

Create `src/eps/ui/packet_proxy.py`:

```python
"""QSortFilterProxyModel implementing display filter logic."""
from __future__ import annotations
from PyQt6.QtCore import QSortFilterProxyModel, QModelIndex
from eps.core.filters import DisplayFilter
from eps.ui.packet_table import PacketTableModel


class PacketProxyModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._filter: DisplayFilter | None = None

    def set_filter(self, text: str) -> None:
        try:
            self._filter = DisplayFilter.parse(text) if text else None
        except ValueError:
            self._filter = None
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if self._filter is None:
            return True
        source: PacketTableModel = self.sourceModel()
        pkt = source.packet_at(source_row)
        return self._filter.matches(pkt)
```

### Step 4 — Wire Filters into `MainWindow`

1. Add a second `QLineEdit` to the toolbar for the display filter, distinct from the BPF input.
2. Set the `QTableView` model to a `PacketProxyModel`, with `PacketTableModel` as the source.
3. Connect the BPF input to validation on Start.
4. Connect the display filter input's `returnPressed` signal to `proxy.set_filter(input.text())`.
5. When the user selects a row, you now need to map the proxy index back to the source index before calling `packet_at`:

```python
source_index = self._proxy.mapToSource(indexes[0])
pkt = self._model.packet_at(source_index.row())
```

### Step 5 — Manual QA

- Type a valid BPF filter, click Start. Verify only matching traffic is captured.
- Type an invalid BPF filter. Verify Start refuses and shows the error.
- Capture mixed traffic without a filter.
- Apply display filters: `ip.src == <your IP>`, `proto == TCP`, `info contains "GET"`.
- Clear the display filter. Verify all rows reappear.

---

## Self-Administered Verification Gate

- [ ] BPF filter input validates before capture starts; invalid filters are rejected with a clear error.
- [ ] Display filter input applies in real time without re-capturing.
- [ ] Toggling the display filter restores rows without data loss.
- [ ] Unit tests for `DisplayFilter` pass.
- [ ] Selecting a filtered row still populates the detail tree correctly (proxy/source index mapping works).
- [ ] `lint-imports` passes.

Once all boxes are checked, you may begin Phase 8.
