"""Append-only decision ledger. The agent's call is written BEFORE a human resolves the record,
so a later grade can never be contaminated by what the human's resolution changed."""
import sqlite3

SCHEMA = """
CREATE TABLE decisions (
    record_id   TEXT PRIMARY KEY,
    action      TEXT NOT NULL,
    person_id   INTEGER,
    reason      TEXT NOT NULL,
    mode        TEXT NOT NULL,          -- shadow or live, at decision time
    decided_seq INTEGER NOT NULL
);
CREATE TABLE grades (
    record_id    TEXT PRIMARY KEY REFERENCES decisions(record_id),
    human_person INTEGER,               -- NULL means the human said "new person"
    agrees       INTEGER NOT NULL
);
CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decisions
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decisions
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER grades_no_update BEFORE UPDATE ON grades
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
"""


class Ledger:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self.seq = 0

    def record(self, record_id, decision, mode):
        self.seq += 1
        self.db.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?)",
                        (record_id, decision.action, decision.person_id, decision.reason, mode, self.seq))

    def grade(self, record_id, human_person):
        """Grade a decision against the human's resolution. Returns True/False for a graded
        merge call, None when the agent skipped (skips are not graded toward the streak)."""
        row = self.db.execute("SELECT action, person_id FROM decisions WHERE record_id=?", (record_id,)).fetchone()
        if row is None:
            raise KeyError(f"no pre-resolution decision for {record_id}; refusing to grade after the fact")
        action, person_id = row
        if action == "skip":
            return None
        agrees = human_person == person_id
        self.db.execute("INSERT INTO grades VALUES (?,?,?)", (record_id, human_person, int(agrees)))
        return agrees

    def summary(self):
        fired, agreed = self.db.execute("SELECT COUNT(*), COALESCE(SUM(agrees),0) FROM grades").fetchone()
        total = self.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        return {"decisions": total, "fired": fired, "agreed": agreed}
