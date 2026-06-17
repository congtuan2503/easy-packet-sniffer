# Easy Packet Sniffer

Easy Packet Sniffer is a professional, Wireshark-style network packet analyzer built using Python, PyQt6, and Scapy. Designed as a high-fidelity desktop application, it showcases enterprise-grade software architecture, strict multi-layered separation of concerns, and clean concurrency patterns.

This application is built as a portfolio artifact demonstrating robust software engineering principles, decoupled domain logic, and high-performance network analysis on Windows environments.

## Core Architectural Design

The codebase enforces a strict Model-View-Controller (MVC) architecture with clear boundaries between the graphical interface, controller orchestration, and core packet-processing logic:

* **Domain / Core Layer (`eps.core`):** Contains zero dependencies on UI frameworks (PyQt6). It manages the background capture engine, protocol parsers, and PCAP persistence. All data representations are compiled into frozen, immutable domain objects to guarantee thread safety across boundaries.
* **Application / Controller Layer (`eps.controllers`):** Manages worker threads, coordinates asynchronous events, and bridges the core domain layer to the presentation layer using thread-safe Qt Signal/Slot communication.
* **Presentation / View Layer (`eps.ui`):** Implements code-driven PyQt6 widgets. It uses a virtualized `QAbstractTableModel` to update visual components in real-time, allowing the UI to remain highly responsive under heavy packet loads.

```
+============================================================+
|                  PRESENTATION LAYER (View)                 |
|                       PyQt6 widgets                        |
|                                                            |
|  MainWindow, PacketTableView, HexDumpView, etc.            |
+============================================================+
               ^                                  |
               | Qt Signals                       | UI Events
               | (PacketCaptured, ErrorRaised)    | (e.g., Clicked)
               |                                  v
+============================================================+
|              APPLICATION LAYER (Controller)                |
|                                                            |
|  CaptureController (bridges worker thread to GUI)          |
+============================================================+
               ^                                  |
               | Thread-safe Queue / Callback     | Commands
               |                                  v
+============================================================+
|                    DOMAIN / CORE LAYER (Model)             |
|                                                            |
|  CaptureEngine (sniff loop) | Parser | PcapIO | Filters    |
+============================================================+
```

## Features

* **Asynchronous Live Capture:** Interface-specific packet capture operating on a background thread utilizing Scapy's `AsyncSniffer` with WinPcap/Npcap integration.
* **Immutability Enforcement:** Captured packets are immediately mapped to frozen Python dataclasses (`eps.core.packet.Packet`) to prevent data corruption during multi-threaded dispatching.
* **Multi-Protocol Dissection:**
  * **Layer 2 (Data Link):** Ethernet II, IEEE 802.1Q VLAN tags.
  * **Layer 2/3:** Address Resolution Protocol (ARP).
  * **Layer 3 (Network):** IPv4 (with IHL offsets), IPv6.
  * **Layer 4 (Transport):** TCP (with full TCP flag mapping), UDP.
  * **Layer 4/7 (Application / Control):** ICMP, LLDP, DNS, HTTP, HTTPS.
* **Wireshark Interoperability:** Implements standard PCAP reading/writing interfaces.
* **Decoupled Architecture Verification:** Strictly enforced via build-time import analysis. The domain core can be run and tested in fully headless environments.

## Directory Structure

```
easy-packet-sniffer/
├── pyproject.toml              # Project configuration and dependencies
├── README.md                   # Project documentation
├── PROJECT_GUIDE.md            # Internal development guide and status
├── src/
│   └── eps/
│       ├── __init__.py
│       ├── core/               # Domain/Model layer (No PyQt6 imports allowed)
│       │   ├── __init__.py
│       │   ├── capture_engine.py
│       │   ├── packet.py
│       │   ├── parser.py
│       │   ├── pcap_io.py
│       │   └── filters.py
│       ├── controllers/        # Application/Controller layer (Qt signals only)
│       │   ├── __init__.py
│       │   └── capture_controller.py
│       ├── ui/                 # Presentation/View layer (PyQt6 widgets)
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   └── packet_table.py
│       └── main.py             # Main application entry point
├── tests/
│   ├── test_parser.py          # Decoupled domain unit tests
│   └── fixtures/
│       └── sample.pcap
└── scripts/
    └── cli_capture.py          # Standalone CLI capture driver for diagnostic use
```

## Setup & Installation

### Prerequisites

* **OS:** Windows 11 (primary target).
* **Python:** 3.13 or newer (tested on 3.14.2).
* **Npcap:** Must be installed in **WinPcap API-compatible Mode** to enable Scapy raw driver bindings on Windows.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/congtuan2503/easy-packet-sniffer.git
   cd easy-packet-sniffer
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install the package and its development dependencies in editable mode:
   ```bash
   pip install -e .[dev]
   ```

## Usage

### Command Line Diagnostics

You can run the terminal-based capture engine diagnostic utility to test the interface drivers and capture loop:

```bash
# Usage: python scripts/cli_capture.py [interface] [bpf_filter] [duration_seconds]
python scripts/cli_capture.py "Wi-Fi" "tcp port 443" 15
```

### Running Graphical UI (Upcoming Phase 5)

Once the GUI components are integrated, run the main entry point:

```bash
python -m eps.main
```

## Running Quality Checks

### Headless Unit Tests

To verify domain-layer packet parsing and immutability guarantees without initiating GUI subsystems:

```bash
pytest tests/ -v
```

### Architecture Dependency Linting

The system enforces architectural rules using `import-linter`. This guarantees that core domain components never import graphical elements.

```bash
# Execute the dependency boundaries check
lint-imports
```

## Project Development Roadmap

This project is developed in 10 sequential phases:

* **Phase 0: Scaffold & Setup** - Environment calibration, repository layout, dependency constraints configuration. (Completed)
* **Phase 1: Terminal Capture Loop** - Asynchronous sniffing loop, callbacks, and low-level engine control. (Completed)
* **Phase 2: Packet Parsing** - Domain object mapping, immutability implementation, and protocol parsers. (Completed)
* **Phase 3: Persistence** - Read/write logic for PCAP file format round-tripping with Wireshark. (Upcoming)
* **Phase 4: Threading & Controller** - Producer-consumer architecture, crossing PyQt6 event boundary safely. (Upcoming)
* **Phase 5: Minimum Viable UI** - Triple-pane design, virtualized table rendering. (Upcoming)
* **Phase 6: Detail Tree & Hex View** - Hierarchical dissecting tree and visual hex memory dump. (Upcoming)
* **Phase 7: Dynamic Filtering** - BPF capture-time filters and display-time query filters. (Upcoming)
* **Phase 8: Statistics & Analytics** - Conversation talkers, band usage, protocol statistics. (Upcoming)
* **Phase 9: Production Hygiene** - Standard logging framework, config management, PyInstaller compilation. (Upcoming)
* **Phase 10: Portfolio Presentation** - Architectural write-up, performance documentation, performance benchmarks. (Upcoming)

## License

This project is open-source software licensed under the MIT License.
