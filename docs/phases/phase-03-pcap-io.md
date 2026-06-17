# Phase 3 — Persistence (`.pcap` Read and Write)

**Estimated duration:** 3–5 days
**Prerequisite:** Phase 2 complete
**Outcome:** `src/eps/core/pcap_io.py` with `write_pcap()` and `read_pcap()` functions. Round-trip tested. Wireshark-interoperable.

---

## Relevant Knowledge

### The `.pcap` File Format

The classic pcap format (also known as "libpcap format") is binary and simple. Every `.pcap` file begins with a **global header**, followed by zero or more **packet records**.

#### Global Header (24 bytes)

```
+----------------------+------------------------+
| Magic Number (4 B)   | 0xa1b2c3d4 (or var.)   |
+----------------------+------------------------+
| Version Major (2 B)  | 0x0002                 |
+----------------------+------------------------+
| Version Minor (2 B)  | 0x0004                 |
+----------------------+------------------------+
| Reserved (4 B)       | thiszone, must be 0    |
+----------------------+------------------------+
| Reserved (4 B)       | sigfigs, must be 0     |
+----------------------+------------------------+
| Snaplen (4 B)        | Max captured per pkt   |
+----------------------+------------------------+
| LinkType (4 B)       | 1 = Ethernet           |
+----------------------+------------------------+
```

Magic number `0xa1b2c3d4` indicates microsecond resolution. `0xa1b23c4d` indicates nanosecond resolution. The byte order of the magic number tells the reader the endianness of the rest of the file.

#### Per-Packet Header (16 bytes)

```
+----------------------+------------------------+
| ts_sec (4 B)         | Timestamp seconds      |
+----------------------+------------------------+
| ts_usec (4 B)        | Microseconds (or ns)   |
+----------------------+------------------------+
| incl_len (4 B)       | Bytes saved to file    |
+----------------------+------------------------+
| orig_len (4 B)       | Bytes on the wire      |
+----------------------+------------------------+
```

`incl_len <= orig_len`. If the original packet was 1500 bytes but you only captured 96 bytes (`snaplen=96`), then `incl_len=96` and `orig_len=1500`.

After the per-packet header come the actual packet bytes (`incl_len` of them).

### LinkType

The `LinkType` field tells the reader what L2 protocol is at the front of every packet. The only one you care about right now is `LINKTYPE_ETHERNET = 1`. The full list lives at the [tcpdump linktypes registry](https://www.tcpdump.org/linktypes.html).

### pcapng

`pcapng` (Next Generation) is a newer format that supports per-interface metadata, comments, and more. Wireshark writes pcapng by default now. We will not implement pcapng directly — Scapy can read both formats, but write only pcap. This is acceptable for the project's scope. Document the limitation.

### Wireshark Interoperability — The Test That Matters

The acid test for your pcap I/O code: a file you write must open in Wireshark and display every packet correctly, and a file Wireshark writes must open in your tool and display every packet correctly. Anything less means a bug.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Wireshark wiki — libpcap file format](https://wiki.wireshark.org/Development/LibpcapFileFormat) | Authoritative format reference |
| [tcpdump linktypes](https://www.tcpdump.org/linktypes.html) | LinkType enumeration |
| [Scapy `wrpcap` and `rdpcap` source](https://github.com/secdev/scapy/blob/master/scapy/utils.py) | Reference implementation |
| [pcapng spec (IETF draft)](https://www.ietf.org/archive/id/draft-tuexen-opsawg-pcapng-02.html) | For future awareness, not required now |

---

## Steps for Implementation

### Step 1 — Implement `pcap_io.py`

Create `src/eps/core/pcap_io.py`:

```python
"""pcap file I/O. Domain-layer code — no PyQt6 imports allowed."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Iterator
from scapy.packet import Packet as ScapyPacket
from scapy.utils import wrpcap, rdpcap, PcapReader


def write_pcap(path: Path, packets: Iterable[ScapyPacket]) -> None:
    """Write all packets to a single .pcap file (Ethernet linktype)."""
    pkts = list(packets) if not isinstance(packets, list) else packets
    if not pkts:
        raise ValueError("Cannot write empty pcap file")
    wrpcap(str(path), pkts)


def read_pcap(path: Path) -> list[ScapyPacket]:
    """Read all packets from a .pcap file into memory."""
    if not path.exists():
        raise FileNotFoundError(path)
    return list(rdpcap(str(path)))


def stream_pcap(path: Path) -> Iterator[ScapyPacket]:
    """Stream packets from a .pcap file one at a time.

    Use for very large captures that should not be fully loaded into RAM.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    with PcapReader(str(path)) as reader:
        for pkt in reader:
            yield pkt
```

### Step 2 — Round-Trip Test

Create `tests/test_pcap_io.py`:

```python
from pathlib import Path
import pytest
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from eps.core.pcap_io import write_pcap, read_pcap


def test_round_trip(tmp_path: Path):
    out = tmp_path / "test.pcap"
    pkts = [
        Ether() / IP(dst="1.2.3.4") / TCP(dport=80),
        Ether() / IP(dst="5.6.7.8") / TCP(dport=443),
    ]
    write_pcap(out, pkts)
    read_back = read_pcap(out)
    assert len(read_back) == 2
    assert read_back[0][IP].dst == "1.2.3.4"
    assert read_back[1][TCP].dport == 443


def test_read_real_capture():
    fixture = Path(__file__).parent / "fixtures" / "sample.pcap"
    pkts = read_pcap(fixture)
    assert len(pkts) > 0


def test_write_empty_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        write_pcap(tmp_path / "empty.pcap", [])
```

### Step 3 — Wireshark Interoperability Check (Manual)

Write a pcap with your tool, then open it in Wireshark. Confirm:

- All packets are present.
- Timestamps look correct.
- Protocols are dissected without errors.

Conversely, save a capture from Wireshark as `.pcap` (not pcapng — use "File > Export Specified Packets" with "Wireshark/tcpdump/... - pcap" as the file type). Open it with your tool. Confirm all packets parse without exceptions.

### Step 4 — Document Limitations

Add a note in `docs/architecture.md` (or create it):

> The current implementation reads both pcap and pcapng (via Scapy's `rdpcap`) but writes only classic pcap. Pcapng write support is planned for a future revision but is not in scope for the current project.

---

## Self-Administered Verification Gate

- [ ] `src/eps/core/pcap_io.py` exists with `write_pcap`, `read_pcap`, and `stream_pcap`.
- [ ] All three functions are covered by unit tests.
- [ ] A pcap file written by my tool opens successfully in Wireshark.
- [ ] A pcap file written by Wireshark opens successfully in my tool.
- [ ] No file in `src/eps/core/` imports PyQt6 (run grep to verify).
- [ ] Limitations are documented in `docs/architecture.md`.

Once all boxes are checked, you may begin Phase 4.
