# scripts/ — Operational E2E checks

This folder holds scripts that exercise the verification surface
against **live external systems**. The auditors in `../auditors/`
are hermetic (no network); the scripts here are not. They exist to
prove that the verification suite's claim of reproducibility extends
to the publication step (Zenodo deposit, OAuth handshake).

There is currently **one script** in this folder:

- `zenodo_oauth_test.py` — End-to-end authentication + deposits
  listing test against the Zenodo REST API.

## What `zenodo_oauth_test.py` does

The script runs three HTTP/1.1 GET requests against the Zenodo
REST API and verifies the response shape and status:

| Test | Endpoint | Auth | Verifies |
| --- | --- | --- | --- |
| 1 | `GET /api/deposit/depositions` | `Bearer` PAT or `Basic` OAuth | Returns 200 + JSON array; lists up to 5 deposition summaries (id, state, submitted, title). |
| 2 | `GET /api/deposit/depositions/<id>` | Same | Returns 200 for the first deposition; prints `self_html` link. Skipped if the user has zero deposits. |
| 3 | `GET /api/records?q=Sovereign+RAG&size=1` | None (anonymous) | Returns 200 + `{hits: {total, hits: [...]}}`; prints total count and the first hit's id and title. |

Test 3 is the **anonymous smoke test**: it does not require any
credential and serves as a sanity check that the API is reachable
from the host. Tests 1 and 2 require a valid token with
`deposit:actions` and `deposit:write` scopes.

## Why raw socket

The script deliberately avoids `urllib`, `http.client`, and
`requests`. The full rationale is documented inline at
`zenodo_oauth_test.py:24-33`; the short version is:

- `urllib.request.urlopen` hangs against Zenodo's edge (no
  response, no error, no timeout).
- `http.client.HTTPSConnection` hangs for the same reason.
- `requests` hangs even with `Connection: close` set explicitly.
- `curl/8.20.0` returns in ~0.7 s.

The root cause is Zenodo's Cloudflare → nginx edge negotiating ALPN
oddly with Python's HTTP stack; the stream half-closes mid-flight
and Python's keep-alive machinery never unblocks. The script works
around this by:

1. Opening a raw `socket` (with `ssl.SSLContext.wrap_socket`).
2. Sending an HTTP/1.1 request with `User-Agent: curl/8.20.0` and
   `Connection: close`.
3. Reading until EOF (no keep-alive), with a 15-second deadline on
   the connect and read.

This pattern is operator-verified; see the comments at
`zenodo_oauth_test.py:88-89` for the User-Agent string and at
`zenodo_oauth_test.py:92-95` for the error classifier.

## Why PAT and not client_credentials

The script accepts either a Personal Access Token (PAT) or OAuth
client credentials, but the de facto path against
`zenodo.org` (not `sandbox.zenodo.org`) is PAT only. Zenodo's
`invenio-oauth2server` module does implement `client_credentials`,
but the production nginx config does not route `/oauth/*` — it only
serves `/`, `/api/*`, and `/static/*`. A direct probe to
`GET /oauth/token` and `/api/oauth/token` returns 404. See the
inline rationale at `zenodo_oauth_test.py:35-40`.

## Auth resolution order

The script resolves credentials in this strict order:

1. `$LZT_ZENODO_PAT` (environment variable) — preferred.
2. `$ZENODO_CLIENT_ID` + `$ZENODO_CLIENT_SECRET` (environment
   variables) — OAuth basic auth.
3. `<config-path>/credentials.toml` — TOML seed file with the same
   two fields (`personal_access_token` or `client_id` +
   `client_secret`).

If neither path resolves, the script prints `FAIL: no env vars and
no seed file at <path>` and **exits 2** without making any network
request. The TOML path is a placeholder in the public source
(`<config-path>` is not expanded; it is a literal string the
operator overrides locally).

The endpoint can be overridden via `$ZENODO_API_BASE` (default
`https://zenodo.org/api`). The sandbox URL is
`https://sandbox.zenodo.org/api` (DOI prefix `10.5072`; requires a
separate token).

## Output format

The script prints to stdout in this shape:

```
auth method: PAT
  source:    env:$LZT_ZENODO_PAT
  token:     abc123…wxyz (len=86)
  endpoint:  https://zenodo.org/api  (host=zenodo.org port=443 base='/api')

=== Test 1: GET /api/deposit/depositions ===
  HTTP 200 OK, body-len=4128
  OK: 3 deposition(s) for this user
    - id=12345 state=inprogress submitted=False title='…'
    …

=== Test 2: GET /api/deposit/depositions/12345 ===
  HTTP 200 OK, body-len=1820
  OK: id=12345 state=inprogress title='…'
  self_html: https://zenodo.org/deposit/12345

=== Test 3: GET /api/records?q=Sovereign+RAG&size=1 (anonymous) ===
  HTTP 200 OK, body-len=720
  OK: total=1, sample id=…
  sample title: …

=== ZENODO API TEST: ALL CHECKS PASSED ===
  auth:     PAT via env:$LZT_ZENODO_PAT
  endpoint: https://zenodo.org/api
  deposits: 3 active for this user
  scopes:   deposit:actions, deposit:write, user:email
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All three tests passed (or Test 2 was skipped because the user has no deposits, and Test 3 returned 200). |
| `1` | At least one of Tests 1-3 returned a non-200 status, or Test 1 returned invalid JSON, or the response shape was wrong (e.g. not a JSON array). |
| `2` | No credentials resolvable from env vars or TOML seed. No network request was made. |

## Running the script

```bash
export LZT_ZENODO_PAT="<personal-access-token>"
python3 scripts/zenodo_oauth_test.py
```

Without `$LZT_ZENODO_PAT` (and without the env-var pair or the TOML
seed), the script exits `2` immediately.

## What this folder does NOT cover

- **Deposit creation, file upload, publish** — out of scope. The
  script only verifies that authentication works and the existing
  deposit surface is reachable. The deposit pipeline itself is
  driven by the operator's publication harness and is not part of
  the verification surface.
- **OAuth `authorization_code` flow** — the script exercises only
  the M2M paths (PAT, client_credentials). The interactive flow
  against `sandbox.zenodo.org` is left to the operator's local
  testing.
- **Rate-limit interaction** — the script does not exercise the
  429 back-pressure path documented at
  `zenodo_oauth_test.py:81`. A reviewer probing rate-limit behavior
  should run a dedicated harness against the sandbox.

## Cross-references

- Companion paper:
  [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
- MANIFEST provenance:
  [`../MANIFEST.md`](../MANIFEST.md)
- Bidirectional claim-to-test map:
  [`../TRACEABILITY.md`](../TRACEABILITY.md)
