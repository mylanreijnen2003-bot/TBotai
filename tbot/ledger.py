"""Logboek (SQLite) voor de live paper-run: trades, posities, equity, beslissingen.

- Idempotent: elke dag wordt maar één keer verwerkt (tabel `runs`), en elke
  trade heeft een unieke client_id (strategie + datum + munt + kant).
- Reconciliatie: cash en posities worden bij elke run opnieuw opgebouwd uit
  alle trades en vergeleken met de opgeslagen stand. Verschil -> stoppen.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .portfolio import Portfolio, Trade

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS runs (
    bar_date TEXT PRIMARY KEY, run_time TEXT, status TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS universe (month TEXT PRIMARY KEY, symbols TEXT, asof TEXT);
CREATE TABLE IF NOT EXISTS cash (strategy TEXT PRIMARY KEY, cash REAL);
CREATE TABLE IF NOT EXISTS positions (strategy TEXT, symbol TEXT, qty REAL, PRIMARY KEY (strategy, symbol));
CREATE TABLE IF NOT EXISTS trades (
    client_id TEXT PRIMARY KEY, strategy TEXT, date TEXT, symbol TEXT, side TEXT,
    qty REAL, price REAL, notional REAL, cost REAL, reason TEXT, version TEXT);
CREATE TABLE IF NOT EXISTS equity (
    strategy TEXT, date TEXT, equity REAL, cash REAL, exposure REAL, n_positions INTEGER,
    PRIMARY KEY (strategy, date));
CREATE TABLE IF NOT EXISTS decisions (
    strategy TEXT, date TEXT, symbol TEXT, target REAL, weight_before REAL, action TEXT,
    PRIMARY KEY (strategy, date, symbol));
CREATE TABLE IF NOT EXISTS observations (
    date TEXT, name TEXT, value REAL, extra TEXT, fetched_at TEXT, PRIMARY KEY (date, name));
CREATE TABLE IF NOT EXISTS data_windows (
    date TEXT, symbol TEXT, first_bar TEXT, last_bar TEXT, exec_price REAL, PRIMARY KEY (date, symbol));
"""


class Ledger:
    def __init__(self, path: str | Path = ":memory:", readonly: bool = False):
        if readonly:
            # alleen lezen (controles): het bestand blijft byte-voor-byte gelijk
            self.db = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
            return
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def has_table(self, name: str) -> bool:
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    # ---- meta ---------------------------------------------------------
    def get_meta(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_meta(self, key: str, value) -> None:
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(value)))

    # ---- runs ---------------------------------------------------------
    def already_processed(self, bar_date: str) -> bool:
        row = self.db.execute("SELECT status FROM runs WHERE bar_date=?", (bar_date,)).fetchone()
        return bool(row) and row[0] == "ok"

    def record_run(self, bar_date: str, run_time: str, status: str, message: str = "") -> None:
        self.db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)", (bar_date, run_time, status, message))

    def ok_bars(self) -> list[str]:
        """Alle signaaldagen die met succes verwerkt zijn, oplopend."""
        return [r[0] for r in self.db.execute("SELECT bar_date FROM runs WHERE status='ok' ORDER BY bar_date")]

    # ---- universe -----------------------------------------------------
    def get_universe(self, month: str) -> list[str] | None:
        row = self.db.execute("SELECT symbols FROM universe WHERE month=?", (month,)).fetchone()
        return json.loads(row[0]) if row else None

    def latest_universe(self) -> tuple[str, list[str]] | None:
        row = self.db.execute("SELECT month, symbols FROM universe ORDER BY month DESC LIMIT 1").fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def set_universe(self, month: str, symbols: list[str], asof: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO universe VALUES (?,?,?)", (month, json.dumps(symbols), asof))

    # ---- portefeuilles ------------------------------------------------
    def load_portfolios(self) -> dict[str, Portfolio]:
        pfs = {s: Portfolio(s, c) for s, c in self.db.execute("SELECT strategy, cash FROM cash")}
        for s, sym, q in self.db.execute("SELECT strategy, symbol, qty FROM positions"):
            if s in pfs and q > 0:
                pfs[s].qty[sym] = q
        return pfs

    def save_portfolio(self, pf: Portfolio) -> None:
        self.db.execute("INSERT OR REPLACE INTO cash VALUES (?,?)", (pf.name, pf.cash))
        self.db.execute("DELETE FROM positions WHERE strategy=?", (pf.name,))
        self.db.executemany(
            "INSERT INTO positions VALUES (?,?,?)", [(pf.name, s, q) for s, q in pf.qty.items() if q > 0]
        )

    def add_trades(self, strategy: str, date: str, trades: list[Trade], version: str) -> int:
        n = 0
        for tr in trades:
            cid = f"{version}-{strategy}-{date}-{tr.symbol}-{tr.side}"
            cur = self.db.execute(
                "INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (cid, strategy, date, tr.symbol, tr.side, tr.qty, tr.price, tr.notional, tr.cost, tr.reason, version),
            )
            n += cur.rowcount
        return n

    def add_equity(self, strategy: str, date: str, equity: float, cash: float, exposure: float, n_pos: int) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO equity VALUES (?,?,?,?,?,?)", (strategy, date, equity, cash, exposure, n_pos)
        )

    def add_decisions(self, strategy: str, date: str, rows: list[tuple[str, float, float, str]]) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?,?)", [(strategy, date, *r) for r in rows]
        )

    def add_data_windows(self, date: str, rows: list[tuple[str, str, str, float]]) -> None:
        """Welke koershistorie (eerste/laatste slotdag) en uitvoeringsprijs de run per munt gebruikte."""
        self.db.executemany(
            "INSERT OR REPLACE INTO data_windows VALUES (?,?,?,?,?)", [(date, *r) for r in rows]
        )

    def add_observation(self, date: str, name: str, value: float, extra: str, fetched_at: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?)", (date, name, value, extra, fetched_at))

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    # ---- reconciliatie ------------------------------------------------
    def reconcile(self, start_capital: float, tol: float = 1e-6) -> list[str]:
        """Bouw cash en posities opnieuw op uit alle trades. Geeft een lijst verschillen terug (leeg = oké)."""
        problems = []
        stored = self.load_portfolios()
        rebuilt: dict[str, Portfolio] = {s: Portfolio(s, start_capital) for s in stored}
        for s, sym, side, qty, notional, cost in self.db.execute(
            "SELECT strategy, symbol, side, qty, notional, cost FROM trades ORDER BY date, rowid"
        ):
            pf = rebuilt.setdefault(s, Portfolio(s, start_capital))
            if side == "buy":
                pf.cash -= notional + cost
                pf.qty[sym] = pf.qty.get(sym, 0.0) + qty
            else:
                pf.cash += notional - cost
                pf.qty[sym] = pf.qty.get(sym, 0.0) - qty
        for s in set(stored) | set(rebuilt):
            a, b = stored.get(s), rebuilt.get(s)
            if a is None or b is None:
                problems.append(f"{s}: ontbreekt in opgeslagen stand of trades")
                continue
            if abs(a.cash - b.cash) > tol * max(1.0, abs(b.cash)):
                problems.append(f"{s}: cash {a.cash:.6f} ≠ uit trades {b.cash:.6f}")
            for sym in set(a.qty) | set(b.qty):
                qa, qb = a.qty.get(sym, 0.0), b.qty.get(sym, 0.0)
                if qb < 1e-12:
                    qb = 0.0
                if abs(qa - qb) > max(1e-9, 1e-7 * abs(qb)):
                    problems.append(f"{s}/{sym}: positie {qa} ≠ uit trades {qb}")
            if b.cash < -1e-6:
                problems.append(f"{s}: negatief cash {b.cash}")
        return problems

    # ---- export -------------------------------------------------------
    def export_csv(self, out_dir: str | Path) -> None:
        import pandas as pd

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for table in ["equity", "trades", "universe", "observations", "runs"]:
            pd.read_sql_query(f"SELECT * FROM {table}", self.db).to_csv(out / f"{table}.csv", index=False)
