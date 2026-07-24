"""Login throttle for the one code that guards Brisken's bank statements.

`POST /api/login` is the entire security boundary on this app: a single
shared operator code, no second factor, no per-user accounts. Until this
module there was nothing between an attacker and unlimited guesses at it.

Two tiers, because one is not enough HERE specifically:

* **Per-IP** — N failures inside a window locks that caller out, with the
  lockout doubling for every further failure. This is the tier that stops
  an ordinary online guessing run. The address has to come from the
  ``Fly-Client-IP`` header: the container runs uvicorn without
  ``--proxy-headers``, so ``request.client.host`` is Fly's own proxy
  (``fdaa:``…, identical for every caller in the world) and keying on it
  would collapse all callers into one bucket — meaning any attacker could
  lock the operator out. Verified against the live app 2026-07-22: Fly's
  proxy OVERWRITES a client-supplied ``Fly-Client-IP``, so the value is
  the real peer and cannot be forged.
* **Global** — a much larger budget of failures across ALL callers inside
  the same window. Forging the header is not the gap this covers; address
  ROTATION is. A caller on IPv6 typically holds a whole /64 (or wider), so
  keying on a bare /128 would hand them an unlimited supply of fresh
  buckets. `client_ip` therefore keys IPv6 on its /64 prefix, and the
  global budget catches what is left: a wider allocation, or a genuinely
  distributed attack.

Only FAILED attempts are recorded, and a success clears the caller's
record, so the legitimate operator never walks into a lockout by using
the tool. The global tier can delay a legitimate login while an attack is
in progress; the threshold is set far above human-typo volume and the
lockout is short, which is the right trade against an open door.

The gate is a no-op when the password gate itself is off (local loopback
dev, no operator code set): there is no secret to brute force.

Env vars (all optional; defaults are the shipped policy):
    EXPENSE_RECON_LOGIN_RATELIMIT     "0" disables the throttle entirely
    EXPENSE_RECON_LOGIN_MAX_ATTEMPTS  per-IP failures allowed  (default 5)
    EXPENSE_RECON_LOGIN_WINDOW        window seconds           (default 900)
    EXPENSE_RECON_LOGIN_LOCKOUT       base lockout seconds     (default 60)
    EXPENSE_RECON_LOGIN_LOCKOUT_CAP   max lockout seconds      (default 3600)
    EXPENSE_RECON_LOGIN_GLOBAL_MAX    global failures allowed  (default 50)
    EXPENSE_RECON_LOGIN_GLOBAL_LOCKOUT  global lockout seconds (default 300)
"""
from __future__ import annotations

import ipaddress
import math
import os
from dataclasses import dataclass

# Cap the stored identity so a hostile header cannot bloat the table.
_MAX_KEY_LEN = 64

# An IPv6 caller is bucketed by prefix, not by address: a single end site
# normally holds a /64, so keying on the /128 would give one attacker 2**64
# fresh buckets. IPv4 is keyed on the full address.
_IPV6_PREFIX = 64


@dataclass(frozen=True)
class Policy:
    max_attempts: int = 5
    window: int = 900
    lockout: int = 60
    lockout_cap: int = 3600
    global_max: int = 50
    global_lockout: int = 300


@dataclass(frozen=True)
class Verdict:
    """`allowed` False means answer 429 and do not check the code."""

    allowed: bool
    retry_after: int = 0
    scope: str = ""  # "ip" | "global" when denied


ALLOW = Verdict(allowed=True)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def enabled() -> bool:
    return os.environ.get("EXPENSE_RECON_LOGIN_RATELIMIT", "1").strip() != "0"


def policy() -> Policy:
    return Policy(
        max_attempts=_env_int("EXPENSE_RECON_LOGIN_MAX_ATTEMPTS", 5),
        window=_env_int("EXPENSE_RECON_LOGIN_WINDOW", 900),
        lockout=_env_int("EXPENSE_RECON_LOGIN_LOCKOUT", 60),
        lockout_cap=_env_int("EXPENSE_RECON_LOGIN_LOCKOUT_CAP", 3600),
        global_max=_env_int("EXPENSE_RECON_LOGIN_GLOBAL_MAX", 50),
        global_lockout=_env_int("EXPENSE_RECON_LOGIN_GLOBAL_LOCKOUT", 300),
    )


def bucket_key(raw: str) -> str:
    """The throttle bucket for a caller address.

    IPv6 collapses to its /64 prefix so one end site is one bucket; IPv4
    keeps the full address. Anything unparseable is used verbatim (local
    dev sends things like ``testclient``), truncated so a hostile value
    cannot bloat the table.
    """
    candidate = raw.strip()
    if not candidate:
        return "unknown"
    try:
        addr = ipaddress.ip_address(candidate)
    except ValueError:
        return candidate[:_MAX_KEY_LEN]
    if addr.version == 6:
        net = ipaddress.IPv6Network(f"{addr}/{_IPV6_PREFIX}", strict=False)
        return str(net)
    return str(addr)


def client_ip(request) -> str:
    """Best available caller identity, as a throttle bucket.

    ``Fly-Client-IP`` first (Fly's proxy sets it, and overwrites any
    client-supplied value; without it every hosted caller would collapse
    into the proxy's own address), then the first hop of
    ``X-Forwarded-For``, then the socket peer for local/dev use.
    """
    headers = getattr(request, "headers", None)
    if headers is not None:
        for header in ("fly-client-ip", "x-forwarded-for"):
            raw = headers.get(header)
            if raw:
                first = raw.split(",")[0].strip()
                if first:
                    return bucket_key(first)
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client else None
    return bucket_key(host or "unknown")


def _lock_seconds(failures: int, pol: Policy) -> int:
    """Lockout for `failures` recorded failures: base, doubling for each
    failure past the allowance, capped."""
    over = max(0, failures - pol.max_attempts)
    # Bound the exponent before shifting so a long attack cannot build a
    # pathologically large intermediate.
    if over > 32:
        return pol.lockout_cap
    return min(pol.lockout * (2**over), pol.lockout_cap)


def evaluate(store, ip: str, now: float, pol: Policy | None = None) -> Verdict:
    """Whether this caller may attempt a code right now.

    Read-only with respect to the attempt itself: recording a failure is
    `register_failure`, clearing on success is `register_success`.
    """
    if not enabled():
        return ALLOW
    pol = pol or policy()
    since = now - pol.window
    store.prune_login_failures(since)

    n_ip, last_ip = store.login_failure_stats(since, ip=ip)
    if n_ip >= pol.max_attempts:
        remaining = (last_ip + _lock_seconds(n_ip, pol)) - now
        if remaining > 0:
            return Verdict(False, max(1, math.ceil(remaining)), "ip")

    n_all, last_all = store.login_failure_stats(since)
    if n_all >= pol.global_max:
        remaining = (last_all + pol.global_lockout) - now
        if remaining > 0:
            return Verdict(False, max(1, math.ceil(remaining)), "global")

    return ALLOW


def register_failure(store, ip: str, now: float) -> None:
    if enabled():
        store.record_login_failure(ip, now)


def register_success(store, ip: str) -> None:
    """A correct code clears that caller's failures, so an operator who
    fat-fingers the code a few times and then gets it right starts clean."""
    if enabled():
        store.clear_login_failures(ip)


def denial_body(verdict: Verdict) -> dict:
    return {
        "error": "too many login attempts",
        "retry_after": verdict.retry_after,
        "scope": verdict.scope,
    }
