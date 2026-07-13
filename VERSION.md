# Hermes OS Version

- Company: Hermes Quant Labs
- Version: 0.1.0-rc1
- Release type: Paper Trading Release Candidate with V4 Local Operator Platform
- Mode: PAPER only
- Live trading: disabled
- Verified tests: 242 passing before final V4.6 validation
- Development milestone: V5.6 Continuous PAPER Platform Hardening
- Research schema: 1
- Current development validation: V5.1 through V5.5 complete; final V5.6 validation pending
- Docker: image build, Compose startup, non-root user, writable volumes, and health verified
- GitHub Actions: `test` and `secret-scan` passed for RC1
- Limitations: synchronous single-process operation, SQLite storage, artificial replay fixtures, fixed demonstration risk caps, long-only simulation, no default internet provider, and no profitability claim
