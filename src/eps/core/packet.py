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
    raw: bytes       