# Moedu Business Data Skill

摩度全流程业财一体化平台的只读数据 CLI 与智能体 Skill。它把 CRM、进销存、HRM、绩效、目标和审批等后台接口整理为稳定资源，让 Mox AI 企业版或其他能够调用本地命令的智能体，在当前登录账号的授权范围内查询业务数据。

## 安全边界

- 只开放白名单查询资源，不提供新增、修改、删除和审批操作。
- CLI 原样携带当前登录账号的 CRM 会话，不生成管理员身份，也不绕过服务端角色、菜单和数据范围。
- 手机号、证件号、银行卡、邮箱和地址默认脱敏；工资类资源还需要显式确认。
- token 仅保存到权限为 `0600` 的本机配置；Skill、仓库和命令示例均不包含账号、密码或 token。
- “登录成功”只代表接口可用。实际可见范围由所在组织的 CRM 权限配置决定，正式接入前应使用至少两个不同权限账号做隔离验收。

详细约束见 [docs/security.md](docs/security.md)。

## 安装

要求 Python 3.9 或更高版本，不依赖第三方 Python 包。

```bash
git clone https://github.com/heavenzhang/moedu-business-data-skill.git
cd moedu-business-data-skill
python3 -m pip install -e .
moedu-agent doctor
```

也可以不安装，直接运行：

```bash
./bin/moedu-agent resources list --domain crm --format table
```

默认连接 `https://crm.moedu.com`。如连接独立部署实例，可通过 `MOEDU_BASE_URL` 指定地址。

## 登录

推荐在本机浏览器页面完成一次登录：

```bash
moedu-agent auth browser-login --username YOUR_USERNAME
```

授权页只监听 `127.0.0.1`，密码只发送到已配置的 CRM 登录接口，不写入本机配置或日志。成功后保存独立的 `type=4` 智能体会话，不影响 PC/H5 会话。无图形界面的服务器可使用终端登录：

```bash
moedu-agent auth login --username YOUR_USERNAME
```

不要在聊天、Skill 文件、仓库或命令历史里粘贴 token 和密码。

## 智能体接入

完整 Skill 位于 [skills/moedu-business-data](skills/moedu-business-data)。对于支持目录式 Skill 的工具，可安装或链接该目录；对于其他能够执行本地命令的智能体，按 `SKILL.md` 的安全顺序调用 `moedu-agent` 即可。

建议流程：

1. `moedu-agent doctor`：确认正式地址、登录身份和资源目录。
2. `moedu-agent resources describe crm.customers`：确认资源字段和过滤提示。
3. 先做一页小查询，再按需要扩大范围。
4. 只投影完成任务所需字段；无权限与有权限但无数据必须区分。

示例：

```bash
MOEDU_AGENT_ID=mox-ai \
  moedu-agent query crm.contracts \
  --filter startTime=2026-01-01 \
  --limit 20 \
  --select contractId,contractName,customerName,money,startTime,endTime
```

当前 Skill 不依赖 Mox AI，可以被 Mox AI、Codex、Claude Code 或其他支持本地 CLI 的智能体工具调用。不同产品对 Skill 目录格式的支持程度不同；不支持目录式 Skill 时，仍可直接使用 CLI。

## 资源范围

当前目录覆盖 39 个白名单资源，包括：

- CRM：客户、线索、商机、合同、回款、发票；
- 进销存：产品、供应商、采购、销售、库存与仓库；
- HRM：员工、考勤、工资、绩效；
- 目标、费用包、IPI、审批与反馈等业务资源。

查询返回稳定 JSON、请求 ID、分页信息，并写入不含业务数据的本机审计日志。

## 配置

| 环境变量 | 含义 |
| --- | --- |
| `MOEDU_BASE_URL` | 平台地址，默认 `https://crm.moedu.com` |
| `MOEDU_TOKEN` | 当前账号的 CRM 会话；优先于本机配置 |
| `MOEDU_AGENT_ID` | 调用智能体的稳定标识 |
| `MOEDU_TIMEOUT` | HTTP 超时秒数 |
| `MOEDU_CONFIG_FILE` | 自定义配置文件位置 |
| `MOEDU_AUDIT_FILE` | 自定义本地审计日志位置 |

默认配置与审计文件位于 `~/.config/moedu-agent/`，权限为 `0600`。

## 输出契约

```json
{
  "ok": true,
  "resource": "crm.contracts",
  "request_id": "...",
  "duration_ms": 123,
  "data": [],
  "page": {
    "number": 1,
    "size": 20,
    "returned": 0,
    "total": 0,
    "total_pages": 0
  }
}
```

错误输出同样为 JSON，并返回非零退出码，便于智能体稳定处理。

## 当前限制

- 目前是 CLI + Skill，不是 MCP Server。
- CRM 正式后端的一次性授权码/PKCE 接口尚未正式上线，因此当前版本使用本机回环登录页取得个人会话。
- CRM 按 ID 查详情接口尚未全部具备一致的服务端数据范围校验，因此公开 Skill 暂只开放 CRM 列表查询。
- 仓库暂未附加开源许可证；公开可见不等同于授予再分发或商用许可。
