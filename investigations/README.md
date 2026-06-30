# GuardDuty Investigations

Agent skills to run **Amazon GuardDuty AI-Powered Investigations (Preview)**
against your findings and accounts. GuardDuty Investigation uses AI to analyze a
finding, account, or organization and return a risk disposition with confidence
scoring, MITRE ATT&CK® technique classification, supporting evidence, and
recommended actions.

These skills are **independent of the CDK app** in the repo root — they work
against any account with your own AWS credentials, whether or not you deployed
the tester. They support three situations:

1. **Investigate findings you generated** with the GuardDuty Tester.
2. **Investigate findings you really received** (any finding/account/org).
3. **Investigate through an agent** using the included Claude and Kiro skills.

> AI-generated analysis and recommendations may contain errors or incomplete
> assessments. **Human review is recommended.**

The **skills (`skills/`)** are for agents (Claude, Kiro). They call AWS via the
[AWS API MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
using its `call_aws` / `run_script` tools.

## Prerequisites

- The [AWS API MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
  connected to your agent. The skills call AWS exclusively through its
  `call_aws` / `run_script` tools, authenticated with your existing IAM
  credentials.
- AWS CLI ≥ 2.35.11 (the preview Investigation APIs are missing from older CLIs).
- An active GuardDuty detector in a supported region (see below).
- The `AI_ANALYST` feature enabled on the detector. The skill can enable it for
  you (with confirmation).
- IAM permissions: `guardduty:CreateInvestigation`, `guardduty:GetInvestigation`,
  `guardduty:ListInvestigations` (plus `GetDetector`/`UpdateDetector`/
  `ListDetectors`/`ListFindings` for setup). The skills recommend running with
  **ReadOnly credentials augmented by a scoped inline policy** granting just the
  three investigation actions on your detector ARN — see the example policy in
  each skill file rather than using broad admin credentials.

### Supported regions (preview, 10 total)

`us-east-1`, `us-east-2`, `us-west-2`, `ca-central-1`, `eu-central-1`,
`eu-west-1`, `eu-west-2`, `eu-west-3`, `eu-north-1`, `ap-northeast-1`

### Preview quotas

10 investigations per account per day; 100 per account total. Failed
investigations do not count. The skills check and warn before spending quota.

## Skills usage

Two self-contained agent workflows that drive GuardDuty Investigation through
the AWS API MCP Server:

- **Claude** — `skills/claude/guardduty-investigation/SKILL.md`
- **Kiro** — `skills/kiro/guardduty-investigation/guardduty-investigation.md`

Both encode the same guardrails (region allowlist, preview quotas, prompt rules,
polling, result interpretation) in prose, so an agent can run an investigation
end to end. The skills begin by confirming the AWS API MCP Server tools
(`call_aws`/`run_script`) are connected and that the AWS CLI is new enough, then
stop with guidance if not. Each runs the same Steps 0–6 procedure (MCP/CLI
preflight → region/detector → enable AI_ANALYST → quota → prompt → create+poll →
report).

### Run the Claude skill

1. Make it discoverable. Copy (or symlink) the skill folder into a skills
   directory Claude Code reads — project scope `.claude/skills/` or personal
   scope `~/.claude/skills/`:
   ```bash
   mkdir -p .claude/skills
   ln -s "$(pwd)/skills/claude/guardduty-investigation" \
         .claude/skills/guardduty-investigation
   ```
2. Start (or restart) Claude Code and confirm it loads — type `/` to see
   `guardduty-investigation` in the skill list.
3. Trigger it with a natural request, e.g.:
   - `Investigate GuardDuty finding 1ab2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`
   - `Is this GuardDuty alert a real threat?`
   - `Analyze the threat posture of account 123456789012`

### Run the Kiro skill

1. Place the steering doc under your Kiro workspace at
   `.kiro/steering/guardduty-investigation.md` (copy the file from
   `skills/kiro/guardduty-investigation/`). It uses `inclusion: manual`, so it
   loads only when you reference it.
2. In Kiro, invoke it by context-referencing the steering file (e.g. `#`-mention
   `guardduty-investigation`) alongside your request, such as
   `Investigate GuardDuty finding <id>`.
3. Kiro follows the same Steps 0–6 procedure.

### Lint the skill files

Validate frontmatter and required fields before relying on a skill:

```bash
python3 skills/lint_skill.py
```

## Layout

```
investigations/
└── skills/                # Claude + Kiro agent workflows (+ lint_skill.py)
    ├── claude/guardduty-investigation/SKILL.md
    ├── kiro/guardduty-investigation/guardduty-investigation.md
    └── lint_skill.py
```

## References

- [GuardDuty Investigation (User Guide)](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-investigation.html)
- [CreateInvestigation](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_CreateInvestigation.html)
 · [GetInvestigation](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_GetInvestigation.html)
 · [ListInvestigations](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_ListInvestigations.html)
- [AWS API MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
