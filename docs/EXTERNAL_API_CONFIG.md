# External API 配置（Salesforce 等）

Agent D 在「批准」审核时，可勾选「创建 Salesforce Case」，将工单推到外部系统。本文说明如何配置。

---

## 免费用户能用吗？能创建 Connected App 吗？

**可以。** 常见情况如下：

- **Developer Edition（开发者版）**：免费注册，支持 API、Connected App、完整设置菜单。适合个人开发/联调，推荐用这个创建 Connected App。
- **免费试用（Trial）**：通常也支持 API 和 Connected App，和正式版功能类似。
- **极简免费版（如 Salesforce CRM Free）**：可能没有 Setup 或 API，若看不到「App Manager」就说明当前版本不支持，可先注册一个 [Developer Edition](https://developer.salesforce.com/signup) 再按下面步骤操作。

注册 Developer Edition：打开 [developer.salesforce.com/signup](https://developer.salesforce.com/signup)，填邮箱、姓名等，完成后用该账号登录即可使用 Setup 和 App Manager。

---

## 怎么创建 Connected App（详细步骤）

1. **进入设置**  
   登录 Salesforce 后，点击右上角 **齿轮图标** → **Setup**。

2. **打开 App Manager**  
   左侧 **Quick Find** 搜索框输入 **App Manager**，回车，进入 **App Manager** 页面。

3. **新建 Connected App**  
   点击右上角 **New Connected App**。

4. **填写基本信息**  
   - **Connected App Name**：必填，例如 `Agent D` 或 `My Ticket App`。  
   - **API Name**：会自动根据名称生成，一般不用改。  
   - **Contact Email**：填你的邮箱。  
   - **Description**、**Logo** 等可留空。

5. **启用 OAuth**  
   勾选 **Enable OAuth Settings**。勾选后会出现：  
   - **Callback URL**：必填，可填 `https://localhost` 或 `https://login.salesforce.com`（仅用于 OAuth 流程，本项目的密码模式不依赖回调）。  
   - **Selected OAuth Scopes**：在左侧列表至少勾选：  
     - **Access and manage your data (api)**  
     - **Perform requests at any time (refresh_token, offline_access)**  
   然后点 **Add** 移到右侧。

6. **其他选项**  
   - **Require Secret for Web Server Flow**：保持勾选（会生成 Consumer Secret）。  
   - **Require Secret for Refresh Token Flow**：可选。  
   - 其他保持默认即可。

7. **保存并等待生效**  
   点击 **Save**，再点 **Continue**。  
   Salesforce 会提示 Connected App 需要 **2–10 分钟** 才会生效，生效后才能用 Consumer Key/Secret 换 Token。

8. **拿到 Consumer Key 和 Consumer Secret**  
   - 在 **App Manager** 列表里找到刚创建的 App，点击右侧 **▼** → **Manage**。  
   - 在 **API (Enable OAuth Settings)** 区域可以看到 **Consumer Key**（即 `SALESFORCE_CLIENT_ID`）。  
   - **Consumer Secret** 会显示为 *****，点击 **Click to reveal** 后复制，即 `SALESFORCE_CLIENT_SECRET`。  
   - 若没有 **Manage**，可点 App 名称进入详情，在同一区域查看。

9. **配置到项目**  
   把 **Consumer Key**、**Consumer Secret** 和 **域名、用户名、密码+Security Token** 按文档「方式 B」填到 `.env` 即可。

---

## 一步一步配置（手把手）

任选一种方式：**方式 A** 最快（只填域名 + Token）；**方式 B** 适合长期用（用 Connected App 自动换 Token）。

---

### 方式 A：只用 Access Token（最快，先跑通）

**第 1 步：拿到你的 Salesforce 域名**

1. 用浏览器登录你的 Salesforce（例如公司给的 `https://xxx.my.salesforce.com`）。
2. 登录后看浏览器地址栏，域名就是 `https://` 后面、第一个 `/` 之前的那一段。
3. 例如地址是 `https://mycompany.my.salesforce.com/lightning/...`，则域名为：`mycompany.my.salesforce.com`。
4. 打开项目根目录的 **`.env`** 文件，找到或添加一行，填上（把下面换成你的实际域名）：
   ```env
   SALESFORCE_DOMAIN=mycompany.my.salesforce.com
   ```

**第 2 步：在 Salesforce 里拿到 Security Token**

1. 登录 Salesforce 后，点击右上角 **头像（或齿轮图标）**。
2. 点击 **Settings（设置）**。
3. 左侧菜单找到 **Personal（个人）** → **Reset My Security Token（重置我的安全令牌）**。
4. 点击 **Reset My Security Token**，系统会把新的 **Security Token** 发到你的登录邮箱。
5. 打开邮件，复制那一串 Token（只含字母数字，无空格），先保存到记事本备用。

**第 3 步：用用户名 + 密码 + Security Token 换 Access Token**

用下面任一方式拿到 `access_token`：

- **用 curl（终端）：** 在终端执行（把 `你的域名`、`你的登录邮箱`、`你的登录密码`、`上一步拿到的SecurityToken` 换成真实值，密码和 Token 直接拼在一起，中间不要空格）：
  ```bash
  curl -X POST "https://你的域名/services/oauth2/token" \
    -d "grant_type=password" \
    -d "client_id=你的ConsumerKey（见下方方式B第2步）" \
    -d "client_secret=你的ConsumerSecret" \
    -d "username=你的登录邮箱" \
    -d "password=你的登录密码你的SecurityToken"
  ```
  若你还没有 Connected App，可先走 **方式 B 第 1～2 步** 创建 App 拿到 Consumer Key/Secret，再用上面命令；返回的 JSON 里 `access_token` 就是你要的。

- **或用 Postman：**  
  - URL: `https://你的域名/services/oauth2/token`  
  - Method: **POST**  
  - Body 选 **x-www-form-urlencoded**，填：`grant_type=password`、`client_id`、`client_secret`、`username`、`password`（password = 登录密码 + Security Token 拼在一起）。  
  - 发送后，响应里的 `access_token` 复制下来。

**第 4 步：把 Access Token 和域名写进 .env**

在项目根目录的 **`.env`** 里确保有这两行（值换成你上几步拿到的）：

```env
SALESFORCE_DOMAIN=mycompany.my.salesforce.com
SALESFORCE_ACCESS_TOKEN=这里粘贴你拿到的 access_token
```

保存 `.env` 后，重启 Agent D（或整个项目）。在 Review Queue 里批准一条请求并勾选「创建 Salesforce Case」，此时应会在 Salesforce 里创建 Case。

---

### 方式 B：用 Connected App + 用户名密码（推荐长期使用）

**第 1 步：创建 Connected App**

1. 登录 Salesforce → 右上角 **齿轮图标** → **Setup（设置）**。
2. 左侧搜索框输入 **App Manager**，进入 **App Manager**。
3. 点击 **New Connected App**。
4. **Connected App Name** 随便填，例如 `Agent D Ticket`。
5. **API Name** 会自动生成，不用改。
6. 勾选 **Enable OAuth Settings**。
7. **Callback URL** 填：`https://localhost`（仅用于拿 Token，不必真实可访问）。
8. **Selected OAuth Scopes** 里至少勾选：
   - `Access and manage your data (api)`
   - `Perform requests at any time (refresh_token, offline_access)`
9. 点击 **Save**，等待约 2～10 分钟（Salesforce 会提示等待生效）。

**第 2 步：拿到 Consumer Key 和 Consumer Secret**

1. 保存后，在 App Manager 列表里找到刚创建的 App，点右侧 **▼** → **Manage**。
2. 页面里可以看到 **Consumer Key**（即 Client ID）和 **Consumer Secret**。点击 **Click to reveal** 显示 Consumer Secret，复制保存。
3. 若在「Manage」里没看到，可回到 **Setup** → **App Manager** → 点该 App 名称进入，在 **API (Enable OAuth Settings)** 区域查看。

**第 3 步：拿到 Security Token（若还没有）**

同方式 A 第 2 步：**Settings** → **Personal** → **Reset My Security Token**，从邮件里复制 Security Token。

**第 4 步：填写 .env**

在项目根目录的 **`.env`** 里填（全部换成你的实际值）：

```env
SALESFORCE_DOMAIN=mycompany.my.salesforce.com
SALESFORCE_CLIENT_ID=你的 Consumer Key
SALESFORCE_CLIENT_SECRET=你的 Consumer Secret
SALESFORCE_USERNAME=你的登录邮箱
SALESFORCE_PASSWORD=你的登录密码你的SecurityToken
```

说明：`SALESFORCE_PASSWORD` 是 **账号密码** 和 **Security Token** 直接拼在一起，中间不加空格或符号。例如密码是 `Abc123`，Token 是 `xyz789`，则填 `Abc123xyz789`。

**不要**在 .env 里填 `SALESFORCE_ACCESS_TOKEN`，程序会用上面的信息自动换 Token。

保存后重启服务，批准时勾选「创建 Salesforce Case」即可。

---

### 方式 C：Client Credentials Flow（仅 Client ID + Secret）

若在 Connected App 里勾选了 **Enable Client Credentials Flow**，则只需配置 **域名 + Consumer Key + Consumer Secret**，无需用户名、密码和 Security Token。

**重要**：启用 Client Credentials 后，必须在 Connected App 里指定 **Run As User**（以哪个用户身份调用 API）。  
编辑该 App → 找到 **Client Credentials Flow** 区域 → 设置 **Run As** / **Run As User** 为某个用户（如你自己）→ 保存。否则会报错 `no client credentials user enabled`。

在 **`.env`** 里填：

```env
SALESFORCE_DOMAIN=你的公司.my.salesforce.com
SALESFORCE_CLIENT_ID=你的 Consumer Key
SALESFORCE_CLIENT_SECRET=你的 Consumer Secret
```

不填 `SALESFORCE_ACCESS_TOKEN`、`SALESFORCE_USERNAME`、`SALESFORCE_PASSWORD`。程序会自动用 Client Credentials 流程换 Token。保存后重启服务即可。

---

### 验证是否配好

1. 确保 `.env` 里至少有两种之一：
   - 方式 A：`SALESFORCE_DOMAIN` + `SALESFORCE_ACCESS_TOKEN`
   - 方式 B：`SALESFORCE_DOMAIN` + `SALESFORCE_CLIENT_ID` + `SALESFORCE_CLIENT_SECRET` + `SALESFORCE_USERNAME` + `SALESFORCE_PASSWORD`
2. 重启 Agent D（或 `npm run dev` / 启动脚本）。
3. 在前端进入 Review Queue，对一条记录点击「批准」，勾选「Create Salesforce Case」，提交。
4. 到 Salesforce 里打开 **Cases** 列表，应能看到刚创建的 Case；本地 `tickets` 表也会有一条记录。

若报错，检查：域名是否带 `https://`（不要带）、密码是否已拼接 Security Token、Connected App 是否已生效（等几分钟）。

---

### 两种 Flow 的区别（Connected App 里两个勾选）

| Connected App 勾选 | 含义 | 脚本里对应 |
|--------------------|------|------------|
| **Enable Client Credentials Flow** | 用 Client ID + Secret 换 Token，无需用户名密码；需在 App 里设 **Run As User**。适合后端/脚本。 | 脚本会试：`grant_type=client_credentials`（[1/2]） |
| **Enable Authorization Code and Credentials Flow** | 授权码流程：用户浏览器登录后拿 code，再用 code + Client ID/Secret 换 Token。需用户参与，脚本无法自动试。 | 脚本不试（需浏览器） |

**Username-Password Flow** 对应组织设置里的 **Allow OAuth Username-Password Flows** + App 允许；脚本会试 `grant_type=password`（[2/2]）。

跑 `python scripts/test_salesforce_connection.py` 会依次尝试 [1/2] Client Credentials、[2/2] Password，并打印各自成功或失败原因。

---

### 常见错误（测试脚本报错时对照）

| 报错信息 | 原因 | 处理 |
|----------|------|------|
| `no client credentials user enabled` | Client Credentials 已开启，但未指定“以谁身份”运行 | 编辑 Connected App，在 **Client Credentials Flow** 里设置 **Run As User** 为某个用户，保存后等几分钟 |
| `authentication failure`（Password 流程） | 用户名/密码认证失败 | ① `SALESFORCE_PASSWORD` 必须是 **登录密码 + Security Token** 直接拼接（无空格）<br>② Connected App 勾选 **Allow Username-Password Authentication**<br>③ `SALESFORCE_USERNAME` 填完整登录邮箱 |
| `invalid_client` | Client ID 或 Secret 错误 | 核对 Consumer Key / Consumer Secret，或重新 Reveal 并复制 Secret |

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
