from __future__ import annotations
from typing import Callable, Optional
from scapy.all import AsyncSniffer
from scapy.packet import Packet as ScapyPacket
from scapy.arch import get_if_list

class CaptureEngine:
    """Thread-managed packet capture using Scapy's AsyncSniffer.

    Domain-layer class. Forbidden from importing anything from PyQt6.
    """

    def __init__(self, iface: str | None = None, bpf_filter: str = "") -> None:
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

    def stop(self) -> dict[str,int]:
        if self._sniffer is None:
            raise RuntimeError("Capture not running")
        results = self._sniffer.stop()
        stats = {
            "captured": len(results) if results else 0,
            # Scapy exposes drop counters via the underlying socket
        }
        self._sniffer = None
        return stats
    
def list_interface() -> list[str]:
    return get_if_list()

