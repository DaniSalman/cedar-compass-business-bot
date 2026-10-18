"""Persistent, cross-process reservations for this project's small API budget."""
import json
import sqlite3
import uuid
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

# Gemini 3.5 Flash-Lite paid-tier text rates, checked in official docs on
# 2026-10-18 ($0.30 input / $2.50 output per million tokens). The Gemini free
# tier costs $0, so these estimates only matter if billing is enabled on the
# Google project. Thinking tokens are billed as output. Flash-Lite is the default
# because gemini-3.8-flash allows only 20 free requests per day.
DEFAULT_MODEL = "gemini-3.5-flash-lite"
INPUT_USD_PER_MILLION = Decimal("0.30")
OUTPUT_USD_PER_MILLION = Decimal("2.50")
DEFAULT_BUDGET_USD = Decimal("1.00")
ABSOLUTE_BUDGET_USD = Decimal("10.00")
MICRO = Decimal(1_000_000)
MAX_INPUT_BOUND = 40_000


class BudgetExceeded(RuntimeError):
    """No request was sent because its maximum cost would exceed the cap."""


def cost_micro(input_tokens, output_tokens):
    """Integer microdollars, rounded up; no floating-point budget comparisons."""
    return int((Decimal(input_tokens) * INPUT_USD_PER_MILLION
                + Decimal(output_tokens) * OUTPUT_USD_PER_MILLION)
               .to_integral_value(rounding=ROUND_CEILING))


def input_upper_bound(payload):
    """UTF-8 bytes overestimate byte-BPE text tokens; allow extra chat framing.

    We serialize *all* prompt/schema fields, then add generous framing overhead.
    Oversized requests are rejected instead of silently dropping instructions.
    """
    size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    bound = size + 2048 + 64 * len(payload.get("messages", []))
    if bound > MAX_INPUT_BOUND:
        raise BudgetExceeded("This conversation is too long. Start a new chat.")
    return bound


class Budget:
    def __init__(self, path, limit=DEFAULT_BUDGET_USD, model=DEFAULT_MODEL):
        self.path = Path(path)
        self.model = model
        self.path.parent.mkdir(parents=True, exist_ok=True)
        requested = Decimal(str(limit))
        if not requested.is_finite() or not (0 < requested <= ABSOLUTE_BUDGET_USD):
            raise ValueError(f"Budget must be greater than 0 and at most ${ABSOLUTE_BUDGET_USD}.")
        self.limit_micro = int(requested * MICRO)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests "
                       "(id TEXT PRIMARY KEY, phase TEXT, reserved INTEGER, "
                       "charged INTEGER, input_tokens INTEGER, output_tokens INTEGER)")

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=30)

    def reserve(self, phase, payload, max_output_tokens):
        maximum = cost_micro(input_upper_bound(payload), max_output_tokens)
        call_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT COALESCE(SUM(charged),0) FROM requests").fetchone()[0]
            if total + maximum > self.limit_micro:
                raise BudgetExceeded("The project API budget is nearly used up; no request was sent.")
            # Crashes, timeouts and unknown billing retain the full reservation.
            db.execute("INSERT INTO requests VALUES (?,?,?,?,NULL,NULL)",
                       (call_id, phase, maximum, maximum))
        return call_id

    def settle(self, call_id, input_tokens, output_tokens):
        actual = cost_micro(input_tokens, output_tokens)
        overrun = False
        with self.connect() as db:
            reserved = db.execute("SELECT reserved FROM requests WHERE id=?", (call_id,)).fetchone()[0]
            if actual > reserved:
                # Unexpected pricing/token-accounting changes must fail closed.
                db.execute("UPDATE requests SET charged=? WHERE id=?", (self.limit_micro, call_id))
                overrun = True
            else:
                db.execute("UPDATE requests SET charged=?,input_tokens=?,output_tokens=? WHERE id=?",
                           (actual, input_tokens, output_tokens, call_id))
        if overrun:
            raise BudgetExceeded("Unexpected token accounting; API calls have been stopped.")

    def release(self, call_id):
        """A request the API rejected before running (HTTP 429) is not billed."""
        with self.connect() as db:
            db.execute("UPDATE requests SET charged=0,input_tokens=0,output_tokens=0 WHERE id=?", (call_id,))

    def summary(self):
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*),COALESCE(SUM(charged),0),"
                             "COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),"
                             "SUM(CASE WHEN input_tokens IS NULL THEN 1 ELSE 0 END) FROM requests").fetchone()
        return {"model": self.model, "calls_attempted": row[0],
                "accounted_usd": round(row[1] / 1_000_000, 6),
                "input_tokens": row[2], "output_tokens": row[3],
                "unsettled_reservations": row[4] or 0,
                "cap_usd": self.limit_micro / 1_000_000}
