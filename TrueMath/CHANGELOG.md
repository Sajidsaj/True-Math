# Changelog

All notable changes to TrueMath will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Native desktop shell bootstrap via `pywebview`
- PowerShell build, packaging, and release scripts
- Windows installer definition for Inno Setup
- Release and operations documentation
- Runtime configuration validation and typed environment overrides

### Changed
- Runtime data, logs, and databases now resolve through release-safe absolute paths
- Frontend version display now tracks the repository `VERSION` file
- Dashboard startup now fails fast if production assets are missing

---

## [1.0.0] — 2026-07-04

### Added
- 15-module autonomous mathematical research engine
- Monte Carlo Tree Search (MCTS) with UCB1 exploration/exploitation
- Lean 4 formal theorem verification subprocess bridge
- Statistical falsification engine (1000-iteration brute-force)
- Graveyard RAG memory (cosine-similarity SQLite failure store)
- Symbolic Genesis operator invention engine
- LLM bridge (zero-dependency HTTP client for Ollama/llama.cpp)
- Cognitive context window manager with token budgeting
- WebSocket IPC server (port 9999) with live telemetry broadcast
- React/Vite dashboard with MCTS tree visualization and Brain Power metrics
- HTTP dashboard server with security headers (CSP, X-Frame-Options)
- SQLite state persistence with WAL mode and zlib compression
- UDP P2P swarm discovery with peer validation
- Async rotating file logger (thread-safe queue listener)
- Lazy SymPy loading (180ms startup reduction)

### Security
- WebSocket frame size capped at 64 KB (DoS protection)
- Maximum 10 concurrent WebSocket connections
- eval() input hard-capped at 512 characters
- UDP inbound beacon validation (agent field check)
- Log expression truncation (80-char cap on disk)
- HTTP security headers on all dashboard responses

### Performance
- MCTS UCB1 `exploration_multiplier` pre-computed per depth level
- Zero-allocation token counting (`count(' ')` vs `split()`)
- Lean 4 binary availability cached at startup with `shutil.which()`
- Debug f-string logging guarded with `isEnabledFor(10)`
- SQLite connections use `@contextmanager` for guaranteed closure

### Fixed
- Graveyard dimensionality mismatch (vector length guard)
- `os.chdir()` global CWD mutation (BUG-03)
- LRU cache memory leak on instance methods (BUG-08)
- Thread-safety: peer set mutations locked (BUG-09)
- `signal.pause()` Windows incompatibility (BUG-01)
- MCTS exploration weight orphaned constant (BUG-13)
- Cognitive context reset via private attrs (BUG-07)
