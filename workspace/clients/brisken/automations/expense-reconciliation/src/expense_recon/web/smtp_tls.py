"""STARTTLS material for the intake listener (backlog item 125).

Until 2026-09-18 the mailbox answered `454 TLS not available`, so a sender
doing opportunistic TLS (Exchange Online's outbound default) fell back to
cleartext for this domain and every receipt crossed the public internet
readable. The listener now offers STARTTLS with a certificate it makes for
itself on the data volume; a CA-issued pair drops in through the two env
overrides below without a code change.

Opportunistic on purpose (`require_starttls=False` in smtp_server.py): a
sender that cannot do TLS must still deliver a receipt, and forcing it
would bounce mail, which is worse than a cleartext receipt. Whether a
session was encrypted is recorded on the receipt (`transport_tls`) so the
operator can see who still delivers in the clear.

Self-signed means a sender that VERIFIES the certificate (rare for MX
delivery; Exchange Online's opportunistic mode does not) refuses the
handshake and, being opportunistic, retries in cleartext, which is today's
behaviour, not a regression. The remaining step is a CA certificate (Let's
Encrypt via DNS-01 on the registrar API; see README), not built here.

Fail-open throughout: no openssl binary, a generation failure, an unreadable
pair, all log a warning and return None, and the listener stays plaintext,
exactly what it was before this module existed. A crash here would take the
mailbox down with it.
"""
from __future__ import annotations

import logging
import os
import shutil
import ssl
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("expense_recon.intake")

DEFAULT_HOSTNAME = "mx.expenses.brisken.com"
CERT_DAYS = 825            # the leaf-certificate ceiling browsers enforce; ample for an MX
RENEW_WITHIN_DAYS = 30     # regenerate when less than this is left
ENV_CERT = "EXPENSE_RECON_SMTP_TLS_CERT"
ENV_KEY = "EXPENSE_RECON_SMTP_TLS_KEY"


def _openssl() -> str | None:
    return shutil.which("openssl")


def _x509(openssl: str, cert: Path, *args: str) -> str | None:
    """`openssl x509 -noout <args> -in cert` stdout, or None on any failure."""
    try:
        return subprocess.run(
            [openssl, "x509", "-noout", *args, "-in", str(cert)],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def cert_not_after(cert: Path, openssl: str | None = None) -> datetime | None:
    """Expiry of a PEM certificate as an aware UTC datetime, or None when it
    cannot be read.

    Read with the openssl binary (`x509 -enddate`), which the generator
    needs anyway, and parsed by `ssl.cert_time_to_seconds`, the public,
    locale-independent parser for exactly this `notAfter` format. The
    alternative, `ssl._ssl._test_decode_cert`, needs no binary but is a
    private CPython hook, so the binary route is the one that stays
    reliable across Python releases."""
    exe = openssl or _openssl()
    if exe is None:
        return None
    out = _x509(exe, cert, "-enddate")
    if out is None:
        return None
    line = out.strip()
    if not line.startswith("notAfter="):
        return None
    try:
        secs = ssl.cert_time_to_seconds(line[len("notAfter="):].strip())
    except ValueError:
        return None
    return datetime.fromtimestamp(secs, tz=timezone.utc)


def cert_summary(cert: Path, openssl: str | None = None) -> dict:
    """{subject_cn, issuer_cn, self_signed, not_after} for the startup line;
    every field best-effort ("" / None when unreadable)."""
    exe = openssl or _openssl()
    subject_cn = issuer_cn = ""
    if exe is not None:
        out = _x509(exe, cert, "-subject", "-issuer", "-nameopt", "RFC2253") or ""
        for raw in out.splitlines():
            label, _, value = raw.partition("=")
            cn = ""
            if "CN=" in value:
                cn = value.split("CN=", 1)[1].split(",", 1)[0].strip()
            if label.strip() == "subject":
                subject_cn = cn
            elif label.strip() == "issuer":
                issuer_cn = cn
    return {
        "subject_cn": subject_cn,
        "issuer_cn": issuer_cn,
        "self_signed": bool(subject_cn) and subject_cn == issuer_cn,
        "not_after": cert_not_after(cert, exe),
    }


def describe(cert: Path) -> str:
    """`self-signed, CN=mx.expenses.brisken.com, expires 2028-12-21` for
    the log line; a CA-issued pair reads `issued by <CN>` instead."""
    s = cert_summary(cert)
    kind = "self-signed" if s["self_signed"] else f"issued by {s['issuer_cn'] or 'unknown'}"
    expires = f"{s['not_after']:%Y-%m-%d}" if s["not_after"] else "unknown"
    return f"{kind}, CN={s['subject_cn'] or 'unknown'}, expires {expires}"


def _needs_regeneration(cert: Path, key: Path, openssl: str) -> str | None:
    """None when the pair on disk is usable; else the reason to regenerate."""
    if not cert.is_file() or not key.is_file():
        return "no certificate on the volume"
    try:
        cert.read_bytes()
        key.read_bytes()
    except OSError as exc:
        return f"pair unreadable: {exc}"
    not_after = cert_not_after(cert, openssl)
    if not_after is None:
        return "certificate expiry cannot be read"
    if not_after - datetime.now(timezone.utc) < timedelta(days=RENEW_WITHIN_DAYS):
        return (
            f"certificate expires {not_after:%Y-%m-%d} "
            f"(within {RENEW_WITHIN_DAYS} days)"
        )
    return None


def _generate(openssl: str, tls_dir: Path, hostname: str, days: int) -> None:
    """Write a fresh self-signed pair into tls_dir. Generated under temp
    names and moved into place, so a crash mid-way never leaves a
    half-written pair for the next start to load."""
    tls_dir.mkdir(parents=True, exist_ok=True)
    key_tmp = tls_dir / "key.pem.tmp"
    cert_tmp = tls_dir / "cert.pem.tmp"
    for p in (key_tmp, cert_tmp):
        p.unlink(missing_ok=True)
    subprocess.run(
        [
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-days", str(days),
            "-keyout", str(key_tmp), "-out", str(cert_tmp),
            "-subj", f"/CN={hostname}",
            "-addext", f"subjectAltName=DNS:{hostname}",
        ],
        capture_output=True, text=True, timeout=120, check=True,
    )
    try:
        os.chmod(key_tmp, 0o600)  # best effort: Windows keeps only the write bit
    except OSError:
        pass
    os.replace(key_tmp, tls_dir / "key.pem")
    os.replace(cert_tmp, tls_dir / "cert.pem")


def env_pair() -> tuple[Path, Path] | None:
    """The operator-supplied pair (both env vars set and both files present),
    else None. One var alone is a misconfiguration: logged, then ignored."""
    env_cert = os.environ.get(ENV_CERT, "").strip()
    env_key = os.environ.get(ENV_KEY, "").strip()
    if not env_cert and not env_key:
        return None
    if not (env_cert and env_key):
        log.warning(
            "intake SMTP STARTTLS: only one of %s / %s is set; both are "
            "needed, using the generated pair instead", ENV_CERT, ENV_KEY,
        )
        return None
    cert, key = Path(env_cert), Path(env_key)
    if not (cert.is_file() and key.is_file()):
        log.warning(
            "intake SMTP STARTTLS: %s / %s point at missing files (%s, %s); "
            "using the generated pair instead", ENV_CERT, ENV_KEY, cert, key,
        )
        return None
    return cert, key


def ensure_cert(
    data_root: Path, hostname: str = DEFAULT_HOSTNAME, *, days: int = CERT_DAYS,
) -> tuple[Path, Path] | None:
    """(cert.pem, key.pem) the listener can load, or None (stay plaintext).

    Order: the env pair when both vars are set (a CA-issued certificate,
    skipped generation); else `<data_root>/tls/{cert,key}.pem`, generated
    when missing, unreadable, or inside its last RENEW_WITHIN_DAYS. `days`
    is the validity of a NEW pair (tests shorten it to prove renewal)."""
    pair = env_pair()
    if pair is not None:
        return pair
    openssl = _openssl()
    if openssl is None:
        log.warning("intake SMTP STARTTLS off: no openssl binary on PATH")
        return None
    tls_dir = Path(data_root) / "tls"
    cert, key = tls_dir / "cert.pem", tls_dir / "key.pem"
    reason = _needs_regeneration(cert, key, openssl)
    if reason is None:
        return cert, key
    log.info("intake SMTP STARTTLS: generating a self-signed certificate (%s)", reason)
    try:
        _generate(openssl, tls_dir, hostname, days)
    except (OSError, subprocess.SubprocessError) as exc:
        detail = (getattr(exc, "stderr", "") or str(exc)).strip()
        log.warning("intake SMTP STARTTLS off: certificate generation failed: %s", detail)
        return None
    # Read the fresh pair back for existence and a parseable expiry only, NOT
    # the renew window: a deliberately short-lived cert (a `days=1` renewal
    # test) is inside the window by construction and must still be returned.
    if not (cert.is_file() and key.is_file() and cert_not_after(cert, openssl) is not None):
        log.warning("intake SMTP STARTTLS off: the generated pair does not read back")
        return None
    return cert, key


def server_context(cert: Path, key: Path) -> ssl.SSLContext:
    """The STARTTLS context: server side, TLS 1.2 or newer, no client
    certificates (an MX never asks for one). Raises on a bad pair; the
    caller logs and stays plaintext."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=str(cert), keyfile=str(key))
    return ctx
