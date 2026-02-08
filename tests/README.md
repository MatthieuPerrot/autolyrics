# Tests

## Structure

```
tests/
├── conftest.py              # Shared fixtures, sys.path setup
├── helpers/
│   └── assertions.py        # Assertion helpers (no direct assert in tests)
├── fixtures/                 # Sample HTML files for each source
│   ├── animelyrics_*.html
│   ├── nautiljon_*.html
│   └── ...
├── unit/                     # Unit tests (pure functions, no network)
│   ├── test_parsers.py       # parse_* functions for all 6 sources
│   └── test_source_registry.py
└── integration/              # Integration tests (mocked network, full flows)
    └── test_orchestrator.py  # Three-phase orchestrator with mocked fetchers
```

## Conventions

1. **No direct `assert`** — use helpers from `tests/helpers/assertions.py`
2. **No access to private members** (`_foo`, `__bar`) in tests — if needed,
   expose via a helper in `tests/helpers/`
3. **Fixtures in files** — HTML samples live in `tests/fixtures/` as `.html` files
4. **No network in unit tests** — all HTTP calls mocked
5. **Integration tests may mock at the network boundary** (requests, selenium)
   but should exercise the full orchestrator logic

## Running

```bash
# All tests
python3 -m pytest tests/ -v

# Unit tests only
python3 -m pytest tests/unit/ -v

# Integration tests only
python3 -m pytest tests/integration/ -v

# Single test file
python3 -m pytest tests/unit/test_parsers.py -v
```
