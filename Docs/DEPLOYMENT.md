# Paper-Only Deployment

Hermes requires Python 3.11+, one CPU, 512 MB RAM, and persistent local volumes
for `/app/data` and `/app/logs`. Run locally with `python main.py` or build with
`docker compose build` and start with `docker compose up -d`.

The container runs as the non-root `hermes` user, displays PAPER mode through its
healthcheck, and runs a foreground signal-aware health supervisor. The supervisor
does not execute trades or access a network; paper sessions remain explicit
application commands. The service restarts unless stopped. No ports, credentials, exchange
connections, or live-trading switches are configured. CI tests but never deploys.

Back up with `database.maintenance.backup_database`; validate backups before
restore. Stop the paper process before restoring a database.
