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
    assert read_back[1][IP].dst == "5.6.7.8"
    assert read_back[0][TCP].dport == 80
    assert read_back[1][TCP].dport == 443

def test_read_real_capture():
    fixture = Path(__file__).parent / "fixtures" / "sample.pcap"
    pkts = read_pcap(fixture)
    assert len(pkts) > 0

def test_write_empty_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        write_pcap(tmp_path / "empty.pcap", [])