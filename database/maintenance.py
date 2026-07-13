"""Safe local SQLite backup and restore operations."""
from pathlib import Path
import shutil,sqlite3
from contextlib import closing
from database.journal import SQLiteAuditJournal
def backup_database(source,destination):
    source=Path(source).resolve(); destination=Path(destination).resolve()
    if source==destination or not source.is_file(): raise ValueError("Backup source must exist and differ from destination.")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst); dst.commit()
    SQLiteAuditJournal(destination).validate_schema(); return destination
def restore_database(backup,target):
    backup=Path(backup).resolve(); target=Path(target).resolve()
    if backup==target or not backup.is_file(): raise ValueError("Restore backup must exist and differ from target.")
    SQLiteAuditJournal(backup).validate_schema(); target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+".restore"); shutil.copy2(backup,temporary); temporary.replace(target)
    SQLiteAuditJournal(target).validate_schema(); return target

def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("operation",choices=("backup","restore")); parser.add_argument("source"); parser.add_argument("destination"); args=parser.parse_args()
    result=backup_database(args.source,args.destination) if args.operation=="backup" else restore_database(args.source,args.destination)
    print(result)
if __name__=="__main__": main()
