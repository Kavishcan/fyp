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
import time
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
    """Client side. `key` is the shared secret issued by the federation."""
    client_id: str
    key: bytes

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


@dataclass
class Authorizer:
    """Node side. Allow-list + per-client per-day evaluation counter + audit."""
    node_id: str
    policies: dict[str, ClientPolicy] = field(default_factory=dict)
    usage: dict[tuple[str, str], int] = field(default_factory=dict)   # (client_id, day) -> evaluations
    audit: list[dict] = field(default_factory=list)

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
        used = self.usage.get((client_id, day), 0)
        if used + len(blinded) > policy.daily_evaluation_budget:
            self._log(client_id, "budget_exhausted", len(blinded))
            raise Unauthorized("budget_exhausted")
        self.usage[(client_id, day)] = used + len(blinded)
        self._log(client_id, "ok", len(blinded))
        return client_id

    def remaining(self, client_id: str, now: float | None = None) -> int:
        policy = self.policies.get(client_id)
        if policy is None:
            return 0
        return max(0, policy.daily_evaluation_budget - self.usage.get((client_id, utc_day(now)), 0))

    def _log(self, client_id: str | None, outcome: str, evaluations: int) -> None:
        # Who asked, when, how many probes, and the outcome — never what.
        self.audit.append({"ts": time.time(), "client_id": client_id, "outcome": outcome, "evaluations": evaluations})


# --- allow-list file -----------------------------------------------------------
#
# {"clients": {"<client_id>": {"key_hex": "...", "daily_evaluation_budget": 200}}}
# Absent file = open node (the prototype's behaviour, stated in docs/43).


def load_authorizer(node_id: str, path: Path) -> Authorizer | None:
    if not path.exists():
        return None
    spec = json.loads(path.read_text())
    policies = {
        cid: ClientPolicy(key=bytes.fromhex(entry["key_hex"]), daily_evaluation_budget=int(entry["daily_evaluation_budget"]))
        for cid, entry in spec.get("clients", {}).items()
    }
    return Authorizer(node_id=node_id, policies=policies)


def write_allow_list(path: Path, clients: dict[str, ClientPolicy]) -> None:
    path.write_text(json.dumps({"clients": {
        cid: {"key_hex": p.key.hex(), "daily_evaluation_budget": p.daily_evaluation_budget} for cid, p in clients.items()
    }}, indent=2))
    path.chmod(0o600)


def new_credential(client_id: str) -> Credential:
    return Credential(client_id=client_id, key=os.urandom(32))
