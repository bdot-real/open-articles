#!/usr/bin/env bash
# A virtual key per tenant, with its own budget and attribution tags.
# Hitting the cap stops requests. It does not warn, it stops.
set -euo pipefail

TENANT="${1:?usage: tenant-key.sh <tenant-id> [monthly-budget-usd]}"
BUDGET="${2:-200}"

curl -sS -X POST "${LITELLM_URL:-http://localhost:4000}/key/generate" \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY:?}" \
  -H "Content-Type: application/json" \
  -d "{
        \"user_id\": \"tenant-${TENANT}\",
        \"max_budget\": ${BUDGET},
        \"budget_duration\": \"30d\",
        \"metadata\": {\"tags\": [\"tenant:${TENANT}\"]}
      }" | python3 -m json.tool
