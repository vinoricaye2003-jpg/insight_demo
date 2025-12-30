# 🔄 切换到Qwen模型配置指南

## ✅ 修改已完成

系统已从 DeepSeek 切换到 **阿里云通义千问（Qwen）**

---

## 📋 使用步骤

### 1. 获取API Key

访问：https://dashscope.console.aliyun.com/apiKey

- 登录阿里云账号
- 开通DashScope服务（免费额度）
- 创建API Key

### 2. 设置环境变量

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"
```

**永久设置（推荐）:**
```powershell
[System.Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "sk-your-key", "User")
```

**或者在 .env 文件中:**
```
DASHSCOPE_API_KEY=sk-your-api-key-here
```

### 3. 运行系统

```powershell
.\.venv\Scripts\python.exe market_insight_system.py
```

---

## 🎯 可用模型

修改 `__init__` 方法中的默认模型：

| 模型 | 适用场景 | 成本 |
|------|---------|------|
| `qwen-turbo` | 快速响应，一般任务 | 低 |
| `qwen-plus` | **推荐**，性能均衡 | 中 |
| `qwen-max` | 复杂推理，最高质量 | 高 |
| `qwen-long` | 超长文本处理 | 中高 |

**使用示例：**
```python
# 方式1：修改默认模型（已设置为qwen-plus）
system = MarketInsightSystem(api_key=api_key)

# 方式2：运行时指定模型
system = MarketInsightSystem(api_key=api_key, model="qwen-max")
```

---

## 🔧 修改内容说明

### 修改1：API配置（第28-31行）
```python
# 旧配置
base_url="https://api.deepseek.com"
model="deepseek-chat"

# 新配置
base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
model="qwen-plus"
```

### 修改2：环境变量（第880行）
```python
# 旧
api_key = os.getenv("DEEPSEEK_API_KEY")

# 新
api_key = os.getenv("DASHSCOPE_API_KEY")
```

---

## 🆚 DeepSeek vs Qwen 对比

| 维度 | DeepSeek | Qwen |
|------|----------|------|
| 推理能力 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 中文理解 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 响应速度 | 快 | 很快 |
| 价格 | 低 | 低 |
| 免费额度 | 有 | 有 |
| 国内访问 | 稳定 | 非常稳定 |

**推荐理由**：Qwen在中文场景下表现更优，且阿里云服务在国内更稳定。

---

## 🔀 如何切换回DeepSeek

如果需要切换回DeepSeek，修改三处：

1. **第28行**：`base_url="https://api.deepseek.com"`
2. **第20行**：`model="deepseek-chat"`
3. **第880行**：`api_key = os.getenv("DEEPSEEK_API_KEY")`

---

## 🐛 常见问题

### Q1: 报错 "401 Unauthorized"
**解决**：检查API Key是否正确设置
```powershell
echo $env:DASHSCOPE_API_KEY  # 查看当前值
```

### Q2: 报错 "rate limit exceeded"
**解决**：
- 免费额度用尽，需要充值
- 或降低并发，增加请求间隔

### Q3: 想使用其他Qwen模型
**解决**：
```python
# 在main函数中修改
system = MarketInsightSystem(api_key=api_key, model="qwen-max")
```

---

## 📊 测试验证

运行测试：
```powershell
echo 1 | .\.venv\Scripts\python.exe market_insight_system.py
```

成功标志：
```
✓ 加载数据: 6月 - 389 行, 27 列
✓ 加载数据: 12月 - 412 行, 27 列
[Analyst] 正在分析数据...
洞察: ...（生成内容）
```

---

## 💡 优化建议

1. **如果响应慢**：切换到 `qwen-turbo`
2. **如果质量不够**：切换到 `qwen-max`
3. **处理长文本**：使用 `qwen-long`（支持100万tokens）

---

**修改完成！** 🎉 现在可以直接使用Qwen模型了。
