# Contributing to rttgap

Thanks for helping. Bug reports, new framework integrations and measurements from
other proxy networks are all welcome.

## Set up

```bash
git clone https://github.com/MrDebugger/rttgap
cd rttgap
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[test]"
python -m pytest -q
```

Some tests read the kernel's `tcp_info` and only run on Linux, including the one
that puts a relay between client and server to play the proxy. CI runs the suite on
Linux, Windows and macOS.

## Pull requests

- Keep the core (`rttgap.core`, `rttgap.measure`, `rttgap.tcpinfo`) free of
  third-party dependencies. Integrations go in their own module with an optional
  extra in `pyproject.toml`.
- Add a test for every behaviour change. For anything that touches the verdict,
  show the numbers: what the gap was before and after.
- Update `CHANGELOG.md` under an "Unreleased" heading.

## Sharing measurements

If you run rttgap against a proxy network or an access network (mobile carriers,
satellite, corporate proxies) and the thresholds misjudge it, please open an issue
with the gaps you saw. Leave out anything that identifies the proxy provider's
customers or your own infrastructure.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
