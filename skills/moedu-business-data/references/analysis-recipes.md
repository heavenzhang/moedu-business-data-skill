# Analysis recipes

Use these recipes as query plans, not as assumptions about data completeness. Always start with bounded queries and inspect actual fields.

## Sales funnel and conversion

1. Query `crm.leads`, `crm.opportunities`, and `crm.contracts` for the same time and owner scope.
2. Keep their primary keys, owner fields, creation dates, stage or status, and amount fields.
3. Verify whether converted records expose direct source IDs before joining. If they do not, report stage-level aggregates separately.
4. Compute counts, amounts, stage conversion rates, and cycle time only from records with compatible definitions.
5. State whether the calling account's CRM data scope is individual, team, or company-wide.

## Contract, invoice, and cash collection

1. Query `crm.contracts`, `crm.invoices`, and `crm.receivables`.
2. Join through `contractId` when present; otherwise keep the results separate.
3. Distinguish contract amount, invoiced amount, received amount, and outstanding amount.
4. Deduplicate repeated payments or invoices by their own primary keys.
5. Report missing contracts, unmatched invoices, and unmatched receivables before calculating collection rates.

## Purchase, sales, and inventory

1. Read `jxc.field-metadata` if field names are dynamic.
2. Query `jxc.purchase-orders`, `jxc.sales-orders`, `jxc.receipts`, `jxc.outbounds`, and `jxc.inventory` for the intended period and warehouse scope.
3. Use product and warehouse IDs for joins only after confirming their presence in each dataset.
4. Separate ordered, received or shipped, returned, and current-stock quantities.
5. Flag negative stock, long-idle stock, order-to-receipt gaps, and sales-to-outbound gaps as data findings, not automatic proof of an operational failure.

## People, attendance, and performance

1. Query `hrm.employees` only if the calling account has management access.
2. Use `hrm.my-attendance` for self-service requests and `hrm.attendance` for management-scope requests.
3. Query `hrm.performance-cycles`, `hrm.performance-records`, and `goals.ipi` for performance analysis.
4. Count distinct people separately from appraisal or scorecard rows.
5. Do not include payroll unless the user explicitly requests it and is authorized. Prefer aggregated payroll findings and omit identity-level values.

## Goal, gross-profit, and expense-package alignment

1. Query `goals.plans`, `goals.budgets`, `goals.teams`, and `goals.dashboard` for the same fiscal year.
2. Read plan or budget details by their real primary keys when allocation items are needed.
3. Preserve the returned unit and ratio semantics; do not silently convert yuan to ten-thousand-yuan or `0.15` to `15%`.
4. Compare targets, package allocation, actual progress, and risks only when the periods and organization mappings match.
5. Treat unmatched goal teams and organization departments as a mapping-quality issue.

## Evidence block

End an analytical result with a compact evidence block containing:

- resources queried;
- time and organization filters;
- rows returned and whether pagination was complete;
- request IDs;
- calculations performed;
- permission or data-quality limitations.
