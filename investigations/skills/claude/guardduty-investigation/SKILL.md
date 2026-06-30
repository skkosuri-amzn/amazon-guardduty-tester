---
name: guardduty-investigation
description: Run Amazon GuardDuty AI-Powered Investigations (Preview) — analyze a specific finding, an account, or an organization, then summarize risk, confidence, MITRE ATT&CK techniques, and recommended actions. Also recalls past investigations — show the latest summary, or extract its countermeasures/remediations — without creating a new one. Use when a user wants to investigate a GuardDuty finding/account/org, triage an alert, understand whether a finding is a real threat, or review/summarize a prior investigation. Drives the AWS API MCP Server directly; no local CLI required.
---

# GuardDuty AI-Powered Investigation

This skill drives GuardDuty Investigation (Preview) end to end through the
**AWS API MCP Server** (`call_aws` for single commands, `run_script` for the
create→poll loop). It does not depend on any local script.

## When to use

- "Investigate GuardDuty finding `<id>`"
- "Is this finding a real threat?" / "Triage this alert"
- "Analyze the threat posture of account `<id>`" or "...my organization"
- After generating findings with the GuardDuty Tester, to investigate them

### Recall (read past results — do NOT create a new investigation)

These prompts retrieve an *existing* investigation. Route them to the
**Recall** workflow below, never to create:

- "Show me the last/latest investigation summary"
- "From the last investigation, list the countermeasures / remediations / recommended actions"
- "What did the previous investigation find?" / "Summarize my recent investigations"
- "Get investigation `<uuid>`"

Creating wastes preview quota and returns a *different* analysis than the one
the user asked about — so when a prompt references a prior/last/previous
investigation, recall it; do not create.

## Hard constraints (verify before acting)

1. **Region** — Investigation is available ONLY in these 10 regions. If the
   user's region is not listed, stop and tell them.
   `us-east-1, us-east-2, us-west-2, ca-central-1, eu-central-1, eu-west-1,
   eu-west-2, eu-west-3, eu-north-1, ap-northeast-1`
2. **Quotas (preview)** — 10 investigations/account/day, 100 total/account.
   Failed investigations do not count. Check before creating; warn near caps.
3. **Permissions** — Use ReadOnly credentials for the account, augmented with
   an additional policy granting the investigation actions. Example policy to add:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "guardduty:CreateInvestigation",
                   "guardduty:GetInvestigation",
                   "guardduty:ListInvestigations"
               ],
               "Resource": "arn:aws:guardduty:us-west-2:123456789012:detector/2cb3d4e5f6a7b8c9d0e1f2a3b4c5d6e7"
           }
       ]
   }
   ```
4. **Trigger prompt** — 1–2048 chars; include EXACTLY ONE finding id (32 hex
   chars) OR ONE account id (12 digits), never both, never multiple.
5. Always present the caveat: *AI analysis may contain errors; human review is
   recommended.*

## Workflow

### Step 0 — Confirm the AWS API MCP Server is available
- This skill requires the AWS API MCP Server tools (`call_aws` and
  `run_script`). Verify they are connected before doing anything else.
- If they are NOT available, stop and tell the user to connect the AWS API MCP
  Server (https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html).
  As a fallback, the user can run the equivalent `aws guardduty ...` commands in
  their own terminal, or use the `gd_investigator.py` CLI in this repo.

### Step 1 — Preflight: CLI version, region, detector
- Verify the AWS CLI is at least **2.35.11** (`aws --version`). The Investigation
  APIs are preview and missing from older CLIs — an older version fails with an
  "Invalid choice: create-investigation" error. If it is older, stop and tell
  the user to upgrade the AWS CLI / SDK.
- Get the region; confirm it is one of the 10 supported. If not, stop.
- Find the detector id: `call_aws` → `aws guardduty list-detectors`.

### Step 2 — Ensure AI_ANALYST is enabled
- `call_aws` → `aws guardduty get-detector --detector-id <id>`. Look for a
  feature named `AI_ANALYST` with `Status: ENABLED`.
- If not enabled, enable it:
  `aws guardduty update-detector --detector-id <id> --features '[{"Name":"AI_ANALYST","Status":"ENABLED"}]'`

### Step 3 — Quota check
- `call_aws` → `aws guardduty list-investigations --detector-id <id> --max-results 50`
  (paginate via `--starting-token` if needed). Count non-FAILED items total and
  today. If at/over a cap, stop; if one away, warn and confirm.

### Step 4 — Build the trigger prompt
- Finding: `"Investigate finding <32-hex-id>"`
- Account: `"Analyze findings in account with id <12-digit-id>"`
- Org:     `"Analyze findings in my organization"`

## Recall workflow (retrieve a past investigation — no quota cost)

Use this instead of Steps 4–5 when the prompt references the last/previous/a
specific investigation. Listing and getting do NOT consume quota.

1. **List, newest first** — `call_aws` →
   `aws guardduty list-investigations --detector-id <id> --max-results 50 --sort-criteria '{"AttributeName":"START_TIME","OrderBy":"DESC"}'`
   The first element is the most recent. For "latest *completed*", pick the
   first item whose `Status` is `COMPLETED` (skip `RUNNING`/`FAILED`). The list
   already carries `RiskLevel`, `Confidence`, and `Title` for a quick summary.
2. **Get full details** — `call_aws` →
   `aws guardduty get-investigation --detector-id <id> --investigation-id <inv-id>`
   The summaries from list do NOT include `Summary`/`countermeasures`; you must
   `get` the specific id to see observations, MITRE techniques, and
   countermeasures.
3. **Report** — render per Step 6. For "list the countermeasures/remediations",
   parse `Summary` and present only the `countermeasures` array (each item's
   `description` and any `command`/`cliCommand`).

Fallback CLI: `gd_investigator.py latest` (newest), `latest --completed`
(newest completed), `get <uuid>`, or `list --sort START_TIME --order DESC`.

### Step 5 — Create + poll (use run_script for the loop)
Prefer a single `run_script` so create and polling happen in one round-trip:

```python
async def main():
    detector_id = "<DETECTOR_ID>"
    prompt = "<TRIGGER_PROMPT>"
    created = await call_boto3(
        service_name="guardduty",
        operation_name="CreateInvestigation",
        params={"DetectorId": detector_id, "TriggerPrompt": prompt},
    )
    inv_id = created["InvestigationId"]
    import asyncio
    for _ in range(10):  # ~10 min at 60s
        got = await call_boto3(
            service_name="guardduty",
            operation_name="GetInvestigation",
            params={"DetectorId": detector_id, "InvestigationId": inv_id},
        )
        status = got["Investigation"]["Status"]
        if status in ("COMPLETED", "FAILED"):
            return got["Investigation"]
        await asyncio.sleep(60)
    return got["Investigation"]

result = await main()
result
```

For a quick single create or get without polling, use `call_aws`:
`aws guardduty create-investigation --detector-id <id> --trigger-prompt "<prompt>"`
`aws guardduty get-investigation --detector-id <id> --investigation-id <inv-id>`

### Step 6 — Report
The `Summary` field is a JSON string. Parse it and present:
- **Risk Level** (Info/Low/Medium/High/Critical) and **Confidence**
  (Unknown/Low/Medium/High)
- **Key Observations** (title, narrative, observations)
- **Threat Assessment** — MITRE ATT&CK techniques
- **Recommended Actions** — including any CLI commands in `countermeasures`
- The human-review caveat.

If `Status` is `FAILED`, show the `Error` field and note failures don't count
against quota.
