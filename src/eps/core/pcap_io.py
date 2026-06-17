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
