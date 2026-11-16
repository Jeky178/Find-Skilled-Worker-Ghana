"""
Regenerate docs/API.md and docs/openapi.json from the running code, so the documentation can never drift.
Run from the project folder:   python scripts/export_api_docs.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")
os.environ.setdefault("SECRET_KEY", "docs-only-secret-docs-only-secret-0123456789")
os.environ.setdefault("DATABASE_URL", "sqlite:///./docs_tmp.db")

from main import app  # noqa: E402

spec = app.openapi()
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")


def who(method: str, path: str, secured: bool) -> str:
    if path.startswith("/api/admin") or (path.startswith("/api/contact") and method != "POST"):
        return "Admin"
    if path.startswith("/api/artisan/me"):
        return "Artisan"
    if path.startswith("/api/billing") and path not in ("/api/billing/plans", "/api/billing/webhook/paystack"):
        return "Artisan"
    if path == "/api/billing/webhook/paystack":
        return "Paystack (signed)"
    if (method, path) in {("POST", "/api/requests"), ("POST", "/api/requests/{request_id}/review")}:
        return "Customer"
    return "Logged in" if secured else "Public"


order = ["System", "Authentication", "Categories", "Artisan directory", "Artisan profile (artisan only)", "Billing and payments",
         "Service requests", "Reviews", "Notifications", "Reports", "Contact", "Administration"]
groups: dict[str, list] = {}
for path, ops in spec["paths"].items():
    for method, op in ops.items():
        tag = (op.get("tags") or ["Other"])[0]
        groups.setdefault(tag, []).append((path, method.upper(), op))

lines = [
    "# API reference", "",
    "Generated from the code by `python scripts/export_api_docs.py`. The same information, with a **Try it out** button,",
    "is at `/docs` while the backend runs in development (the page is switched off in production).", "",
    "**Authentication.** Log in with `POST /api/auth/login`, then send the returned token on every protected call:",
    "`Authorization: Bearer <token>`. Tokens last 60 minutes by default.", "",
    "**Errors.** Failures return JSON with a `detail` message. Validation problems return `422` with an `errors` list of `{field, message}`.",
    "Common codes: `401` not logged in, `403` wrong role or suspended, `404` not found (also used when you may not see something),",
    "`409` conflict with the current state, `429` too many attempts, `503` payments not switched on.", "",
    "**Who can call it** uses these labels: Public, Logged in, Customer, Artisan, Admin.", "",
]
for tag in order + sorted(set(groups) - set(order)):
    if tag not in groups:
        continue
    lines += [f"## {tag}", "", "| Method | Path | Who | What it does |", "|---|---|---|---|"]
    for path, method, op in sorted(groups[tag], key=lambda x: (x[0], x[1])):
        summary = (op.get("summary") or "").replace("|", "/")
        doc = " ".join((op.get("description") or "").split()).replace("|", "/")
        text = doc if doc and doc.lower() != summary.lower() else summary
        lines.append(f"| `{method}` | `{path}` | {who(method, path, bool(op.get('security')))} | {text[:220]} |")
    lines.append("")
(ROOT / "docs" / "API.md").write_text("\n".join(lines), encoding="utf-8")
print("endpoints documented:", sum(len(v) for v in groups.values()), "| tags:", len(groups))
