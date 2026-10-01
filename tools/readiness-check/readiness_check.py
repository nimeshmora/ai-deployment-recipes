#!/usr/bin/env python3
"""Readiness check: probe an AI service endpoint for deployment safeguards.

Black-box and dependency-free (standard library only). Point it at a running
recipe-style endpoint and it reports which safeguards are present, as pass/fail.

    python3 readiness_check.py http://localhost:8000 --token "$(cat .secrets/app_token)"

What it checks (remotely observable only):
  - authentication is required           (no token -> 401)
  - content type is enforced             (text/plain -> 415)
  - request schema is strict             (unknown field -> 422)
  - oversized bodies are rejected        (>16 KB -> 413)
  - requests are rate limited            (burst -> 429)   [spends the minute; --no-rate to skip]
  - responses carry hardened headers     (CSP, nosniff, ...)
  - health endpoints respond             (/health/live, /health/ready)

Not checkable from outside (verify these in the recipe/CI, not here): redacted
logs, non-root/read-only container, pinned dependencies. This tool is a quick
signal, not a certification. It assumes a recipe-01-style JSON chat endpoint;
adjust --path / --health for other shapes.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

OK, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def request(url, method="GET", headers=None, body=None, timeout=35):
    req = urllib.request.Request(
        url,
        method=method,
        headers=headers or {},
        data=body if body is None or isinstance(body, bytes) else body.encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


class Report:
    def __init__(self):
        self.rows = []

    def add(self, result, name, owasp, detail):
        self.rows.append((result, name, owasp, detail))

    def print_and_exit(self):
        width = max(len(n) for _, n, _, _ in self.rows)
        print()
        for result, name, owasp, detail in self.rows:
            mark = {OK: "PASS", FAIL: "FAIL", SKIP: "skip"}[result]
            tag = f"[{owasp}]" if owasp else ""
            print(f"  {mark}  {name.ljust(width)}  {tag:<12} {detail}")
        passed = sum(1 for r, *_ in self.rows if r == OK)
        failed = sum(1 for r, *_ in self.rows if r == FAIL)
        skipped = sum(1 for r, *_ in self.rows if r == SKIP)
        checked = passed + failed
        print(
            f"\n  Score: {passed}/{checked} safeguards present"
            + (f" · {failed} missing" if failed else "")
            + (f" · {skipped} skipped" if skipped else "")
        )
        print(
            "  (log redaction, non-root container and pinned deps are not remotely checkable.)\n"
        )
        sys.exit(1 if failed else 0)


def main():
    ap = argparse.ArgumentParser(
        description="Probe an AI service for deployment safeguards."
    )
    ap.add_argument("base_url", help="e.g. http://localhost:8000")
    ap.add_argument(
        "--token", default="", help="app bearer token (unlocks the token-gated checks)"
    )
    ap.add_argument(
        "--path", default="/api/chat", help="chat/inference path (default /api/chat)"
    )
    ap.add_argument(
        "--health",
        default="/health/live,/health/ready",
        help="comma-separated health paths",
    )
    ap.add_argument(
        "--rpm",
        type=int,
        default=30,
        help="expected requests-per-minute budget (default 30)",
    )
    ap.add_argument(
        "--no-rate",
        action="store_true",
        help="skip the rate-limit check (it spends the minute)",
    )
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    chat = base + args.path
    rep = Report()
    jsonct = {"Content-Type": "application/json"}
    bearer = {**jsonct, "Authorization": f"Bearer {args.token}"} if args.token else None

    # Health endpoints
    for hp in [p for p in args.health.split(",") if p]:
        code, _ = request(base + hp, "GET")
        rep.add(OK if code == 200 else FAIL, f"health {hp}", "", f"HTTP {code}")

    # Authentication required (no token)
    code, headers_seen = request(chat, "POST", jsonct, json.dumps({"message": "hi"}))
    rep.add(
        OK if code == 401 else FAIL,
        "auth required",
        "API2",
        f"no token -> HTTP {code} (want 401)",
    )

    # Hardened response headers (present on any response, including the 401 above)
    want = [
        "x-request-id",
        "content-security-policy",
        "x-content-type-options",
        "referrer-policy",
        "cache-control",
    ]
    lower = {k.lower() for k in headers_seen}
    missing = [h for h in want if h not in lower]
    rep.add(
        OK if not missing else FAIL,
        "hardened headers",
        "API8",
        "all present" if not missing else "missing: " + ", ".join(missing),
    )

    def gated(name, owasp, run):
        if not bearer:
            rep.add(SKIP, name, owasp, "needs --token")
            return
        run()

    # Content-type enforced
    gated(
        "content-type enforced",
        "API8",
        lambda: rep.add(
            *(
                (OK, "content-type enforced", "API8", "text/plain -> 415")
                if request(
                    chat,
                    "POST",
                    {**bearer, "Content-Type": "text/plain"},
                    json.dumps({"message": "hi"}),
                )[0]
                == 415
                else (FAIL, "content-type enforced", "API8", "text/plain not rejected")
            )
        ),
    )

    # Strict schema (unknown field)
    gated(
        "strict schema",
        "API3",
        lambda: rep.add(
            *(
                (OK, "strict schema", "API3", "unknown field -> 422")
                if request(
                    chat, "POST", bearer, json.dumps({"message": "hi", "admin": True})
                )[0]
                == 422
                else (FAIL, "strict schema", "API3", "extra field not rejected")
            )
        ),
    )

    # Oversized body
    gated(
        "oversized rejected",
        "LLM10",
        lambda: rep.add(
            *(
                (OK, "oversized rejected", "LLM10", "~20 KB -> 413")
                if request(chat, "POST", bearer, '{"message":"' + "a" * 20000 + '"}')[0]
                == 413
                else (FAIL, "oversized rejected", "LLM10", "large body not rejected")
            )
        ),
    )

    # Rate limit (spends the minute)
    if args.no_rate:
        rep.add(SKIP, "rate limited", "LLM10", "--no-rate")
    elif not bearer:
        rep.add(SKIP, "rate limited", "LLM10", "needs --token")
    else:
        ok = blocked = 0
        for _ in range(args.rpm + 5):
            c, _h = request(chat, "POST", bearer, json.dumps({"message": "hi"}))
            if c == 200:
                ok += 1
            elif c == 429:
                blocked += 1
        if ok == 0 and blocked == 0:
            rep.add(FAIL, "rate limited", "LLM10", "all rejected — token correct?")
        else:
            rep.add(
                OK if blocked else FAIL,
                "rate limited",
                "LLM10",
                f"{ok} ok, {blocked} throttled (429)",
            )

    rep.print_and_exit()


if __name__ == "__main__":
    main()
