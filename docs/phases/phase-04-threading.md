# Phase 4 — Threading and the Controller

**Estimated duration:** 1 week
**Prerequisite:** Phase 3 complete
**Outcome:** A `CaptureController` class in `src/eps/controllers/capture_controller.py` that runs the capture engine in a worker thread and emits Qt signals on the main thread. `import-linter` configured to enforce architectural boundaries.

---

## Relevant Knowledge

### The Global Interpreter Lock (GIL) — Read This Carefully

The GIL is a mutex in CPython (the standard Python implementation) that allows **only one thread at a time** to execute Python bytecode. This means Python threads cannot achieve true CPU parallelism for pure-Python computation.

**However:**

1. The GIL is **released** during blocking I/O operations (file I/O, network I/O, sleeping). While one thread waits on a network read, another thread can run Python code.
2. The GIL is **released** when calling into C extensions that explicitly release it (NumPy, libpcap-via-Scapy, etc.).
3. Therefore: **for I/O-bound workloads, Python threading is genuinely useful.**

Packet capture is I/O-bound. The capture thread spends almost all its time blocked in a kernel `recv` call. Releasing the GIL during that wait lets the UI thread run smoothly. This is exactly the regime where Python threading wins.

For CPU-bound workloads, use `multiprocessing` or a C extension. Not relevant here.

### `threading.Thread` and `queue.Queue`

- `threading.Thread(target=fn).start()` spawns a thread running `fn`.
- `queue.Queue` is a thread-safe FIFO. `put()` and `get()` are atomic. This is the standard producer-consumer pipeline.

For this project we will not use `queue.Queue` directly — Qt's signal system replaces it — but understanding it is essential for the conceptual model.

### Qt's Threading Model — The Cardinal Rule

**Qt GUI objects (widgets) are not thread-safe.** Only the main thread (the one that called `QApplication(...)`) may create, modify, or delete GUI widgets. Touching a `QWidget` from a worker thread is undefined behavior — sometimes it works, sometimes it crashes.

To cross thread boundaries safely, Qt provides **signals and slots with queued connections**. When a signal is emitted from thread A and connected to a slot in thread B, Qt's event system serializes the call and dispatches it on B's event loop. The emit is fire-and-forget; the slot runs later, on the receiving thread.

This is the mechanism that lets `CaptureController` receive packets in Scapy's worker thread and safely deliver them to a `QTableView` model on the main thread.

### `QObject`, `pyqtSignal`, and `QThread`

- A class that wants to emit signals must inherit `QObject`.
- A signal is declared as a class attribute: `packet_received = pyqtSignal(object)`.
- The argument(s) to `pyqtSignal(...)` declare the types the signal carries. `object` accepts any Python object.
- `QThread` is Qt's thread wrapper; it integrates with Qt's event loop. For our use case (the worker thread is owned by Scapy's `AsyncSniffer`, not by us), we do **not** need a `QThread` ourselves. Scapy spawns its own `threading.Thread`. We only need a `QObject`-derived class to host the signals.

### Why Not `queue.Queue` + `QTimer`?

An older pattern was: producer pushes into a `queue.Queue`, then the UI uses a `QTimer.singleShot(0, ...)` or a polling timer to drain the queue. This works, but `pyqtSignal` with queued connections does the same job at lower latency and with less code. Use signals.

### `import-linter` — The Architecture Enforcer

`import-linter` runs as a CI/local check that fails the build when import contracts are violated. Two contracts matter for this project:

1. **`eps.core` may not import from `PyQt6`.** Ever.
2. **`eps.controllers` may not import from `PyQt6.QtWidgets`** (it may import from `PyQt6.QtCore` for signals).

The configuration was already declared in `PROJECT_GUIDE.md` Section 7. This phase is where you actually run it.

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [Python docs — threading module](https://docs.python.org/3/library/threading.html) | Thread API |
| [Python docs — queue module](https://docs.python.org/3/library/queue.html) | Thread-safe queues |
| [Real Python — "What Is the Python GIL?"](https://realpython.com/python-gil/) | Practical GIL explanation |
| [Qt for Python — Threading basics](https://doc.qt.io/qtforpython-6/overviews/thread-basics.html) | Qt's threading model |
| [Qt — Signals and Slots across threads](https://doc.qt.io/qt-6/threads-qobject.html) | The mechanism we rely on |
| [import-linter docs](https://import-linter.readthedocs.io/) | Configuration reference |
| Anthony Shaw, *CPython Internals* (No Starch Press) | Optional — deep dive on the GIL |

---

## Steps for Implementation

### Step 1 — Install `import-linter` and Verify Pre-Phase

```
pip install "import-linter>=2.0,<3.0"
lint-imports
```

This should pass currently (no PyQt6 imports anywhere in `src/eps/core/` yet — verify).

### Step 2 — Implement `CaptureController`

Create `src/eps/controllers/__init__.py` (empty) and `src/eps/controllers/capture_controller.py`. Use the skeleton from `PROJECT_GUIDE.md` Section 6, Phase 4. Key points:

- It inherits `QObject`.
- It declares three `pyqtSignal`s: `packet_received(object)`, `capture_stopped(dict)`, `error_raised(str)`.
- The Scapy callback runs in Scapy's worker thread. When it calls `self.packet_received.emit(parse(scapy_pkt))`, Qt automatically queues the signal for the main thread (because the receiver lives on the main thread).
- Exceptions in the parser are caught and surfaced via `error_raised` rather than killing the worker thread.

### Step 3 — Smoke Test the Controller

Create `scripts/qt_smoke_test.py`:

```python
"""Phase 4 smoke test: verify packets arrive on the main thread."""
from __future__ import annotations
import sys
from PyQt6.QtCore import QCoreApplication, QTimer
from eps.controllers.capture_controller import CaptureController


def main():
    app = QCoreApplication(sys.argv)
    controller = CaptureController()

    def on_packet(pkt):
        print(f"[main thread] received: {pkt.summary}")

    def on_stop(stats):
        print(f"[main thread] stopped: {stats}")
        app.quit()

    controller.packet_received.connect(on_packet)
    controller.capture_stopped.connect(on_stop)
    controller.error_raised.connect(lambda msg: print(f"ERROR: {msg}"))

    controller.start(iface=None, bpf_filter="")
    QTimer.singleShot(10_000, controller.stop)  # stop after 10s
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Run from an Administrator terminal. You should see packets printed for 10 seconds, then a clean shutdown. The "[main thread]" tag is for your own reassurance — Qt's signal system already guarantees it.

### Step 4 — Demonstrate Cross-Thread Safety (Optional Exercise)

To prove to yourself that Qt is doing the cross-thread dispatch correctly, add this to the controller's `_on_packet`:

```python
import threading
def _on_packet(self, scapy_pkt) -> None:
    print(f"[worker thread {threading.get_ident()}] producing packet")
    self.packet_received.emit(parse(scapy_pkt))
```

And in the smoke test's `on_packet`:

```python
def on_packet(pkt):
    print(f"[consumer thread {threading.get_ident()}] received packet")
```

You will see two different thread IDs. This is the proof.

### Step 5 — Run `import-linter`

```
lint-imports
```

If you accidentally added a PyQt6 import to `eps.core`, the linter will fail and tell you which line. Fix and re-run until clean.

### Step 6 — Add a `pytest` Test for the Controller (Without Real Capture)

You cannot reliably unit-test live packet capture (it depends on the environment). But you can test the controller's signal wiring with a mock engine:

```python
# tests/test_capture_controller.py
from unittest.mock import MagicMock
from PyQt6.QtCore import QCoreApplication
from eps.controllers.capture_controller import CaptureController
import sys

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)


def test_emits_on_packet(monkeypatch):
    received = []
    controller = CaptureController()
    controller.packet_received.connect(received.append)

    # Replace CaptureEngine with a stub
    fake_engine = MagicMock()
    monkeypatch.setattr(
        "eps.controllers.capture_controller.CaptureEngine",
        lambda *a, **kw: fake_engine,
    )

    controller.start(iface=None)
    # Simulate the engine invoking the callback
    fake_pkt = MagicMock()
    fake_pkt.time = 0.0
    # parse() will be invoked; you may need to patch it as well
    # ... (left as an exercise to wire up properly)
```

This is intentionally sketched, not complete. Wiring up a clean test for cross-thread Qt signals is itself instructive.

---

## Self-Administered Verification Gate

- [ ] `src/eps/controllers/capture_controller.py` exists and defines `CaptureController` with three signals.
- [ ] `scripts/qt_smoke_test.py` runs successfully and prints captured packets for 10 seconds.
- [ ] You have observed two different thread IDs (worker vs main).
- [ ] `lint-imports` passes with zero violations.
- [ ] `src/eps/controllers/` does not import any `PyQt6.QtWidgets` module — only `QtCore`.
- [ ] You can explain in writing why touching a `QWidget` from the capture callback would be unsafe.

Once all boxes are checked, you may begin Phase 5.
