# Backup and Restore

Stop the PAPER service before restore. Create backups with `python -m database.maintenance backup SOURCE DESTINATION`, then verify with `python -m database.maintenance verify SOURCE BACKUP`. Restore only a schema-validated backup to the intended local target and run database integrity checks before restart.

SQLite is synchronous and single-host. Do not share its volume between concurrent containers. Preserve the original database until restored state and portfolio reload are verified.

Before restoring a multi-symbol session, stop scheduling all symbols. After restore, validate shared cash/equity and each persisted position before enabling cycles.
