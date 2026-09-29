"""Node-side authorisation for the PSI step (docs/43).

The OPRF evaluation is the natural gate: a node that refuses to evaluate for
a caller leaks nothing and serves nothing, because no envelope opens without
the node's cooperation. This module is that gate, plus the per-credential
evaluation budget that turns table enumeration (docs/37: an authorised
client dumps a node in ⌈clusters/nprobe⌉ queries) from "rate-limitable in
principle" into a measured bound with an identity in the audit log.

Credential: a client id and a shared HMAC key issued by the federation
operator. The client signs each request over (node_id, day, blinded points)
so a request cannot be replayed against another node, another day, or with
other points. The node keeps an allow-list `{client_id: (key, daily_budget)}`
in a JSON file next to its data (mode 0600) and counts evaluations per
client per UTC day.

This identifies WHICH member asked — the node learns "client 42 probed 2
clusters today", never what the query was. Hiding membership too needs an
anonymous credential (Privacy Pass-style tokens); that is the design
direction, not built.

Not a substitute for transport security: TLS on every hop is assumed in
deployment and out of scope here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

_DOMAIN = b"fedsaferouter/credential/v1"


def utc_day(now: float | None = None) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() if now is None else now))


def request_digest(node_id: str, day: str, blinded: list[bytes]) -> bytes:
    h = hashlib.sha256(_DOMAIN)
    h.update(node_id.encode("utf-8") + b"\0" + day.encode("utf-8") + b"\0")
    for point in blinded:
        h.update(point)
    return h.digest()


@dataclass(frozen=True)
class Credential:
    """Client side. `key` is the shared secret issued by the federation.
    `roles` is the client's own copy of the roles it was issued — used only
    to choose which published clusters to probe (docs/45). The node never
    trusts it: the node reads the client's roles from its own allow-list."""
    client_id: str
    key: bytes
    roles: tuple[str, ...] = ()

    def sign(self, node_id: str, blinded: list[bytes], now: float | None = None) -> dict:
        day = utc_day(now)
        mac = hmac.new(self.key, request_digest(node_id, day, blinded), hashlib.sha256).hexdigest()
        return {"client_id": self.client_id, "day": day, "mac": mac}


class Unauthorized(Exception):
    """Raised before any OPRF evaluation happens; carries a stable reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class ClientPolicy:
    key: bytes
    daily_evaluation_budget: int  # blinded points evaluated per UTC day
    roles: tuple[str, ...] = ()   # issued by the federation; decides readable collections (docs/45)


@dataclass
class Authorizer:
    """Node side. Allow-list + per-client per-day evaluation counter + audit.

    With `state_path` the counter and the audit log live in a SQLite file
    next to the node's data (0600), updated in one IMMEDIATE transaction per
    request, so every process of the node — a fresh one per MCP call, or one
    after a restart — enforces the same budget. Without it (tests, in-process
    simulation) they are in memory. Before this (audit, docs/49) the budget
    was in memory only and a spawn-per-call node reset it on every call."""
    node_id: str
    policies: dict[str, ClientPolicy] = field(default_factory=dict)
    usage: dict[tuple[str, str], int] = field(default_factory=dict)   # (client_id, day) -> evaluations
    audit: list[dict] = field(default_factory=list)
    state_path: Path | None = None

    def __post_init__(self) -> None:
        if self.state_path is not None:
            with closing(self._db()) as db:
                db.execute("CREATE TABLE IF NOT EXISTS usage (client_id TEXT, day TEXT, evaluations INTEGER, "
                           "PRIMARY KEY (client_id, day))")
                db.execute("CREATE TABLE IF NOT EXISTS audit (ts REAL, client_id TEXT, outcome TEXT, evaluations INTEGER)")
            os.chmod(self.state_path, 0o600)

    def _db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.state_path, timeout=30, isolation_level=None)

    def _persisted_check(self, client_id: str, day: str, n: int, budget: int) -> bool:
        """Atomically charge `n` evaluations if they fit; log either way."""
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT evaluations FROM usage WHERE client_id = ? AND day = ?", (client_id, day)).fetchone()
            used = row[0] if row else 0
            ok = used + n <= budget
            if ok:
                db.execute("INSERT INTO usage VALUES (?, ?, ?) ON CONFLICT(client_id, day) DO UPDATE SET evaluations = ?",
                           (client_id, day, used + n, used + n))
            db.execute("INSERT INTO audit VALUES (?, ?, ?, ?)",
                       (time.time(), client_id, "ok" if ok else "budget_exhausted", n))
            db.execute("COMMIT")
            self.usage[(client_id, day)] = used + n if ok else used
            return ok
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def persisted_audit(self) -> list[dict]:
        if self.state_path is None:
            return list(self.audit)
        with closing(self._db()) as db:
            return [{"ts": ts, "client_id": c, "outcome": o, "evaluations": n}
                    for ts, c, o, n in db.execute("SELECT ts, client_id, outcome, evaluations FROM audit ORDER BY rowid")]

    def check(self, auth: dict | None, blinded: list[bytes], now: float | None = None) -> str:
        """Validates the credential and charges the evaluations. Returns the
        client id. Raises Unauthorized (nothing is evaluated) otherwise."""
        if not auth or not isinstance(auth, dict):
            self._log(None, "missing_credential", len(blinded))
            raise Unauthorized("missing_credential")
        client_id, day, mac = auth.get("client_id"), auth.get("day"), auth.get("mac", "")
        policy = self.policies.get(client_id or "")
        if policy is None:
            self._log(client_id, "unknown_client", len(blinded))
            raise Unauthorized("unknown_client")
        if day != utc_day(now):
            self._log(client_id, "stale_credential", len(blinded))
            raise Unauthorized("stale_credential")
        expected = hmac.new(policy.key, request_digest(self.node_id, day, blinded), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, mac):
            self._log(client_id, "bad_signature", len(blinded))
            raise Unauthorized("bad_signature")
        if self.state_path is not None:
            if not self._persisted_check(client_id, day, len(blinded), policy.daily_evaluation_budget):
                self.audit.append({"ts": time.time(), "client_id": client_id, "outcome": "budget_exhausted",
                                   "evaluations": len(blinded)})
                raise Unauthorized("budget_exhausted")
            self.audit.append({"ts": time.time(), "client_id": client_id, "outcome": "ok", "evaluations": len(blinded)})
            return client_id
        used = self.usage.get((client_id, day), 0)
        if used + len(blinded) > policy.daily_evaluation_budget:
            self._log(client_id, "budget_exhausted", len(blinded))
            raise Unauthorized("budget_exhausted")
        self.usage[(client_id, day)] = used + len(blinded)
        self._log(client_id, "ok", len(blinded))
        return client_id

    def roles_of(self, client_id: str) -> tuple[str, ...]:
        policy = self.policies.get(client_id)
        return tuple(policy.roles) if policy else ()

    def remaining(self, client_id: str, now: float | None = None) -> int:
        policy = self.policies.get(client_id)
        if policy is None:
            return 0
        day = utc_day(now)
        used = self.usage.get((client_id, day), 0)
        if self.state_path is not None:
            with closing(self._db()) as db:
                row = db.execute("SELECT evaluations FROM usage WHERE client_id = ? AND day = ?", (client_id, day)).fetchone()
            used = row[0] if row else 0
        return max(0, policy.daily_evaluation_budget - used)

    def _log(self, client_id: str | None, outcome: str, evaluations: int) -> None:
        # Who asked, when, how many probes, and the outcome — never what.
        entry = {"ts": time.time(), "client_id": client_id, "outcome": outcome, "evaluations": evaluations}
        self.audit.append(entry)
        if self.state_path is not None:
            with closing(self._db()) as db:
                db.execute("INSERT INTO audit VALUES (?, ?, ?, ?)", (entry["ts"], client_id, outcome, evaluations))


# --- allow-list file -----------------------------------------------------------
#
# {"clients": {"<client_id>": {"key_hex": "...", "daily_evaluation_budget": 200}}}
# Absent file = open node (the prototype's behaviour, stated in docs/43).


def load_authorizer(node_id: str, path: Path, state_path: Path | None = None) -> Authorizer | None:
    """`state_path`: where the budget counter and audit log persist (the MCP
    node passes `<node>.usage.sqlite`); None keeps them in memory."""
    if not path.exists():
        return None
    spec = json.loads(path.read_text())
    policies = {
        cid: ClientPolicy(key=bytes.fromhex(entry["key_hex"]), daily_evaluation_budget=int(entry["daily_evaluation_budget"]),
                          roles=tuple(entry.get("roles", ())))
        for cid, entry in spec.get("clients", {}).items()
    }
    return Authorizer(node_id=node_id, policies=policies, state_path=state_path)


def write_allow_list(path: Path, clients: dict[str, ClientPolicy]) -> None:
    path.write_text(json.dumps({"clients": {
        cid: {"key_hex": p.key.hex(), "daily_evaluation_budget": p.daily_evaluation_budget, "roles": list(p.roles)}
        for cid, p in clients.items()
    }}, indent=2))
    path.chmod(0o600)


def new_credential(client_id: str, roles: tuple[str, ...] = ()) -> Credential:
    return Credential(client_id=client_id, key=os.urandom(32), roles=tuple(roles))


# --- role-based access to document collections (docs/45) ------------------------
#
# A node holds its documents in named collections ("public", "research",
# "clinical_notes", ...). Its access policy — role -> collections — is part of
# its signed profile, so every client can see what each role may read. Which
# roles a CLIENT holds is in the node's allow-list, issued by the federation;
# the client cannot claim a role. "public" is readable by any authorised
# client and, on an open node (no allow-list), by anyone. A restricted
# collection on an open node is readable by no one.

PUBLIC = "public"


def permitted_collections(access_policy: dict[str, list[str]] | None, roles: tuple[str, ...] | list[str],
                          available: list[str], *, authorised: bool) -> list[str]:
    allowed = {PUBLIC}
    if authorised:
        for role in roles:
            allowed.update((access_policy or {}).get(role, []))
    return sorted(c for c in available if c in allowed)
