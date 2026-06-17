# Phase 1 — Terminal Capture Loop

**Estimated duration:** 1 week
**Prerequisite:** Phase 0 complete
**Outcome:** A working `CaptureEngine` class in `src/eps/core/capture_engine.py` and a CLI driver script in `scripts/cli_capture.py` that captures live packets and prints them to stdout.

---

## Relevant Knowledge

### What is BPF?

**BPF** stands for **Berkeley Packet Filter**. It is a tiny virtual machine inside the kernel that runs a small bytecode program against every incoming packet and decides whether to pass it to user space.

You write BPF filters in a high-level syntax (the "pcap-filter" syntax) like `tcp port 443`, and libpcap compiles it to BPF bytecode. The kernel then runs the bytecode per-packet. This is critical for performance: filtering 1 million packets/second in the kernel costs nothing extra; filtering in Python would consume your entire CPU.

Common BPF filter examples:

| Filter | Meaning |
|---|---|
| `tcp` | All TCP packets |
| `udp port 53` | DNS traffic |
| `host 8.8.8.8` | Anything to or from 8.8.8.8 |
| `tcp port 443 and host 1.2.3.4` | HTTPS to/from 1.2.3.4 |
| `not arp` | Everything except ARP |
| `icmp` | Ping traffic |
| `ether host 00:11:22:33:44:55` | By MAC address |

### Scapy `sniff` vs `AsyncSniffer`

| API | Behavior | Use case |
|---|---|---|
| `sniff(...)` | Blocks the calling thread until done or count reached | Quick scripts, not GUI |
| `AsyncSniffer(...).start()` | Returns immediately; spawns its own thread; runs until `.stop()` | What we use |

We use `AsyncSniffer` because the GUI will need to call `stop()` from the main thread while capture continues in the background.

### Promiscuous Mode

By default a network card discards frames not addressed to its own MAC address. **Promiscuous mode** disables this filter, letting the NIC see every frame on the local segment. On modern switched networks this only shows you traffic involving your own machine (because switches do not flood traffic to all ports), but it is still essential to capture broadcast and multicast traffic correctly.

Scapy's `sniff` enables promiscuous mode by default. You can disable it via the `promisc` argument if needed.

### The Callback Pattern (`prn=`)

Instead of accumulating packets in a list (which is wasteful for long captures), Scapy lets you pass a callback function via the `prn` argument. The callback is invoked once per captured packet, in Scapy's worker thread. This is a **producer**; later you will pair it with a consumer (the UI).

Combined with `store=False`, this prevents Scapy from retaining captured packets in memory. Without `store=False`, a 30-minute capture can exhaust RAM.

### Drop Counters

When traffic arrives faster than your callback can process it, the kernel ring buffer fills up and the kernel drops packets. **A capture with non-zero drops is incomplete by definition.** You must always check the drop counter at the end of a capture before trusting the data.

Scapy exposes this through the underlying socket's statistics method.

---

## Resources for Learning and Research

| Resource | Scope |
|---|---|
| [Scapy documentation — Sniffing](https://scapy.readthedocs.io/en/latest/usage.html#sniffing) | Official guide to `sniff` and `AsyncSniffer` |
| [tcpdump pcap-filter(7) man page](https://www.tcpdump.org/manpages/pcap-filter.7.html) | The authoritative BPF filter syntax reference |
| [Wireshark wiki — Capture Filters](https://wiki.wireshark.org/CaptureFilters) | Practical BPF examples |
| [Steven McCanne and Van Jacobson, "The BSD Packet Filter" (1993)](https://www.tcpdump.org/papers/bpf-usenix93.pdf) | The original BPF paper (optional, but illuminating) |
| Scapy source: `scapy/sendrecv.py` | Read the `AsyncSniffer` class to understand what we are wrapping |

---

## Steps for Implementation

### Step 1 — Skeleton `CaptureEngine`

Create `src/eps/core/capture_engine.py` with the skeleton from `PROJECT_GUIDE.md` Section 6, Phase 1. Read every line and make sure you understand it before continuing.

### Step 2 — Add Interface Enumeration

The user must select which network interface to capture on. Add a helper:

```python
from scapy.arch import get_if_list

def list_interfaces() -> list[str]:
    """Return available network interface names."""
    return get_if_list()
```

On Windows, interface names look like GUIDs (e.g., `\\Device\\NPF_{ABCD-1234}`). Scapy also exposes friendly names via `scapy.arch.windows.get_windows_if_list()`. Investigate both and decide which to surface to the user later.

### Step 3 — Robust Error Handling

`CaptureEngine.start()` must handle:

- Interface not found.
- BPF filter syntax invalid.
- Insufficient privileges (no Administrator).
- Already-running capture (double start).

Raise specific exceptions or use the `error_raised` signal mechanism that will be added in Phase 4. For now, raise plain `RuntimeError` with a clear message.

### Step 4 — Drop Counter Access

After calling `.stop()`, read the drop counter and include it in the returned statistics. Investigate `AsyncSniffer.results` and the underlying socket (`AsyncSniffer.sock`) to find the right method. Scapy's `L2ListenSocket` exposes `get_stats()` on some platforms.

Document what you find in a comment.

### Step 5 — CLI Driver Script

Create `scripts/cli_capture.py`:

```python
"""Phase 1 throwaway driver: dump packets to stdout for N seconds."""
from __future__ import annotations
import sys
import time
from eps.core.capture_engine import CaptureEngine


def main(argv: list[str]) -> int:
    iface = argv[1] if len(argv) > 1 else None
    bpf = argv[2] if len(argv) > 2 else ""
    duration = int(argv[3]) if len(argv) > 3 else 10

    engine = CaptureEngine(iface=iface, bpf_filter=bpf)
    engine.set_packet_callback(lambda p: print(p.summary()))
    engine.start()
    try:
        time.sleep(duration)
    finally:
        stats = engine.stop()
    print(f"\n[stats] {stats}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### Step 6 — Test the CLI Driver

Run in an Administrator terminal:

```
python scripts/cli_capture.py
python scripts/cli_capture.py "" "tcp"
python scripts/cli_capture.py "" "udp port 53" 30
```

Generate traffic in another window (browse a website, run `ping 8.8.8.8`, run `nslookup google.com`).

### Step 7 — Document Behavior in `docs/`

Create `docs/capture-engine.md` and write 1–2 paragraphs explaining:

- What `CaptureEngine` does.
- Why `store=False` is set.
- Why the callback runs in a background thread.

Writing this documentation now will help you in Phase 4 when the threading discussion arrives.

---

## Self-Administered Verification Gate

- [ ] `src/eps/core/capture_engine.py` exists and contains a working `CaptureEngine` class.
- [ ] `scripts/cli_capture.py` runs and prints packet summaries from an Administrator terminal.
- [ ] At least three different BPF filters have been tested (`tcp`, `udp port 53`, and one of your own).
- [ ] `CaptureEngine` does not import anything from `PyQt6`. Verify with `grep -ri "PyQt6" src/eps/core/` — must return zero hits.
- [ ] The drop counter is accessible via the returned statistics dictionary.
- [ ] You can explain in writing why `store=False` is correct.

Once all boxes are checked, you may begin Phase 2.
