"""Allowlisted read-only resources exposed by the CLI."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class Resource:
    name: str
    domain: str
    description: str
    list_path: str
    paginated: bool = True
    default_body: Dict[str, Any] = field(default_factory=dict)
    primary_key: Optional[str] = None
    detail_path: Optional[str] = None
    detail_body_key: Optional[str] = None
    sensitivity: str = "internal"
    filter_hints: Tuple[str, ...] = ()

    def public_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["read_only"] = True
        return value


def _jxc(
    name: str,
    description: str,
    label: int,
    primary_key: str,
    detail_service: Optional[str] = None,
) -> Resource:
    return Resource(
        name=name,
        domain="jxc",
        description=description,
        list_path="jxcField/queryPageList/{0}".format(label),
        default_body={"label": label},
        primary_key=primary_key,
        detail_path=("{0}/queryById/{{id}}".format(detail_service) if detail_service else None),
        filter_hints=("search", "createTime", "updateTime", "ownerUserId"),
    )


RESOURCE_LIST = (
    Resource(
        "crm.customers", "crm", "客户", "crmCustomer/queryPageList",
        primary_key="customerId", detail_path="crmCustomer/queryById/{id}",
        filter_hints=("search", "ownerUserId", "sceneId", "createTime"),
    ),
    Resource(
        "crm.leads", "crm", "线索", "crmLeads/queryPageList",
        primary_key="leadsId", detail_path="crmLeads/queryById/{id}",
        filter_hints=("search", "ownerUserId", "sceneId", "createTime"),
    ),
    Resource(
        "crm.opportunities", "crm", "商机", "crmBusiness/queryPageList",
        primary_key="businessId", detail_path="crmBusiness/queryById/{id}",
        filter_hints=("search", "ownerUserId", "statusId", "customerId", "createTime"),
    ),
    Resource(
        "crm.contracts", "crm", "合同", "crmContract/queryPageList",
        primary_key="contractId", detail_path="crmContract/queryById/{id}",
        filter_hints=("search", "ownerUserId", "customerId", "businessId", "createTime"),
    ),
    Resource(
        "crm.receivables", "crm", "回款", "crmReceivables/queryPageList",
        primary_key="receivablesId", detail_path="crmReceivables/queryById/{id}",
        filter_hints=("search", "ownerUserId", "customerId", "contractId", "returnTime"),
    ),
    Resource(
        "crm.invoices", "crm", "发票", "crmInvoice/queryPageList",
        primary_key="invoiceId", detail_path="crmInvoice/queryById/{id}",
        filter_hints=("search", "ownerUserId", "customerId", "contractId", "invoiceStatus"),
    ),
    _jxc("jxc.products", "产品", 1, "productId", "jxcProduct"),
    _jxc("jxc.suppliers", "供应商", 2, "supplierId", "jxcSupplier"),
    _jxc("jxc.purchase-orders", "采购订单", 3, "purchaseId", "jxcPurchase"),
    _jxc("jxc.purchase-returns", "采购退货单", 4, "retreatId", "jxcRetreat"),
    _jxc("jxc.sales-orders", "销售订单", 5, "saleId", "jxcSale"),
    _jxc("jxc.sales-returns", "销售退货单", 6, "salereturnId", "jxcSalereturn"),
    _jxc("jxc.receipts", "入库单", 7, "receiptId", "jxcReceipt"),
    _jxc("jxc.outbounds", "出库单", 8, "outboundId", "jxcOutbound"),
    _jxc("jxc.payments", "付款单", 9, "paymentNoteId", "jxcPayment"),
    _jxc("jxc.collections", "回款单", 10, "collectionNoteId", "jxcCollection"),
    _jxc("jxc.stock-checks", "库存盘点", 11, "inventoryId", "jxcInventory"),
    _jxc("jxc.stock-transfers", "库存调拨", 12, "allocationId", "jxcAllocation"),
    _jxc("jxc.stock-movements", "出入库明细", 13, "detailedId"),
    Resource(
        "jxc.warehouses", "jxc", "仓库", "jxcWarehouse/queryPageList",
        primary_key="warehouseId", filter_hints=("search",),
    ),
    Resource(
        "jxc.inventory", "jxc", "仓库产品库存", "jxcWarehouseProduct/queryPageList",
        primary_key="warehouseProductId", filter_hints=("warehouseId", "productId", "search"),
    ),
    Resource(
        "jxc.field-metadata", "jxc", "进销存字段元数据", "jxcField/queryFields",
        paginated=False,
    ),
    Resource(
        "hrm.employees", "hrm", "员工档案", "hrmEmployee/queryPageList",
        primary_key="employeeId", detail_path="hrmEmployee/queryById/{id}",
        sensitivity="confidential", filter_hints=("search", "deptId", "status", "employeeId"),
    ),
    Resource(
        "hrm.attendance", "hrm", "管理范围内的考勤记录", "hrmAttendanceClock/queryPageList",
        primary_key="clockId", sensitivity="confidential",
        filter_hints=("employeeId", "deptId", "startTime", "endTime"),
    ),
    Resource(
        "hrm.my-attendance", "hrm", "当前账号本人的考勤记录", "hrmAttendanceClock/queryMyPageList",
        primary_key="clockId", sensitivity="confidential",
        filter_hints=("startTime", "endTime"),
    ),
    Resource(
        "hrm.performance-cycles", "hrm", "绩效考核方案", "hrmAchievementAppraisal/queryAppraisalPageList",
        primary_key="appraisalId", detail_path="hrmAchievementAppraisal/queryAppraisalById/{id}",
        sensitivity="confidential", filter_hints=("status", "search", "startTime", "endTime"),
    ),
    Resource(
        "hrm.performance-records", "hrm", "员工绩效档案", "hrmAchievementAppraisal/queryEmployeeAppraisal",
        primary_key="employeeAppraisalId", detail_path="hrmAchievementAppraisal/queryEmployeeDetail/{id}",
        sensitivity="confidential", filter_hints=("employeeId", "appraisalId", "status"),
    ),
    Resource(
        "hrm.latest-payroll-period", "hrm", "最近工资核算期间", "hrmSalaryMonthRecord/queryLastSalaryMonthRecord",
        paginated=False, sensitivity="restricted",
    ),
    Resource(
        "hrm.payroll-records", "hrm", "工资核算记录", "hrmSalaryMonthRecord/querySalaryPageList",
        primary_key="employeeId", sensitivity="restricted",
        filter_hints=("srecordId", "employeeId", "deptId", "search"),
    ),
    Resource(
        "goals.dashboard", "goals", "目标管理总览", "biAchievement/moeduGoal/dashboard",
        paginated=False, filter_hints=("fiscalYear",),
    ),
    Resource(
        "goals.teams", "goals", "责任团队", "biAchievement/moeduGoal/team/list",
        paginated=False, primary_key="teamId", filter_hints=("fiscalYear", "teamId"),
    ),
    Resource(
        "goals.plans", "goals", "目标方案", "biAchievement/moeduGoal/plan/list",
        paginated=False, primary_key="planId", detail_path="biAchievement/moeduGoal/plan/detail",
        detail_body_key="id", filter_hints=("fiscalYear", "teamId", "status"),
    ),
    Resource(
        "goals.budgets", "goals", "毛利分配与费用包方案", "biAchievement/moeduGoal/budget/list",
        paginated=False, primary_key="companyBudgetId", detail_path="biAchievement/moeduGoal/budget/detail",
        detail_body_key="id", sensitivity="confidential",
        filter_hints=("fiscalYear", "teamId", "status"),
    ),
    Resource(
        "goals.ipi", "goals", "员工 IPI 责任书", "biAchievement/moeduGoal/ipi/list",
        paginated=False, primary_key="scorecardId", detail_path="biAchievement/moeduGoal/ipi/detail",
        detail_body_key="id", sensitivity="confidential",
        filter_hints=("fiscalYear", "employeeId", "teamId", "status"),
    ),
    Resource(
        "support.feedback", "support", "问题与建议反馈", "oaFeedback/admin/page",
        primary_key="feedbackId", detail_path="oaFeedback/detail/{id}",
        sensitivity="internal",
        filter_hints=("status", "reviewStatus", "feedbackType", "priority", "moduleCode", "keyword"),
    ),
    Resource(
        "workflow.oa-approvals", "workflow", "OA 审批实例", "examineWaiting/queryOaExamineList",
        primary_key="examineRecordId", sensitivity="confidential",
        filter_hints=("status", "categoryId", "startTime", "endTime"),
    ),
    Resource(
        "workflow.contract-approvals", "workflow", "合同审批实例", "examineWaiting/queryCrmExamineList",
        default_body={"label": 1}, primary_key="examineRecordId", sensitivity="confidential",
        filter_hints=("status", "startTime", "endTime"),
    ),
    Resource(
        "workflow.receivables-approvals", "workflow", "回款审批实例", "examineWaiting/queryCrmExamineList",
        default_body={"label": 2}, primary_key="examineRecordId", sensitivity="confidential",
        filter_hints=("status", "startTime", "endTime"),
    ),
    Resource(
        "workflow.invoice-approvals", "workflow", "发票审批实例", "examineWaiting/queryCrmExamineList",
        default_body={"label": 3}, primary_key="examineRecordId", sensitivity="confidential",
        filter_hints=("status", "startTime", "endTime"),
    ),
)

RESOURCES = {resource.name: resource for resource in RESOURCE_LIST}


def get_resource(name: str) -> Resource:
    try:
        return RESOURCES[name]
    except KeyError:
        raise KeyError("unknown resource: {0}".format(name))
