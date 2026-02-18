# VLM API Keys 配置说明

## 需要的 API Key

多模态功能需要 Vision Language Model (VLM) API。你需要**选择其中一个**：

### 选项1：Claude Vision（推荐）

**为什么推荐：**
- ✅ 质量好，价格适中
- ✅ API 简单易用
- ✅ 对工业场景理解好

**需要的 Key：**
- `ANTHROPIC_API_KEY` - Anthropic Claude API key

**获取方式：**
1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 在 Settings → API Keys 创建新 key
4. 复制 key 到 `.env` 文件

**配置：**
```bash
# 在 .env 文件中
VLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxx  # 你的真实 key
```

---

### 选项2：OpenAI GPT-4V

**需要的 Key：**
- `OPENAI_API_KEY` - OpenAI API key

**获取方式：**
1. 访问 https://platform.openai.com/api-keys
2. 注册/登录账号
3. 创建新 API key
4. 复制 key 到 `.env` 文件

**配置：**
```bash
# 在 .env 文件中
VLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx  # 你的真实 key
```

---

## 安装依赖

```bash
# Claude Vision
pip install anthropic

# 或 OpenAI GPT-4V
pip install openai

# 3D 可视化（必需）
pip install pyvista
```

或一次性安装（已在 requirements.txt 中）：
```bash
pip install -r requirements.txt
```

---

## 使用说明

1. **配置 `.env`**：
   - 选择 provider（claude 或 openai）
   - 填入对应的 API key
   - 设置 `VISION_FREQUENCY_SEC=5`（每5秒生成一次vision描述）

2. **启动 Simulator**：
   - 如果配置了 API key，Simulator 会自动：
     - 每5秒渲染一次3D模型
     - 调用 VLM API 分析图像
     - 发布 vision 描述到 MQTT `vision/pump01`

3. **查看 Vision 输出**：
   ```bash
   # 订阅 vision 消息
   mosquitto_sub -h localhost -p 1883 -t "vision/#" -v
   
   # 或查看日志
   tail -f logs/vision.jsonl
   ```

---

## 成本估算

- **Claude Vision**：约 $0.003-0.015 每张图片（取决于模型）
- **OpenAI GPT-4V**：约 $0.01-0.03 每张图片

如果每5秒生成一次，每小时约 720 张图片，成本约 $2-20/小时（取决于使用频率和模型）。

**建议**：测试时设置 `VISION_FREQUENCY_SEC=30`（每30秒一次），降低成本。

---

## 故障排查

**如果看到 "VLM client not initialized (no API key provided)"：**
- 检查 `.env` 文件中是否填写了 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`
- 确认 `VLM_PROVIDER` 设置正确（claude 或 openai）

**如果看到 "Could not initialize VLM client"：**
- 检查 API key 是否有效
- 检查网络连接（需要访问 API）
- 检查是否安装了对应的库（`anthropic` 或 `openai`）
