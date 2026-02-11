# MQTT Broker 设置指南

## 问题：Docker daemon 未运行

如果看到错误：`Cannot connect to the Docker daemon... Is the docker daemon running?`

---

## 解决方案 1：启动 Docker Desktop（推荐）

### macOS / Windows

1. **打开 Docker Desktop 应用**
   - macOS: 在 Applications 文件夹找到 Docker.app 并启动
   - Windows: 从开始菜单启动 Docker Desktop

2. **等待 Docker 启动完成**
   - 看到 Docker 图标在菜单栏/系统托盘显示为运行状态

3. **验证 Docker 运行**
   ```bash
   docker ps
   ```
   应该能看到容器列表（即使为空也说明 Docker 在运行）

4. **启动 Mosquitto**
   ```bash
   docker-compose up -d mosquitto
   ```

---

## 解决方案 2：本地安装 Mosquitto（不使用 Docker）

### macOS

```bash
# 使用 Homebrew
brew install mosquitto

# 启动 Mosquitto
brew services start mosquitto
# 或前台运行
mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf
```

### Linux (Ubuntu/Debian)

```bash
# 安装
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# 启动服务
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### Windows

1. 下载 Mosquitto: https://mosquitto.org/download/
2. 安装并启动服务

---

## 解决方案 3：不使用 MQTT（最简单）

**Simulator 可以不启动 MQTT 直接运行！**

MQTT 只是用于发布遥测数据，Simulator 仍然会：
- ✅ 正常运行
- ✅ 生成遥测数据
- ✅ 写入日志文件 `logs/telemetry.jsonl`
- ✅ 响应 API 请求

**只是不会发布到 MQTT broker。**

### 直接运行 Simulator（无需 MQTT）

```bash
# 激活 venv
source venv/bin/activate

# 运行 Simulator（会看到 MQTT 连接警告，可以忽略）
cd simulator-service
python3 main.py
```

你会看到类似警告：
```
Warning: Could not connect to MQTT broker: ...
Simulator will run but telemetry will not be published
```

**这是正常的，Simulator 会继续运行。**

---

## 验证 MQTT 是否工作

如果启动了 MQTT，可以测试：

```bash
# 发布测试消息
mosquitto_pub -h localhost -p 1883 -t test -m "hello"

# 订阅消息（在另一个终端）
mosquitto_sub -h localhost -p 1883 -t "test" -v
```

如果能看到消息，说明 MQTT 正常工作。

---

## 推荐方案

**对于快速测试：**
- 使用**解决方案 3**（不启动 MQTT）
- Simulator 会正常运行并写入日志文件
- 后续需要 MQTT 时再启动 Docker

**对于完整测试（需要 Agent 订阅 MQTT）：**
- 启动 Docker Desktop
- 运行 `docker-compose up -d mosquitto`
- 然后启动 Simulator
