# 多模态功能快速开始

## 1. 安装依赖

```bash
pip install pyvista anthropic
# 或
pip install -r requirements.txt
```

## 2. 配置 API Key

在 `.env` 文件中添加（**二选一**）：

**选项A：Claude Vision（推荐）**
```bash
VLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxx  # 你的真实 key
```

**选项B：OpenAI GPT-4V**
```bash
VLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx  # 你的真实 key
```

**获取 API Key：**
- Claude: https://console.anthropic.com/ → Settings → API Keys
- OpenAI: https://platform.openai.com/api-keys

## 3. 启动 Simulator

```bash
python simulator-service/main.py
```

如果看到：
```
[Simulator] 3D renderer initialized
[Simulator] VLM client (Claude) initialized
```
说明多模态功能已启用。

## 4. 查看 Vision 输出

**订阅 vision 消息：**
```bash
mosquitto_sub -h localhost -p 1883 -t "vision/#" -v
```

**或查看日志：**
```bash
tail -f logs/vision.jsonl
```

## 5. 工作原理

1. Simulator 每5秒（可配置）渲染一次3D泵模型
2. 根据传感器数据更新颜色（振动高→红色，温度高→橙色等）
3. 截图保存为 PNG
4. 调用 VLM API 分析图像
5. VLM 返回文本描述（例如："泵体呈红色，表示振动异常"）
6. 发布 vision 描述到 MQTT `vision/pump01`

## 配置选项

在 `.env` 中：
- `VISION_FREQUENCY_SEC=5` - 每N秒生成一次vision（默认5秒）
- `VLM_PROVIDER=claude` - 选择 VLM provider

## 成本

- Claude Vision: ~$0.003-0.015 每张图片
- OpenAI GPT-4V: ~$0.01-0.03 每张图片

如果每5秒一次，每小时约720张图片。建议测试时设为30秒降低成本。
