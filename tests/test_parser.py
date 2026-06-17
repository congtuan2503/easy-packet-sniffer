import pytest
from typing import Any, cast
from scapy.layers.l2 import Ether, ARP, Dot1Q
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.inet6 import IPv6
from scapy.contrib.lldp import LLDPDU, LLDPDUChassisID, LLDPDUPortID, LLDPDUEndOfLLDPDU
from eps.core.parser import parse

def test_parse_ethernet_basic():
    """Verify basic Ethernet L2 field extraction."""
    pkt = Ether(src="aa:bb:cc:dd:ee:ff", dst="11:22:33:44:55:66", type=0x0800)
    parsed = parse(pkt)
    
    assert parsed.src_mac == "aa:bb:cc:dd:ee:ff"
    assert parsed.dst_mac == "11:22:33:44:55:66"
    assert parsed.ethertype == 0x0800

def test_parse_ipv4_tcp():
    """Verify IPv4 and TCP L3/L4 field extraction and flag parsing."""
    pkt = Ether()/IP(src="1.1.1.1", dst="2.2.2.2")/TCP(sport=1234, dport=80, flags="SA")
    parsed = parse(pkt)
    
    assert parsed.src_ip == "1.1.1.1"
    assert parsed.dst_ip == "2.2.2.2"
    assert parsed.ip_proto == 6
    assert parsed.src_port == 1234
    assert parsed.dst_port == 80
    assert parsed.tcp_flags is not None
    assert "S" in parsed.tcp_flags
    assert "A" in parsed.tcp_flags

def test_parse_ipv4_udp():
    """Verify UDP field extraction and absence of TCP-specific flags."""
    pkt = Ether()/IP(src="192.168.1.1", dst="8.8.8.8")/UDP(sport=53535, dport=53)
    parsed = parse(pkt)
    
    assert parsed.src_port == 53535
    assert parsed.dst_port == 53
    assert parsed.ip_proto == 17
    assert parsed.tcp_flags is None

def test_parse_ipv6_tcp():
    """Verify IPv6 header handling."""
    pkt = Ether()/IPv6(src="2001:db8::1", dst="2001:db8::2")/TCP(sport=443, dport=54321)
    parsed = parse(pkt)
    
    assert parsed.src_ip == "2001:db8::1"
    assert parsed.dst_ip == "2001:db8::2"
    assert parsed.ip_proto == 6
    assert parsed.src_port == 443

def test_parse_arp():
    """Verify ARP psrc/pdst extraction which bypasses standard IP layers."""
    pkt = Ether()/ARP(psrc="192.168.1.1", pdst="192.168.1.5")
    parsed = parse(pkt)
    
    assert parsed.src_ip == "192.168.1.1"
    assert parsed.dst_ip == "192.168.1.5"
    assert parsed.ip_proto is None

def test_parse_icmp():
    """Verify ICMP identification via the IP protocol field."""
    pkt = Ether()/IP(src="10.0.0.1", dst="10.0.0.2")/ICMP()
    parsed = parse(pkt)
    
    assert parsed.ip_proto == 1
    assert parsed.src_ip == "10.0.0.1"
    assert parsed.dst_ip == "10.0.0.2"
    assert parsed.src_port is None
    assert parsed.dst_port is None

def test_parse_vlan_tagged_packet():
    """Verify that the parser correctly extracts the internal ethertype from Dot1Q."""
    pkt = Ether()/Dot1Q(vlan=10, type=0x0800)/IP()
    parsed = parse(pkt)
    
    assert parsed.ethertype == 0x0800

def test_parse_lldp():
    """Verify basic recognition of LLDP frames."""
    pkt = (Ether(dst="01:80:c2:00:00:0e", type=0x88cc) / 
           LLDPDU() / 
           LLDPDUChassisID(subtype=4, id="00:11:22:33:44:55") / 
           LLDPDUPortID(subtype=7, id="eth0") / 
           LLDPDUEndOfLLDPDU())
    parsed = parse(pkt)
    
    assert parsed.ethertype == 0x88cc
    assert "LLDP" in parsed.summary

def test_packet_immutability():
    """Verify that the domain object is frozen and prevents runtime modifications."""
    pkt = Ether()/IP()
    parsed = parse(pkt)
    
    with pytest.raises(Exception):
        # We cast to Any to bypass static type checking for the purpose of this test
        cast(Any, parsed).length = 9999
