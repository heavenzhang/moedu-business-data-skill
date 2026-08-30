# Resource map

Use `resources describe RESOURCE` as the runtime source of truth. This map provides routing and primary-key guidance; it does not replace live discovery.

## CRM

| Resource | Meaning | Primary key |
| --- | --- | --- |
| `crm.customers` | Customers | `customerId` |
| `crm.leads` | Leads | `leadsId` |
| `crm.opportunities` | Sales opportunities | `businessId` |
| `crm.contracts` | Contracts | `contractId` |
| `crm.receivables` | Received payments | `receivablesId` |
| `crm.invoices` | Invoices | `invoiceId` |

Use CRM resources for pipeline, conversion, contract, collection, invoicing, customer, and owner analysis. Do not assume every resource exposes identical date or owner filter names.

## JXC inventory and order management

| Resource | Meaning | Primary key |
| --- | --- | --- |
| `jxc.products` | Products | `productId` |
| `jxc.suppliers` | Suppliers | `supplierId` |
| `jxc.purchase-orders` | Purchase orders | `purchaseId` |
| `jxc.purchase-returns` | Purchase returns | `retreatId` |
| `jxc.sales-orders` | Sales orders | `saleId` |
| `jxc.sales-returns` | Sales returns | `salereturnId` |
| `jxc.receipts` | Warehouse receipts | `receiptId` |
| `jxc.outbounds` | Warehouse outbounds | `outboundId` |
| `jxc.payments` | Supplier payments | `paymentNoteId` |
| `jxc.collections` | JXC collections | `collectionNoteId` |
| `jxc.stock-checks` | Stock checks | `inventoryId` |
| `jxc.stock-transfers` | Stock transfers | `allocationId` |
| `jxc.stock-movements` | Inbound and outbound movements | `detailedId` |
| `jxc.warehouses` | Warehouses | `warehouseId` |
| `jxc.inventory` | Product stock by warehouse | `warehouseProductId` |
| `jxc.field-metadata` | Dynamic JXC field metadata | none |

Read `jxc.field-metadata` when dynamic field names are needed. CRM receivables and JXC collections are different business objects; do not merge them without verifying the business process.

## HRM and performance

| Resource | Meaning | Primary key | Sensitivity |
| --- | --- | --- | --- |
| `hrm.employees` | Employee records | `employeeId` | confidential |
| `hrm.attendance` | Attendance in the caller's management scope | `clockId` | confidential |
| `hrm.my-attendance` | Current account's attendance | `clockId` | confidential |
| `hrm.performance-cycles` | Performance appraisal plans | `appraisalId` | confidential |
| `hrm.performance-records` | Employee appraisal records | `employeeAppraisalId` | confidential |
| `hrm.latest-payroll-period` | Latest payroll period | none | restricted |
| `hrm.payroll-records` | Payroll calculation records | `employeeId` | restricted |

Payroll resources require `--include-sensitive` and matching server permission. Keep personal information redacted unless identity-level data is explicitly required.

## Goals, budgets, and IPI

| Resource | Meaning | Primary key | Sensitivity |
| --- | --- | --- | --- |
| `goals.dashboard` | Goal and budget overview | none | internal |
| `goals.teams` | Responsible operating teams | `teamId` | internal |
| `goals.plans` | Annual goal plans | `planId` | internal |
| `goals.budgets` | Gross-profit allocation and expense packages | `companyBudgetId` | confidential |
| `goals.ipi` | Employee IPI scorecards | `scorecardId` | confidential |

An employee may have multiple IPI scorecards across teams or periods. Count distinct `employeeId` separately from scorecard rows.

## Approval workbench

| Resource | Meaning | Primary key |
| --- | --- | --- |
| `workflow.oa-approvals` | OA approval instances | `examineRecordId` |
| `workflow.contract-approvals` | Contract approvals | `examineRecordId` |
| `workflow.receivables-approvals` | Receivables approvals | `examineRecordId` |
| `workflow.invoice-approvals` | Invoice approvals | `examineRecordId` |

Approval lists are scoped to the current account's approval role and status filters. A zero-row result is not evidence that no approvals exist globally.

## Support and feedback

| Resource | Meaning | Primary key |
| --- | --- | --- |
| `support.feedback` | 企业管理员可见的问题与建议反馈 | `feedbackId` |

Use `support.feedback` for feedback triage and read-only inspection. The supported filters are `status`, `reviewStatus`, `feedbackType`, `priority`, `moduleCode`, and `keyword`. `reviewStatus=1` means waiting for the platform designer; `reviewStatus=2` means the designer explicitly approved AI execution. Reading this resource does not authorize review, status, or reply changes; those writes must continue through the platform's administrator workflow.

## Identifier cautions

- CRM `userId` identifies a platform account.
- HRM `employeeId` identifies an HR employee record.
- `deptId` identifies an organization node.
- Goal `teamId` identifies a goal-management team and may bind to an organization node through a separate field.
- IPI `employeeId` follows the goal/IPI service's account identity. Verify it before joining to HRM employee IDs.
- Customer sales orders in CRM and JXC may use different record IDs even when they describe the same commercial activity.
