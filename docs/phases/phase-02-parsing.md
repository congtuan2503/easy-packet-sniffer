# Phase 2 — Packet Parsing and Domain Object

**Estimated duration:** 1–2 weeks
**Prerequisite:** Phase 1 complete
**Outcome:** A `Packet` dataclass in `src/eps/core/packet.py`, a `parse()` function in `src/eps/core/parser.py`, and at least 10 passing unit tests in `tests/test_parser.py`. Optional rigorous track: a struct-based parser implemented from scratch.

---

## Relevant Knowledge

### Why a Domain Object Instead of the Scapy Packet?

Scapy returns rich, dynamically-typed packet objects that include parsing methods, serialization, and reflection. They are excellent for scripting, but unsuitable as the domain object passed across thread boundaries and into UI models because:

1. **They are mutable.** Mutability is hazardous when one thread produces and another consumes.
2. **They carry references to Scapy internals.** This couples the rest of your code to Scapy. If you later replace Scapy with raw sockets, the entire app must be rewritten.
3. **They are heavy.** A `Packet` instance for the UI only needs a dozen fields; the Scapy object is much larger.

The fix: convert each Scapy packet into a lightweight, **frozen** dataclass at the boundary of the core layer. Everything past that point manipulates only your own `Packet` type.

### Header Field Reference

You must know these by heart. They will be tested in code review.

#### Ethernet II Frame (14 bytes)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Destination MAC (6 bytes)                    |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Source MAC (6 bytes)                         |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         EtherType (2 bytes)   |   ...payload begins here
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Common EtherType values: `0x0800` IPv4, `0x86DD` IPv6, `0x0806` ARP, `0x8100` 802.1Q VLAN tag.

If EtherType is `0x8100`, the actual EtherType comes 4 bytes later (VLAN tag inserts 4 bytes). Handle this.

#### IPv4 Header (20 bytes minimum, up to 60 bytes with options)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|  IHL  |    DSCP   |ECN|         Total Length          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Identification        |Flags|     Fragment Offset     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time to Live |   Protocol    |        Header Checksum        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Source IP Address                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Destination IP Address                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Options (only if IHL > 5)        ...
```

Key fields for your parser:
- **IHL** (Internet Header Length, 4 bits): header size in 32-bit words. Multiply by 4 to get bytes. Normally 5 (= 20 bytes).
- **Protocol** (1 byte): identifies the L4 protocol. Common values: 6 = TCP, 17 = UDP, 1 = ICMP.
- **Source/Destination IP** (4 bytes each).

#### IPv6 Header (40 bytes, fixed)

Unlike IPv4, IPv6 has a fixed-size header. Optional extension headers chain via the Next Header field. For your parser, you need:
- **Next Header** (1 byte): same role as IPv4 Protocol.
- **Source/Destination address** (16 bytes each).

#### TCP Header (20 bytes minimum, up to 60 bytes with options)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Sequence Number                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Acknowledgment Number                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Off | Rsv |C|E|U|A|P|R|S|F|         Window Size               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Checksum             |        Urgent Pointer         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

The flags byte: from MSB to LSB: CWR, ECE, URG, ACK, PSH, RST, SYN, FIN. The three you care about most are SYN, ACK, FIN, RST, PSH.

#### UDP Header (8 bytes, fixed)

Source Port (2 B), Destination Port (2 B), Length (2 B), Checksum (2 B). That is all.

### Why `@dataclass(frozen=True)`

A frozen dataclass:

1. **Forbids mutation after construction.** Any thread receiving a `Packet` cannot accidentally corrupt it. This eliminates an entire class of concurrency bugs.
2. **Is hashable by default.** Useful when packets become keys in a dict (e.g., conversation tracking in Phase 8).
3. **Generates `__eq__` for free.** Useful in unit tests.

### `struct.unpack` for the Optional Track

Python's `struct` module reads binary data using format strings. Example for the Ethernet header:

```python
import struct

raw = b"\xff\xff\xff\xff\xff\xff" + b"\x00\x11\x22\x33\x44\x55" + b"\x08\x00" + ...
dst_mac, src_mac, ethertype = struct.unpack("!6s6sH", raw[:14])
```

The `!` prefix means network byte order (big-endian). `6s` is 6 bytes as a `bytes` object. `H` is an unsigned 16-bit integer.

If you complete the optional track, you will internalize the layout of every header far more deeply than Scapy ever forces you to.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| RFC 791 — Section 3.1 | IPv4 header diagram and field definitions |
| RFC 8200 — Section 3 | IPv6 header (fixed 40 bytes) |
| RFC 9293 — Section 3.1 | TCP header layout |
| RFC 768 | UDP — short, complete reference |
| [Python docs — dataclasses](https://docs.python.org/3/library/dataclasses.html) | Dataclass behaviors and options |
| [Python docs — struct module](https://docs.python.org/3/library/struct.html) | Binary parsing format strings |
| [Wireshark wiki — Ethernet](https://wiki.wireshark.org/Ethernet) | Layer 2 details, VLAN tagging |
| [Scapy docs — Adding a new layer](https://scapy.readthedocs.io/en/latest/build_dissect.html) | Useful for understanding how Scapy itself parses |

---

## Steps for Implementation

### Step 1 — Define the `Packet` Dataclass

Create `src/eps/core/packet.py` using the skeleton in `PROJECT_GUIDE.md` Section 6, Phase 2. Make sure `frozen=True` is set.

### Step 2 — Implement `parse()`

Create `src/eps/core/parser.py` using the skeleton in `PROJECT_GUIDE.md` Section 6, Phase 2. Handle these cases:

- Pure Ethernet frame with no IP (rare but possible: ARP, LLDP).
- IPv4 with TCP.
- IPv4 with UDP.
- IPv4 with ICMP (no ports).
- IPv6 with TCP.
- IPv6 with UDP.
- 802.1Q VLAN-tagged frames.

### Step 3 — Capture Test Fixtures

Open Wireshark (separately from your tool). Capture 30 seconds of mixed traffic. Save as `tests/fixtures/sample.pcap`. Ensure your capture contains at least:

- HTTP traffic (TCP port 80)
- DNS traffic (UDP port 53)
- An ICMP ping
- An ARP request
- Some HTTPS traffic (TCP port 443)

If your network does not produce some of these naturally, generate them:

```
ping 8.8.8.8
nslookup google.com
curl http://example.com
arp -d *      (clears ARP cache; next packet will trigger ARP)
```

### Step 4 — Write Unit Tests

Create `tests/test_parser.py`. At minimum, write tests that:

```python
import pytest
from pathlib import Path
from scapy.utils import rdpcap
from eps.core.parser import parse


FIXTURE = Path(__file__).parent / "fixtures" / "sample.pcap"


@pytest.fixture(scope="module")
def packets():
    return list(rdpcap(str(FIXTURE)))


def test_parse_returns_immutable_packet(packets):
    p = parse(packets[0])
    with pytest.raises(Exception):  # FrozenInstanceError or similar
        p.length = 999


def test_tcp_packet_has_ports(packets):
    tcp = next(p for p in packets if p.haslayer("TCP"))
    parsed = parse(tcp)
    assert parsed.src_port is not None
    assert parsed.dst_port is not None
    assert parsed.ip_proto == 6


# ... at least 8 more tests
```

Verify they pass:

```
pytest tests/test_parser.py -v
```

### Step 5 — Optional Rigorous Track: Raw `struct` Parser

If your schedule permits, create `src/eps/core/raw_parser.py` and implement parsing using only `struct.unpack`. Skip Scapy entirely. Read bytes from a `.pcap` file directly.

This is the segment that will most deeply teach you packet layout. It will also take significant time. Decide based on your schedule.

### Step 6 — Verify Architecture Boundary

Run:

```
grep -r "PyQt6" src/eps/core/
```

Must produce zero results. The core layer has no business knowing about Qt.

Also verify tests run without PyQt6 importable. Temporarily uninstall PyQt6 if you want to be paranoid:

```
pip uninstall PyQt6
pytest tests/test_parser.py        # should still pass
pip install "PyQt6>=6.8,<7.0"      # reinstall
```

---

## Self-Administered Verification Gate

- [ ] `src/eps/core/packet.py` defines a frozen dataclass with all required fields.
- [ ] `src/eps/core/parser.py` correctly handles IPv4-TCP, IPv4-UDP, IPv6-TCP, ARP, ICMP, and VLAN-tagged frames.
- [ ] `tests/test_parser.py` contains at least 10 passing tests.
- [ ] Tests pass with PyQt6 uninstalled (proof of decoupling).
- [ ] No file in `src/eps/core/` imports PyQt6.
- [ ] I can, on paper, identify every field of an Ethernet + IPv4 + TCP packet from a hex dump.

Once all boxes are checked, you may begin Phase 3.
