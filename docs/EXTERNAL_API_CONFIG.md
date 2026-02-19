# External API 配置（Salesforce 等）

Agent D 在「批准」审核时，可勾选「创建 Salesforce Case」，将工单推到外部系统。本文说明如何配置。

---

## 1. 配置项（.env）

在项目根目录 `.env` 中配置（可参考 `.env.example`）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `SALESFORCE_DOMAIN` | Salesforce 实例域名（不含 https://） | `mycompany.my.salesforce.com` |
| `SALESFORCE_ACCESS_TOKEN` | 预置的 Access Token（推荐先用于联调） | 从 Salesforce 设置中复制 |
| `SALESFORCE_CLIENT_ID` | Connected App 的 Consumer Key | |
| `SALESFORCE_CLIENT_SECRET` | Connected App 的 Consumer Secret | |
| `SALESFORCE_USERNAME` | 用户名（用于 Password 流程） | |
| `SALESFORCE_PASSWORD` | 密码 + Security Token（用于 Password 流程） | |

- **至少配置**：`SALESFORCE_DOMAIN` + `SALESFORCE_ACCESS_TOKEN`，即可在批准时创建 Case。
- **不配置**：不填 `SALESFORCE_DOMAIN` 时，前端「创建 Salesforce Case」勾选不会真正调用 Salesforce，仅本地记录审核结果。

---

## 2. 获取 Salesforce Access Token（快速联调）

1. 登录 Salesforce → 右上角头像 → **Settings**。
2. 左侧 **Personal** → **Reset My Security Token**，获取并保存 **Security Token**。
3. 使用 Postman 或 curl 调用 OAuth2 密码流程，用 **用户名 + 密码+Security Token** 换 `access_token`，或使用 Salesforce 提供的 REST 测试工具拿到 Token。
4. 将得到的 `access_token` 填入 `.env` 的 `SALESFORCE_ACCESS_TOKEN`。

或使用 Connected App（见下节）获取 Token。

---

## 3. Connected App（推荐生产）

1. **Setup** → **App Manager** → **New Connected App**。
2. 勾选 **Enable OAuth Settings**。
3. **Callback URL** 可填 `https://localhost` 或你的应用回调地址。
4. **Selected OAuth Scopes** 至少包含：`Access and manage your data (api)`、`Perform requests at any time (refresh_token, offline_access)`（若用 refresh）。
5. 保存后得到 **Consumer Key**（即 `SALESFORCE_CLIENT_ID`）和 **Consumer Secret**（即 `SALESFORCE_CLIENT_SECRET`）。
6. 若用 **Password 流程**：在 `.env` 中配置 `SALESFORCE_USERNAME`、`SALESFORCE_PASSWORD`（密码为「账号密码 + Security Token」拼接）。不填 `SALESFORCE_ACCESS_TOKEN` 时，启动时会用 Client ID/Secret/Username/Password 换 Token。

---

## 4. 行为说明

- **前端**：Review Queue 批准弹窗中有「Create Salesforce Case」勾选；勾选后请求会带 `create_salesforce_case: true`。
- **后端**：仅当 `create_salesforce_case=True` 且 `get_ticket_connector()` 返回非空（即已配置 Salesforce）时，才会调用 Salesforce 创建 Case。
- **创建内容**：Case 的 Subject、Description 由当前诊断的 root_cause、asset_id、plant_id 及审批备注组成；Case 创建成功后会在本地 `tickets` 表插入一条记录（含 `ticket_id` 与 `url`），并写入 RAG 索引（若启用）。

---

## 5. 扩展其他工单系统

若要对接其他系统（如 Jira、自建工单 API）：

1. 在 `shared_lib/integrations/` 下新增模块，实现 `TicketConnector` 接口（见 `base.py` 的 `create_case`）。
2. 在 `shared_lib/config.py` 中增加该系统的配置项（如 URL、API Key）。
3. 在 `shared_lib/integrations/__init__.py` 的 `get_ticket_connector()` 中，根据配置返回对应 connector（或保留当前仅返回 Salesforce）。

Agent D 的 approve 流程只依赖 `get_ticket_connector()` 和 `create_case(...)`，不关心具体是 Salesforce 还是其他系统。
