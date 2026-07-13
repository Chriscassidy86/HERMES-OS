# Hermes OS Version

- Company: Hermes Quant Labs
- Version: 0.1.0-rc1
- Release type: Paper Trading Release Candidate with V4 Local Operator Platform
- Mode: PAPER only
- Live trading: disabled
- Verified tests: 242 passing before final V4.6 validation
- Development milestone: V6.6 Multi-Symbol PAPER Platform Hardening
- Research schema: 1
- Current development validation: V6.1 through V6.5 complete; final V6.6 validation pending
- Docker: image build, Compose startup, non-root user, writable volumes, and health verified
- GitHub Actions: `test` and `secret-scan` passed for RC1
- Limitations: synchronous single-process operation, SQLite storage, artificial replay fixtures, fixed demonstration risk caps, long-only simulation, no default internet provider, and no profitability claim
