"""Versioned SQLite persistence for read-only PAPER validation artifacts."""

from dataclasses import asdict
from contextlib import closing
import json
import sqlite3

from models.trade_report_card import TradeReportCard

VALIDATION_SCHEMA_VERSION = 1


class ValidationRepository:
    def __init__(self, path): self.path = str(path)

    def connect(self):
        connection=sqlite3.connect(self.path); connection.row_factory=sqlite3.Row; return connection

    def initialize(self):
        with closing(self.connect()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS validation_metadata(version INTEGER NOT NULL)")
            row=db.execute("SELECT version FROM validation_metadata").fetchone()
            if row is None: db.execute("INSERT INTO validation_metadata VALUES(?)",(VALIDATION_SCHEMA_VERSION,))
            elif row[0] != VALIDATION_SCHEMA_VERSION: raise RuntimeError("Validation schema version is unsupported.")
            db.execute("CREATE TABLE IF NOT EXISTS trade_report_cards(trade_id TEXT PRIMARY KEY,exit_timestamp TEXT NOT NULL,payload TEXT NOT NULL)")
            db.commit()

    def save_report_card(self, card):
        if not isinstance(card, TradeReportCard): raise ValueError("A TradeReportCard is required.")
        payload=json.dumps(asdict(card),sort_keys=True,separators=(",",":"))
        try:
            with closing(self.connect()) as db:
                db.execute("INSERT INTO trade_report_cards VALUES(?,?,?)",(card.trade_id,card.exit_timestamp,payload)); db.commit()
        except sqlite3.IntegrityError as exc: raise ValueError("Duplicate trade report card.") from exc

    def report_cards(self, limit=100):
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=1000: raise ValueError("Report-card limit is invalid.")
        with closing(self.connect()) as db: rows=db.execute("SELECT payload FROM trade_report_cards ORDER BY exit_timestamp DESC,trade_id LIMIT ?",(limit,)).fetchall()
        result=[]
        tuple_fields=("supporting_evidence","ignored_evidence","assumptions","uncertainty","correct_specialists","incorrect_specialists","learning_recommendations","provider_sources")
        for row in rows:
            payload=json.loads(row[0])
            for field in tuple_fields: payload[field]=tuple(payload[field])
            for field in ("entry_specialists","exit_specialists"): payload[field]=tuple(tuple(item) for item in payload[field])
            result.append(TradeReportCard(**payload))
        return tuple(result)
