# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-29

### Added

- `rttgap.evaluate()`: fastest TCP round trip vs fastest echo, with thresholds from
  798 residential proxy sessions and 50 direct visits.
- Linux `tcp_info` reader (`tcpi_min_rtt`, falling back to `tcpi_rtt`).
- aiohttp integration that reads the round trip from the socket, and refuses a
  loopback peer (a reverse proxy in front) instead of guessing.
- Starlette / FastAPI integration that takes the round trip from a reverse-proxy
  header (nginx `$tcpinfo_rtt`).
- Browser client (`rttgap.CLIENT_JS`), safe to inline in a `<script>` tag.
- `python -m rttgap` demo server.

[0.1.0]: https://github.com/MrDebugger/rttgap/releases/tag/v0.1.0
