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
    engine.set_packet_callback(lambda p: print(f"Captured: {p.summary()}")) #debugging
    engine.start()
    try:
        time.sleep(duration)
    finally:
        stats = engine.stop()
    print(f"\n[stats] {stats}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))