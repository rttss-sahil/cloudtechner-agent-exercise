"""Generate the MOCK runbooks/ corpus (canonical per HR guidance: "use mock data").

The docs deliberately mirror the traps described in the assignment:
near-duplicate structures across checkout-api / payments-api / inventory-api,
one dated incident postmortem (RB-012), and one customer-communication policy
(RB-011). Regenerating this file overwrites runbooks/ with the exact corpus used
by the harness and the deployed Worker.
"""

import re
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "runbooks"

TEMPLATE = """# {title}

## Overview
{overview}

## Symptoms
{symptoms}

## Steps
{steps}
"""

DOCS: dict[str, str] = {
    "RB-001": dict(
        title="checkout-api: High CPU",
        overview=("checkout-api handles order checkout traffic. High CPU usually means a "
                  "sudden traffic spike or an inefficient hot path."),
        symptoms="Sustained CPU >80% on checkout-api pods; latency p95 climbs; checkout timeouts.",
        steps=("1. Check CPU dashboard and recent deploys in the last 2 hours.\n"
               "2. Confirm there is no stuck checkout loop (look for repeated order mutations).\n"
               "3. Check autoscaler target; scale up if traffic is legitimately high.\n"
               "4. Profile the hot path (perf) before making code changes."),
    ),
    "RB-002": dict(
        title="checkout-api: Too Many Connections",
        overview=("checkout-api uses Postgres with a shared connection pool. 'Too many "
                  "connections' errors typically follow pool exhaustion."),
        symptoms="ERROR: too many connections; checkout-api 503s; idle connections maxed.",
        steps=("1. Check pool utilization and count of open Postgres connections.\n"
               "2. Increase pgbouncer max_client_conn and restart lookup.\n"
               "3. Look for a runaway migration holding locks or a long-running query.\n"
               "4. If a migration is the cause, pause it; kill blocked sessions."),
    ),
    "RB-003": dict(
        title="payments-api: High CPU",
        overview=("payments-api authorizes and settles payments. High CPU is usually a "
                  "retry storm from downstream providers or a hot code path."),
        symptoms="Sustained CPU >80% on payments-api pods; settlement lag grows; provider timeouts.",
        steps=("1. Check CPU dashboard and downstream provider latencies.\n"
               "2. Inspect retry loops on failed authorizations.\n"
               "3. Verify settlement batch sizes; they can explode under spike.\n"
               "4. Profile the hot path (perf) before changing code."),
    ),
    "RB-004": dict(
        title="payments-api: Too Many Connections",
        overview=("payments-api shares the checkout cluster's Postgres. 'Too many connections' "
                  "errors follow long-draining transactions during high volume."),
        symptoms="ERROR: too many connections; payments-api 503s; settlement jobs fail.",
        steps=("1. Check connection pool and long-running settlement transactions.\n"
               "2. Increase pool limits after confirming baseline.\n"
               "3. Kill stale sessions from failed settlement retries.\n"
               "4. Raise alert thresholds so retry storms drain."),
    ),
    "RB-005": dict(
        title="checkout-api: Safe Rollback",
        overview=("checkout-api ships via blue-green deploys. Rolls back are safe when DB "
                  "migrations are backward-compatible."),
        symptoms="Regression found after a checkout-api deploy; need to revert quickly.",
        steps=("1. Verify the migration in the target release is backward-compatible.\n"
               "2. Flip the canary/blue-green switch back to the previous build.\n"
               "3. Watch error rate and latency for 10 minutes.\n"
               "4. If schema changes are incompatible, open a data-fix ticket instead of reverting."),
    ),
    "RB-006": dict(
        title="payments-api: Safe Rollback",
        overview=("payments-api also ships blue-green. Settlement sinks may already be "
                  "drained, so check before reverting."),
        symptoms="Regression after a payments-api deploy; revert needed.",
        steps=("1. Confirm no settlement sink was drained by the new build.\n"
               "2. Fall back to the previous payments-api build.\n"
               "3. Replay any drained settlement queue entries.\n"
               "4. Watch provider error rates for 10 minutes."),
    ),
    "RB-007": dict(
        title="inventory-api: Sync Lag",
        overview=("inventory-api syncs stock levels from warehouse events. Lag appears when "
                  "the event queue backs up."),
        symptoms="Stock counts stale; sync lag reported on the inventory dashboard.",
        steps=("1. Measure event queue depth and consumer throughput.\n"
               "2. Restart stuck consumers.\n"
               "3. If a processing bug is present, pause the pipeline at the source.\n"
               "4. Replay the event stream after the fix."),
    ),
    "RB-008": dict(
        title="inventory-api: High CPU",
        overview=("inventory-api recomputes stock projections. High CPU usually means a "
                  "runaway aggregation query on the stock table."),
        symptoms="Sustained CPU >80% on inventory-api pods; projections delayed.",
        steps=("1. Find the expensive aggregation query in the slow query log.\n"
               "2. Add the missing index on the stock table.\n"
               "3. Cap the projection recompute batch window.\n"
               "4. Kill any runaway recompute jobs still running."),
    ),
    "RB-009": dict(
        title="Deploy Freeze & Change Management",
        overview=("Changes to checkout-api, payments-api and inventory-api are frozen during "
                  "promotional windows unless approved."),
        symptoms="Deploy blocked by the freeze policy; need an exception.",
        steps=("1. Check the freeze calendar for the current window.\n"
               "2. File a change request with risk assessment.\n"
               "3. Get explicit approval from the change advisory board.\n"
               "4. Schedule the deploy for the earliest approved slot."),
    ),
    "RB-010": dict(
        title="Incident Severity Definitions",
        overview=("Defines severity levels. A severity-1 incident is a full customer-facing "
                  "outage of a core service."),
        symptoms="Criteria for escalating an incident.",
        steps=("1. Severity-1: core service (checkout, payments, inventory) fully down or "
               "data loss.\n"
               "2. Severity-2: major degradation, workaround available.\n"
               "3. Severity-3: non-urgent defect or minor degradation.\n"
               "4. Declare S1 immediately when customer impact is broad."),
    ),
    "RB-011": dict(
        title="Customer Communication During Incidents",
        overview=("Guidelines for communicating with customers during incidents. Customers "
                  "are informed via the status page and email for S1/S2 incidents."),
        symptoms="Communicating an ongoing incident to customers.",
        steps=("1. Publish status-page update within 15 minutes of S1/S2 declaration.\n"
               "2. State impacted services, start time, and next update time.\n"
               "3. Post an update every 30 minutes until resolved.\n"
               "4. After resolution, send a postmortem summary email within 24h."),
    ),
    "RB-012": dict(
        title="Incident Postmortem 2026-08-10 (checkout-api outage)",
        overview=("On 2026-08-10 checkout-api was down for 47 minutes. Root cause was a "
                  "deploy that shipped an incompatible DB migration; the fix was a rollback "
                  "plus a data-fix ticket to reconcile dropped orders."),
        symptoms="checkout-api 503s; orders stuck in 'processing'; payment links failed.",
        steps=("1. Deploy 2026-08-10 09:12 pushed an incompatible migration.\n"
               "2. 09:18 error rates rose; incident declared at 09:21 (S1).\n"
               "3. 09:41 rollback executed; service restored 09:59.\n"
               "4. Follow-up: backward-compatibility gate added to the deploy pipeline; "
               "orders reconciled via data-fix queue."),
    ),
}


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for doc_id, body in DOCS.items():
        content = TEMPLATE.format(**body)
        (DEST / f"{doc_id}.md").write_text(content, encoding="utf-8")
    print(f"Wrote {len(DOCS)} sample runbooks to {DEST}")
    print("NOTE: runbooks/ is the official corpus (HR: \"use mock data\"). Re-run the harness after a regen.")


if __name__ == "__main__":
    main()