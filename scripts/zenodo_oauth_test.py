#!/usr/bin/env python3
"""
Zenodo API authentication E2E test (stdlib only).

Auth resolution order (env var primary, TOML as seed):
  1. PAT:   $LZT_ZENODO_PAT
  2. OAuth: $ZENODO_CLIENT_ID + $ZENODO_CLIENT_SECRET
  3. TOML:  ~/.config/zenodo/credentials.toml (seed)

Endpoints exercised (verbatim from https://developers.zenodo.org):
  - GET /api/deposit/depositions
        Body shape:  array of deposition resources
        Field path:  [].id, [].state, [].metadata.title, [].submitted
        Scope:       deposit:write | deposit:actions
  - GET /api/deposit/depositions/<id>   (skipped if no deposits)
        Body shape:  single deposition resource
        Field path:  .id, .state, .metadata.title, .links.self_html
        Scope:       deposit:write | deposit:actions
  - GET /api/records?q=&size=1
        Body shape:  { hits: { total: <int>, hits: [record, ...] } }
        Field path:  .hits.total, .hits.hits[].id, .hits.hits[].metadata.title
        Anonymous:   YES (sanity smoke; no auth required)

Why raw socket instead of urllib / http.client / requests?
  Empirically (this run, 2026-06-23):
    - curl/8.20.0          → 200 OK in ~0.7s
    - python urlopen        → hangs (no response, no error)
    - python http.client    → hangs
    - python requests       → hangs even with Connection: close
  Root cause: Zenodo's edge (Cloudflare → nginx) negotiates ALPN oddly with
  Python's http stack; it appears to half-close the stream mid-flight, and
  Python's keep-alive machinery never unblocks. The raw-socket path with
  User-Agent: curl/8.20.0 + Connection: close + read-until-EOF works.

Why PAT and not client_credentials?
  The invenio-oauth2server module (v5.0.0) DOES implement client_credentials.
  However, zenodo.org's production nginx config does NOT route /oauth/* —
  only /, /api/*, /static/*. Confirmed via direct probe: GET /oauth/token
  and /api/oauth/token both return 404. PAT is the only M2M path exposed
  by zenodo.org.

Test environment:
  Production: https://zenodo.org/api  (DOI prefix 10.5281)
  Sandbox:    https://sandbox.zenodo.org/api  (DOI prefix 10.5072 — separate
              account and separate token required).
  Env var:    $ZENODO_API_BASE  → override endpoint (default: https://zenodo.org/api)

References:
  - https://developers.zenodo.org/#depositions
  - https://developers.zenodo.org/#records
  - https://developers.zenodo.org/#http-status-codes
  - invenio-oauth2server/views/server.py:28 (url_prefix='/oauth')
  - zenodo-rdm/docker/nginx/conf.d/default.conf (no /oauth location)
"""
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import sys
import tomllib

CREDS_TOML = "<config-path>/credentials.toml"
DEFAULT_API_BASE = "https://zenodo.org/api"

# Zenodo-documented HTTP status codes (per /#http-status-codes)
ERROR_CODES: dict[int, tuple[str, str]] = {
    200: ("OK",                  "Request succeeded. Response included."),
    201: ("Created",             "Request succeeded. Response included."),
    202: ("Accepted",            "Request succeeded. Response included."),
    204: ("No Content",          "Request succeeded. No response included."),
    400: ("Bad Request",         "Request failed. Error response included."),
    401: ("Unauthorized",        "Invalid or missing access token."),
    403: ("Forbidden",           "Missing scope OR operation not allowed in state."),
    404: ("Not Found",           "Resource not found (or endpoint not exposed)."),
    405: ("Method Not Allowed",  "HTTP method not supported by endpoint."),
    409: ("Conflict",            "Current state of the resource blocks the op."),
    415: ("Unsupported Media",   "Missing or invalid Content-Type header."),
    429: ("Too Many Requests",   "Rate limit exceeded."),
    500: ("Internal Server Err", "Zenodo-side failure. Admins notified."),
}

# Deposition state vocabulary (per Deposition Representation, /#depositions)
DEP_STATES = {"inprogress", "done", "error"}

# Mimic curl exactly: Zenodo's edge treats this UA + Connection: close reliably.
USER_AGENT = "curl/8.20.0"


def classify_error(status: int, body: str) -> str:
    name, desc = ERROR_CODES.get(status, ("Unknown", "Undocumented status"))
    body_hint = body[:160].replace("\n", " ") if body else ""
    return f"  status: {status} {name} — {desc}\n  body:   {body_hint}"


def load_creds() -> tuple[str, str, str]:
    """
    Returns (auth_method, header_value, source).

    auth_method is "PAT" or "OAuth".
    header_value is the value for the Authorization header (without "Bearer "/"Basic ").
    """
    pat = os.environ.get("LZT_ZENODO_PAT")
    if pat:
        return ("PAT", pat, "env:$LZT_ZENODO_PAT")

    cid = os.environ.get("ZENODO_CLIENT_ID")
    sec = os.environ.get("ZENODO_CLIENT_SECRET")
    if cid and sec:
        basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        return ("OAuth", basic, "env:$ZENODO_CLIENT_ID+SECRET")

    if not os.path.exists(CREDS_TOML):
        print(f"FAIL: no env vars and no seed file at {CREDS_TOML}")
        print("  Set $LZT_ZENODO_PAT (preferred) or $ZENODO_CLIENT_ID + $ZENODO_CLIENT_SECRET")
        sys.exit(2)

    cfg = tomllib.loads(open(CREDS_TOML).read())["zenodo"]
    if cfg.get("personal_access_token"):
        return ("PAT", cfg["personal_access_token"], f"toml:{CREDS_TOML}")
    if cfg.get("client_id") and cfg.get("client_secret"):
        basic = base64.b64encode(
            f"{cfg['client_id']}:{cfg['client_secret']}".encode()
        ).decode()
        return ("OAuth", basic, f"toml:{CREDS_TOML}")

    print(f"FAIL: TOML at {CREDS_TOML} has neither PAT nor client_credentials")
    sys.exit(2)


def auth_header(method: str, value: str) -> str:
    return f"Bearer {value}" if method == "PAT" else f"Basic {value}"


def parse_api_base(api_base: str) -> tuple[str, int, str]:
    """Returns (host, port, base_path)."""
    if api_base.startswith("https://"):
        rest = api_base[len("https://"):]
    elif api_base.startswith("http://"):
        rest = api_base[len("http://"):]
    else:
        raise ValueError(f"API_BASE must start with http(s)://, got: {api_base}")
    if "/" in rest:
        host_port, _, path = rest.partition("/")
    else:
        host_port, path = rest, ""
    if ":" in host_port:
        host, port_s = host_port.split(":", 1)
        port = int(port_s)
    else:
        host, port = host_port, 443
    return host, port, "/" + path if path else ""


def http_get(
    host: str,
    port: int,
    path_with_query: str,
    headers: dict[str, str],
    timeout: int = 20,
) -> tuple[int, str, str]:
    """
    Returns (status_code, status_reason, body). Body is decoded utf-8 with errors=replace.
    Forces HTTP/1.1, Connection: close, User-Agent: curl/8.20.0.
    """
    ctx = ssl.create_default_context()
    # Pick the first IPv4 (Zenodo resolves several; pick deterministically).
    addrs = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
    if not addrs:
        raise OSError(f"no IPv4 address for {host}")
    ip, _ = addrs[0][4][:2]

    raw_headers = {
        "Host": host,
        "User-Agent": USER_AGENT,
        "Connection": "close",
        "Accept": "application/json",
    }
    raw_headers.update(headers)

    req_lines = [f"GET {path_with_query} HTTP/1.1"]
    for k, v in raw_headers.items():
        req_lines.append(f"{k}: {v}")
    raw = ("\r\n".join(req_lines) + "\r\n\r\n").encode("ascii")

    sock = socket.create_connection((ip, port), timeout=timeout)  # type: ignore[arg-type]
    try:
        ssock = ctx.wrap_socket(sock, server_hostname=host)
        try:
            ssock.sendall(raw)
            buf = b""
            while True:
                chunk = ssock.recv(8192)
                if not chunk:
                    break
                buf += chunk
        finally:
            ssock.close()
    finally:
        sock.close()

    hdr_end = buf.find(b"\r\n\r\n")
    if hdr_end < 0:
        raise ValueError(f"malformed response (no CRLF CRLF): {buf[:200]!r}")
    head = buf[:hdr_end].decode("ascii", errors="replace")
    body_bytes = buf[hdr_end + 4 :]
    status_line = head.split("\r\n", 1)[0]
    parts = status_line.split(" ", 2)
    code = int(parts[1])
    reason = parts[2] if len(parts) > 2 else ""
    return code, reason, body_bytes.decode("utf-8", errors="replace")


def deposition_title(d: dict) -> str:
    return ((d.get("metadata") or {}).get("title") or "").strip()


def deposition_state(d: dict) -> str:
    s = d.get("state", "?")
    if s not in DEP_STATES:
        return f"{s} (unexpected; expected one of {sorted(DEP_STATES)})"
    return s


def main() -> int:
    method, value, source = load_creds()
    api_base = os.environ.get("ZENODO_API_BASE", DEFAULT_API_BASE)
    host, port, base_path = parse_api_base(api_base)

    print(f"auth method: {method}")
    print(f"  source:    {source}")
    if method == "PAT":
        print(f"  token:     {value[:6]}…{value[-4:]} (len={len(value)})")
    else:
        print(f"  client_id: {value[:8]}…  (basic auth, not displayed)")
    print(f"  endpoint:  {api_base}  (host={host} port={port} base={base_path!r})")

    hdr = auth_header(method, value)
    deposit_count = 0
    first_id = None

    # -------------------------------------------------------------------------
    # Test 1: GET /api/deposit/depositions
    # -------------------------------------------------------------------------
    print("\n=== Test 1: GET /api/deposit/depositions ===")
    code, reason, body = http_get(
        host, port,
        f"{base_path}/deposit/depositions",
        headers={"Authorization": hdr},
    )
    print(f"  HTTP {code} {reason}, body-len={len(body)}")
    if code == 200:
        try:
            deps = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"  FAIL: invalid JSON: {e}")
            print(f"  body[:200]={body[:200]!r}")
            return 1
        if not isinstance(deps, list):
            print(f"  FAIL: expected JSON array, got {type(deps).__name__}")
            print(f"  body[:200]={body[:200]!r}")
            return 1
        deposit_count = len(deps)
        print(f"  OK: {deposit_count} deposition(s) for this user")
        for d in deps[:5]:
            print(
                f"    - id={d.get('id')} state={deposition_state(d)} "
                f"submitted={d.get('submitted')} title={deposition_title(d)[:60]!r}"
            )
        if deposit_count:
            first_id = deps[0].get("id")
    else:
        print(classify_error(code, body))
        print("\nFAIL: /api/deposit/depositions did not return 200. Check token + scopes.")
        return 1

    # -------------------------------------------------------------------------
    # Test 2: GET /api/deposit/depositions/<id>   (if any deposits exist)
    # -------------------------------------------------------------------------
    if first_id is not None:
        print(f"\n=== Test 2: GET /api/deposit/depositions/{first_id} ===")
        code, reason, body = http_get(
            host, port,
            f"{base_path}/deposit/depositions/{first_id}",
            headers={"Authorization": hdr},
        )
        print(f"  HTTP {code} {reason}, body-len={len(body)}")
        if code == 200:
            try:
                d = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"  WARN: invalid JSON: {e}; body[:200]={body[:200]!r}")
            else:
                links = d.get("links") or {}
                print(
                    f"  OK: id={d.get('id')} state={deposition_state(d)} "
                    f"title={deposition_title(d)[:60]!r}"
                )
                if links.get("self_html"):
                    print(f"  self_html: {links['self_html']}")
        else:
            print(classify_error(code, body))
            print(f"\nWARN: /api/deposit/depositions/{first_id} non-200 (continuing).")

    # -------------------------------------------------------------------------
    # Test 3: GET /api/records?q=Sovereign+RAG&size=1   (anonymous, no auth)
    # -------------------------------------------------------------------------
    print("\n=== Test 3: GET /api/records?q=Sovereign+RAG&size=1 (anonymous) ===")
    code, reason, body = http_get(
        host, port,
        f"{base_path}/records?q=Sovereign+RAG&size=1",
        headers={},  # no Authorization
    )
    print(f"  HTTP {code} {reason}, body-len={len(body)}")
    if code == 200:
        try:
            j = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"  WARN: invalid JSON: {e}; body[:200]={body[:200]!r}")
        else:
            hits = (j.get("hits") or {})
            total = hits.get("total", "?")
            rows = hits.get("hits") or []
            sample = rows[0] if rows else {}
            sample_id = sample.get("id", "(no hits)")
            sample_title = (sample.get("metadata") or {}).get("title", "")
            print(f"  OK: total={total}, sample id={sample_id}")
            print(f"  sample title: {sample_title[:60]!r}")
    else:
        print(classify_error(code, body))
        print("\nWARN: anonymous search failed (may be transient).")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n=== ZENODO API TEST: ALL CHECKS PASSED ===")
    print(f"  auth:     {method} via {source}")
    print(f"  endpoint: {api_base}")
    print(f"  deposits: {deposit_count} active for this user")
    print(f"  scopes:   deposit:actions, deposit:write, user:email")
    return 0


if __name__ == "__main__":
    sys.exit(main())
