# Phase 10 — Portfolio Presentation

**Estimated duration:** 3–5 days
**Prerequisite:** Phase 9 complete
**Outcome:** A polished `README.md`, a labeled architecture diagram in `docs/`, an animated demo (GIF or short video), and a written technical note about one non-obvious engineering decision. The project is now presentable to employers.

---

## Relevant Knowledge

### Why Portfolio Presentation Is Not Optional

A working tool that nobody can find, run, or understand has zero portfolio value. The presentation layer determines whether a recruiter spends 30 seconds on your repo and moves on, or spends 5 minutes and adds you to the interview pile.

Employers and senior engineers evaluating a portfolio look for **three** things, in this order:

1. **Can I understand what this is in under 30 seconds?** A clear README headline, a screenshot, and a one-sentence description.
2. **Does this person make good engineering decisions?** Architecture diagram, technical write-up, code organization.
3. **Can I see it actually work?** Demo GIF, clear run instructions, or a downloadable build.

Skip any of these and you lose the candidate-pool dice roll.

### Anatomy of a Strong Technical README

A README for a non-trivial project should answer, in order:

1. **What is this?** One sentence and one screenshot. Above the fold.
2. **What problem does it solve / who is it for?** One paragraph.
3. **Features.** Bulleted list, scannable.
4. **Installation.** Concrete commands, copy-pasteable.
5. **Usage.** Show the happy path with screenshots.
6. **Architecture.** Diagram and a paragraph explaining the layered design.
7. **Build / Develop.** How to run from source, run tests, build the exe.
8. **Roadmap / Status.** What is done, what is planned, what is known to be broken.
9. **Acknowledgements / License.** Brief.

Avoid: emoji garlands, "stars please!" pleas, vague descriptions, screenshots from the wrong app, dead links to old issues.

### Architecture Diagrams

Two approaches both work:

1. **ASCII diagrams** (like the one in `PROJECT_GUIDE.md` Section 5). Universal, version-controllable, no rendering required. Suits a developer-targeted README.
2. **Rendered diagrams** via Mermaid (rendered natively by GitHub README) or PlantUML, or a hand-drawn diagram exported to PNG.

For a security/networking project, the ASCII layered diagram is appropriate and matches the aesthetic of well-respected repos like tcpdump, Wireshark, and Suricata.

### Recording a Demo

Tools for Windows:

- **ScreenToGif** (free, open source) — best for short animated GIFs (the recommended option).
- **OBS Studio** (free) — for full video demos uploaded to YouTube.
- **PowerToys Screen Recorder** (built in) — fine for quick captures.

What to include in a demo:

1. Open the app.
2. Start a capture.
3. Generate traffic (visit a website).
4. Stop the capture.
5. Click a packet, show the detail tree and hex dump.
6. Apply a display filter.
7. Open the Statistics dialog.
8. Save to .pcap, reopen to demonstrate persistence.

Keep it under 30 seconds. Loop-able GIFs hold attention longer than long videos.

### The Technical Write-Up

Pick one non-trivial engineering decision and explain it in 300–600 words. Recommended topics:

- "Why `QAbstractTableModel` and not `QTableWidget`." Includes a discussion of memory and performance differences with concrete numbers from your own benchmarks.
- "The GIL and packet capture: why Python threading works here." Includes an explanation of when threading is and is not useful, with the I/O-bound vs CPU-bound distinction.
- "Enforcing architecture with `import-linter`." Discusses why a self-imposed architectural rule is enforceable in Python despite the language not supporting it natively.
- "Producer-consumer with Qt signals: avoiding the temptation of `queue.Queue`." Discusses the cross-thread bridge.

This write-up demonstrates depth. It is the difference between "this person built a packet sniffer" and "this person understands the *engineering* of a packet sniffer."

---

## Resources for Learning and Research

| Resource | Purpose |
|---|---|
| [GitHub — "awesome-readme"](https://github.com/matiassingers/awesome-readme) | Examples of strong READMEs |
| [Make a README — guide](https://www.makeareadme.com/) | Practical README writing |
| [ScreenToGif](https://www.screentogif.com/) | The recording tool |
| [GitHub Mermaid support](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) | If you go the Mermaid route |
| [shields.io](https://shields.io/) | Badges for Python version, license, etc. — sparingly |
| Wireshark's own README and docs/ | The canonical reference for what a network-tool README should look like |

---

## Steps for Implementation

### Step 1 — Capture a Hero Screenshot

Launch the app, capture some traffic, pick an interesting moment with the detail tree and hex dump visible. Take a screenshot at 1280×800 or similar. Save as `docs/screenshots/main.png`.

### Step 2 — Record the Demo

Using ScreenToGif:

1. Launch ScreenToGif.
2. Position the recording frame over your app window.
3. Start recording.
4. Execute the demo flow (Step 5 of the "Recording a Demo" section above).
5. Stop. Trim. Save as `docs/screenshots/demo.gif`. Aim for under 5 MB.

### Step 3 — Write `README.md`

```markdown
# Easy Packet Sniffer

A Wireshark-style network analyzer built in Python with Scapy and PyQt6.

![Main view](docs/screenshots/main.png)

## What It Does

Easy Packet Sniffer captures live network traffic, parses it into structured
packet objects, and presents the results in a three-pane GUI: a live packet
table, a hierarchical protocol detail tree, and a hex/ASCII dump. It supports
BPF capture filters, display filters, .pcap import/export interoperable with
Wireshark, and per-protocol statistics.

## Features

- Live packet capture on Windows (via Npcap)
- Three-pane Wireshark-style UI
- BPF capture filters (kernel-level)
- Display filters with a simple expression syntax
- Save and load `.pcap` files
- Statistics: protocol hierarchy, endpoints, conversations
- Architecturally decoupled — the core layer is independently testable

![Demo](docs/screenshots/demo.gif)

## Installation

Requirements: Windows 10/11, Python 3.13+, Npcap installed in WinPcap API-compatible mode.

```
git clone https://github.com/<you>/easy-packet-sniffer.git
cd easy-packet-sniffer
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Running

From an Administrator terminal:

```
python -m eps.main
```

Or use the prebuilt executable: see Releases.

## Architecture

The codebase follows a three-layer separation: a domain layer that has no
knowledge of the GUI, an application layer that bridges threads via Qt signals,
and a presentation layer that consumes a `QAbstractTableModel`.

See [docs/architecture.md](docs/architecture.md) for the full diagram.

## Development

```
pytest                # run tests
lint-imports          # verify architectural boundaries
pyinstaller eps.spec  # build standalone executable
```

## Technical Notes

- [Why `QAbstractTableModel` and not `QTableWidget`](docs/notes/qabstracttablemodel.md)

## Status

Version 0.1. All core features implemented. Live decoding of application-layer
protocols (HTTP, TLS handshake) is planned for a future release.

## License

MIT.
```

### Step 4 — `docs/architecture.md`

Move the architecture section out of `PROJECT_GUIDE.md` into its own `docs/architecture.md`. Add:

- The ASCII layered diagram from `PROJECT_GUIDE.md` Section 5.
- The directory layout.
- A paragraph explaining the import boundaries and how `import-linter` enforces them.
- One paragraph on the threading model (capture worker thread, Qt main thread, signals as the bridge).

### Step 5 — `docs/notes/qabstracttablemodel.md`

Write the 300–600 word technical note. Include:

- The problem (live updating a table with N rows).
- The naive solution (`QTableWidget`) and why it fails at scale.
- The Model/View solution.
- Concrete numbers from your own testing if you have them.

### Step 6 — Final Polish

- Verify all links in the README work.
- Verify the screenshot and GIF render correctly on GitHub.
- Run the test suite once more. Verify CI is green if you have CI.
- Tag a release: `git tag v0.1.0 && git push --tags`.
- Optional: create a GitHub Release with the built `.exe` attached.

### Step 7 — LinkedIn / Portfolio Site Post (Optional but Recommended)

Write a short post for LinkedIn or your portfolio site:

> Built a Wireshark-style packet analyzer from scratch in Python. Key
> engineering challenges: keeping the capture engine independently testable
> from the GUI, threading the producer-consumer pipeline through Qt signals,
> and scaling a live table view to 100,000+ rows. Source and architecture
> notes at <link>.

Include the demo GIF.

---

## Self-Administered Verification Gate

- [ ] `README.md` is complete, scannable in 30 seconds, and contains a screenshot above the fold.
- [ ] `docs/architecture.md` exists with the layered diagram and threading explanation.
- [ ] `docs/notes/` contains at least one technical write-up of 300+ words.
- [ ] `docs/screenshots/demo.gif` exists and shows the app working end-to-end.
- [ ] All README links resolve.
- [ ] A release tag has been created.
- [ ] The repository can be shown to a third party without verbal explanation, and they understand what the project is.

Once all boxes are checked, the project is portfolio-ready. Congratulations.

---

## Closing Note

The discipline that produced this project — strict architectural boundaries, verified gates between phases, mandatory reading before code, honest self-assessment — is the same discipline that produces production-quality software in industry. If you take only one thing from this project, take that.
