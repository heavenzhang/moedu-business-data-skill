---
name: moedu-business-data
description: Safely query and analyze the Moedu business platform through the read-only moedu-agent CLI. Use for requests involving CRM customers, leads, opportunities, contracts, receivables or invoices; JXC products, suppliers, purchases, sales, warehouses or inventory; HRM employees, attendance, payroll or performance; goal plans, gross-profit budgets, expense packages, IPI scorecards; or approval data. Also use when discovering available Moedu data resources, exporting bounded datasets, or preparing cross-module operating analysis. Do not use for creating, editing, deleting, approving, or otherwise mutating platform records.
---

# Moedu Business Data

Use the bundled wrapper to access the platform through the allowlisted, read-only CLI. Treat the platform's server-side role and data-scope checks as authoritative.

## Locate the command

Set `skill_root` to this skill directory, then use:

```bash
"$skill_root/scripts/moedu-data" doctor
```

The wrapper locates the adjacent repository CLI, an installed `moedu-agent`, or the explicit `MOEDU_AGENT_CLI` path. Never reproduce or replace the HTTP client with raw database access.

If `doctor` reports that authentication is missing, ask the user to authenticate on the agent host. Do not request a password in chat or place credentials in commands, files, logs, or answers.

## Follow the query workflow

1. Translate the question into a business domain, time range, organization or owner scope, and required measures.
2. Read [references/resource-map.md](references/resource-map.md) when selecting resources or join keys.
3. Run `resources describe RESOURCE` before the first query when the filter names or primary key are uncertain.
4. Fetch one bounded page first. Use `--select` to keep only fields required for the analysis.
5. Inspect the returned `page.total`, field availability, and units. Refine filters before using `--all`.
6. Use `--all --max-pages N` only when the requested analysis genuinely requires the complete filtered population. Never silently treat a truncated result as complete.
7. For multi-resource operating analysis, read [references/analysis-recipes.md](references/analysis-recipes.md) and validate join keys before calculating.
8. Report the resources, filters or period, returned row counts, request IDs, missing data, permission failures, and calculation assumptions with the result.

Example discovery and bounded query:

```bash
"$skill_root/scripts/moedu-data" resources list --domain crm --format table
"$skill_root/scripts/moedu-data" resources describe crm.contracts
"$skill_root/scripts/moedu-data" query crm.contracts \
  --filter startTime=2026-01-01 \
  --limit 100 \
  --select contractId,contractName,customerName,money,startTime,endTime
```

## Enforce data safety

- Keep queries read-only. Do not call undocumented endpoints or platform write endpoints.
- Accept server permission denials. Do not switch accounts, broaden filters, or seek alternate endpoints to bypass them.
- Leave personal information redacted by default. Use `--include-pii` only when the user explicitly requests identity-level output and it is necessary for the task.
- Use `--include-sensitive` only for an explicit payroll or similarly restricted-data request from an authorized user. This flag confirms intent; it does not grant permission.
- Prefer aggregated findings over returning raw employee, customer, contract, or payroll datasets in chat.
- Never expose tokens, config file contents, passwords, audit-log contents, or full HTTP headers.
- Treat empty data and denied data differently. Report an authorization error as an authorization error, not as a zero result.
- Preserve source units. Do not infer that money is yuan or ten-thousand-yuan, or that a ratio is a decimal or percentage, without field or UI evidence.

## Produce analysis-ready output

Use JSON for normal agent reasoning and NDJSON for streaming or local batch processing. Table format is for human inspection only.

When projecting fields, retain the resource primary key and any join key needed later. For cross-module joins, verify identifier semantics first: CRM user IDs, HRM employee IDs, organization department IDs, goal team IDs, and IPI employee IDs are not interchangeable merely because they are numeric.

For every conclusion, distinguish:

- directly returned facts;
- computed totals, rates, or trends;
- data-quality gaps or unmatched joins;
- interpretation or recommendation.

Do not claim a company-wide result unless the query was complete for the intended data scope and the calling account had company-wide access.

## Handle unsupported requests

If the user asks to create or change business records, explain that this Skill and CLI are read-only. Identify the requested write operation and hand it back for a separately authorized implementation or platform workflow; do not improvise a write call.
