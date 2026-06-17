# Phase 0 — Foundations and Environment Setup

**Estimated duration:** 1 week
**Prerequisite:** None
**Outcome:** Working Python + Scapy + PyQt6 environment on Windows, project scaffold committed to git, and a verified live capture from the command line.

---

## Relevant Knowledge

### The TCP/IP Layered Model

Network protocols are organized in layers. Each layer encapsulates the layer above it by prepending its own header. On the wire, the order is:

```
+-----------------------------------------------------------+
| Ethernet header | IPv4 header | TCP header | Application  |
|     (L2)        |    (L3)     |    (L4)    |    Payload   |
|    14 bytes     |  20+ bytes  | 20+ bytes  |   (variable) |
+-----------------------------------------------------------+
```

When you sniff packets, you receive the **outermost** layer first (Ethernet) and parse inward. This is the correct mental model. The reverse (application data on the outside) is wrong.

| Layer | Name | Role | Examples |
|---|---|---|---|
| 1 | Physical | Voltages, light, radio | Cat-6 cable, fiber |
| 2 | Data Link | Frames, MAC addressing | Ethernet, Wi-Fi (802.11) |
| 3 | Network | Packets, routing | IPv4, IPv6, ICMP |
| 4 | Transport | Connections, ports | TCP, UDP |
| 7 | Application | Service semantics | HTTP, DNS, TLS |

(L5 and L6 are session and presentation in the OSI model; they are largely absorbed into L7 in practice.)

### Python Virtual Environments

A virtual environment is an isolated Python installation with its own `site-packages`. It prevents project dependencies from polluting your system Python. Activate it before installing or running anything project-related. Without it, you will eventually break your system Python or be unable to reproduce your build on another machine.

### `pyproject.toml`

The modern Python project configuration file (PEP 621). Replaces `setup.py` and `setup.cfg`. Declares dependencies, build system, scripts, and tool configurations in one place.

### Why Administrator on Windows

Raw packet capture requires direct access to the network driver. The Windows kernel restricts this to privileged processes. Npcap is the driver that mediates this access; even with Npcap installed, the calling process must run as Administrator.

### Npcap and "WinPcap API-compatible Mode"

Npcap is the modern successor to WinPcap on Windows. Scapy expects the WinPcap-compatible API. During Npcap installation, you must check the "Install Npcap in WinPcap API-compatible Mode" option, or Scapy will fail to find network interfaces.

---

## Resources for Learning and Research

| Resource | Scope | Time |
|---|---|---|
| Kurose & Ross, *Computer Networking: A Top-Down Approach*, Ch. 1.5 | Protocol layers, encapsulation | 1 hour |
| Kurose & Ross, Ch. 4.3 | IPv4 header in depth | 1 hour |
| RFC 791 (header section only) | Authoritative IPv4 header reference | 30 min skim |
| RFC 9293 (sections 3.1 and 3.4) | TCP header and connection establishment | 1 hour |
| [Python docs — venv module](https://docs.python.org/3/library/venv.html) | Virtual environment basics | 15 min |
| [Python Packaging User Guide — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) | Modern Python project config | 30 min |
| [Npcap documentation](https://npcap.com/guide/) | Installation and modes | 15 min |
| [Scapy quickstart](https://scapy.readthedocs.io/en/latest/usage.html) | First contact with the library | 30 min |

---

## Steps for Implementation

### Step 1 — Verify Python and Npcap

```
python --version
```

Expected: Python 3.13 or newer. If older, install from [python.org](https://www.python.org/downloads/).

Confirm Npcap is installed in WinPcap API-compatible Mode. If not, reinstall from [npcap.com](https://npcap.com/) with the correct checkbox enabled.

### Step 2 — Create Project Directory Tree

Create exactly this structure at the project root:

```
easy-packet-sniffer/
├── pyproject.toml
├── README.md
├── PROJECT_GUIDE.md          (already exists)
├── .gitignore
├── src/
│   └── eps/
│       ├── __init__.py
│       ├── core/
│       │   └── __init__.py
│       ├── controllers/
│       │   └── __init__.py
│       └── ui/
│           └── __init__.py
├── tests/
│   ├── __init__.py
│   └── fixtures/
├── scripts/
├── docs/
└── .venv/                    (created in step 4)
```

All `__init__.py` files should be empty for now.

### Step 3 — Write `.gitignore`

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.pcap
*.pcapng
dist/
build/
*.egg-info/
.vscode/
.idea/
```

### Step 4 — Initialize Virtual Environment

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

### Step 5 — Write `pyproject.toml`

Copy the template from `PROJECT_GUIDE.md` Section 7. Save as `pyproject.toml` in the project root.

### Step 6 — Install Dependencies

```
pip install -e ".[dev]"
```

The `-e` flag installs the project in editable mode, so changes to your source are immediately reflected without reinstalling.

### Step 7 — Verify Capture

**Open a terminal as Administrator** (right-click the terminal icon, "Run as Administrator"), then activate the venv again in the Administrator terminal:

```
cd "C:\Users\luaho\Documents\GitHub\Easy Packet Sniffer"
.venv\Scripts\activate
python -c "from scapy.all import sniff; sniff(iface='Wi-Fi', count=20, timeout=20, prn=lambda p: print(p.summary()))"
```

The command should hang briefly, capture 3 packets, print their summaries, and exit. If you see no output, generate traffic by opening a browser or pinging a host in another window.

**If this fails:**
- Error mentions "no libpcap" → Npcap not installed or not in WinPcap mode.
- Error mentions permissions → terminal not running as Administrator.
- Hangs forever → no traffic on the default interface; try generating some.

### Step 8 — Initialize Git Repository

```
git init
git add .
git commit -m "Phase 0: project scaffold and environment setup"
```

### Step 9 — Begin Reading List

Start the mandatory reading from `PROJECT_GUIDE.md` Section 9. You should complete it before writing Phase 1 code.

---

## Self-Administered Verification Gate

Before proceeding to Phase 1, confirm all of the following are true. If any are false, the phase is incomplete.

- [ ] The directory tree matches Section 5 of `PROJECT_GUIDE.md` exactly.
- [ ] `.venv` exists and `pip list` inside it shows `scapy`, `PyQt6`, and `pytest`.
- [ ] The Scapy one-liner printed 3 packet summaries.
- [ ] The git repo is initialized and the scaffold is committed.
- [ ] I can draw the encapsulation diagram (`[Ether | IP | TCP | Payload]`) from memory.
- [ ] I can list the three TCP handshake flags from memory (`[S]`, `[S.]`, `[.]`).
- [ ] I have completed at least Kurose & Ross Ch. 1.5 from the reading list.

Once all boxes are checked, you may begin Phase 1.
