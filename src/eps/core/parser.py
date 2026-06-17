from __future__ import annotations
from scapy.packet import Packet as ScapyPacket
from scapy.layers.l2 import Ether, ARP, Dot1Q
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.inet6 import IPv6
from scapy.contrib.lldp import LLDPDU
from .packet import Packet

def parse(scapy_pkt: ScapyPacket) -> Packet:
    """Convert a Scapy packet into a frozen domain Packet."""
    ts = float(scapy_pkt.time)
    raw = bytes(scapy_pkt)
    length = len(raw)

    src_mac = dst_mac = ethertype = None
    src_ip = dst_ip = ip_proto = None
    src_port = dst_port = tcp_flags = None
    
    # LAYER 2: Ethernet
    if Ether in scapy_pkt:
        eth = scapy_pkt[Ether]
        src_mac, dst_mac = eth.src, eth.dst
        ethertype = eth.type
    
    # LAYER 2.5: VLAN (802.1Q)
    if Dot1Q in scapy_pkt:
        vlan = scapy_pkt[Dot1Q]
        ethertype = vlan.type

    # LAYER 2/3: ARP (Trường hợp đặc biệt)
    if ARP in scapy_pkt:
        arp = scapy_pkt[ARP]
        src_ip, dst_ip = arp.psrc, arp.pdst
        ip_proto = None
        # ARP không có ip_proto (nó là protocol riêng ở L2)

    # LAYER 3: IP   
    if IP in scapy_pkt:
        ip = scapy_pkt[IP]
        src_ip, dst_ip, ip_proto = ip.src, ip.dst, ip.proto
    elif IPv6 in scapy_pkt:
        ip6 = scapy_pkt[IPv6]
        src_ip, dst_ip, ip_proto = ip6.src, ip6.dst, ip6.nh

    # LAYER 4: TCP / UDP / ICMP (ICMP lấy proto từ L3)
    if TCP in scapy_pkt:
        tcp = scapy_pkt[TCP]
        src_port, dst_port = int(tcp.sport), int(tcp.dport)
        tcp_flags = str(tcp.flags)

    elif UDP in scapy_pkt:
        udp = scapy_pkt[UDP]
        src_port, dst_port = int(udp.sport), int(udp.dport)
    
    # Đối với ICMP, ta đã có ip_proto = 1 từ layer IP,
    # và src_port/dst_port sẽ mặc định là None -> ĐÚNG bản chất.
    
    return Packet(
        ts=ts, src_mac=src_mac, dst_mac=dst_mac, ethertype=ethertype,
        src_ip=src_ip, dst_ip=dst_ip, ip_proto=ip_proto,
        src_port=src_port, dst_port=dst_port, tcp_flags=tcp_flags,
        length=length, summary=scapy_pkt.summary(), raw=raw,
    )


