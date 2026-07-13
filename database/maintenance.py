"""Safe local SQLite integrity, backup, and restore operations."""
from dataclasses import dataclass
from pathlib import Path
import shutil,sqlite3
from contextlib import closing
from database.journal import SQLiteAuditJournal,TABLES

@dataclass(frozen=True)
class DatabaseVerification:
    path:str; healthy:bool; quick_check:str; foreign_key_errors:int

@dataclass(frozen=True)
class BackupVerification:
    source:DatabaseVerification; backup:DatabaseVerification
    matching_row_counts:bool

def verify_database(path):
    path=Path(path).resolve()
    if not path.is_file(): raise ValueError("Database file does not exist.")
    journal=SQLiteAuditJournal(path); journal.validate_schema()
    with journal.connect() as db:
        quick=db.execute("PRAGMA quick_check").fetchone()[0]
        foreign_errors=len(db.execute("PRAGMA foreign_key_check").fetchall())
    if quick!="ok" or foreign_errors: raise ValueError("Database integrity verification failed.")
    return DatabaseVerification(str(path),True,quick,foreign_errors)

def _row_counts(path):
    journal=SQLiteAuditJournal(path)
    with journal.connect() as db:
        return tuple((table,db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in TABLES)

def verify_backup(source,backup):
    source_check=verify_database(source); backup_check=verify_database(backup)
    matching=_row_counts(source)==_row_counts(backup)
    if not matching: raise ValueError("Backup row counts do not match the source database.")
    return BackupVerification(source_check,backup_check,True)

def backup_database(source,destination):
    source=Path(source).resolve(); destination=Path(destination).resolve()
    if source==destination or not source.is_file(): raise ValueError("Backup source must exist and differ from destination.")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst); dst.commit()
    verify_backup(source,destination); return destination
def restore_database(backup,target):
    backup=Path(backup).resolve(); target=Path(target).resolve()
    if backup==target or not backup.is_file(): raise ValueError("Restore backup must exist and differ from target.")
    SQLiteAuditJournal(backup).validate_schema(); target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+".restore"); shutil.copy2(backup,temporary); temporary.replace(target)
    SQLiteAuditJournal(target).validate_schema(); return target

def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("operation",choices=("backup","restore","verify","verify-backup")); parser.add_argument("source"); parser.add_argument("destination",nargs="?"); args=parser.parse_args()
    if args.operation in {"backup","restore","verify-backup"} and not args.destination: parser.error("destination is required for backup, restore, and backup verification")
    if args.operation=="backup": result=backup_database(args.source,args.destination)
    elif args.operation=="restore": result=restore_database(args.source,args.destination)
    elif args.operation=="verify-backup": result=verify_backup(args.source,args.destination)
    else: result=verify_database(args.source)
    print(result)
if __name__=="__main__": main()
