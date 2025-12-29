# 🔐 环境变量配置指南

## 📝 快速开始

### 1. 创建 .env 文件

将 `.env.example` 复制为 `.env`：

```powershell
Copy-Item .env.example .env
```

或手动创建 `.env` 文件。

### 2. 填入API密钥

编辑 `.env` 文件，将 `your-dashscope-api-key-here` 替换为你的真实密钥：

```env
DASHSCOPE_API_KEY=sk-abc123...
```

### 3. 运行系统

```powershell
.\.venv\Scripts\python.exe market_insight_system.py
```

系统会自动从 `.env` 文件加载密钥，无需手动设置环境变量！

---

## 🔑 获取API密钥

### 阿里云通义千问（Qwen）- 当前使用

1. 访问：https://dashscope.console.aliyun.com/apiKey
2. 登录阿里云账号
3. 点击"创建 API-KEY"
4. 复制密钥，填入 `.env` 文件

**免费额度**：新用户赠送100万tokens

### DeepSeek（备用）

1. 访问：https://platform.deepseek.com/api_keys
2. 注册/登录账号
3. 创建 API Key
4. 复制密钥，填入 `.env` 文件

---

## 📁 .env 文件示例

```env
# 必填：通义千问API密钥
DASHSCOPE_API_KEY=sk-a1b2c3d4e5f6g7h8i9j0

# 可选：如需切换到DeepSeek
# DEEPSEEK_API_KEY=sk-1234567890abcdef

# 可选：如需使用OpenAI的Embedding
# OPENAI_API_KEY=sk-proj-xyz123
```

---

## 🔄 切换API提供商

### 切换到DeepSeek

1. 在 `.env` 中添加 DeepSeek 密钥
2. 修改 `market_insight_system.py` 第28-31行：

```python
base_url="https://api.deepseek.com"
model="deepseek-chat"
```

3. 修改第27行环境变量名：

```python
self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
```

### 切换到其他模型

修改 `model` 参数：

- Qwen: `qwen-turbo`, `qwen-plus`, `qwen-max`, `qwen-long`
- DeepSeek: `deepseek-chat`, `deepseek-coder`

---

## ⚠️ 安全提示

### ✅ 必须做

1. **永远不要提交 `.env` 到Git**
   - 已在 `.gitignore` 中排除
   - 只提交 `.env.example` 模板

2. **定期更换密钥**
   - 如果密钥泄露，立即在控制台删除

3. **设置使用限额**
   - 在API控制台设置每日/每月上限

### ❌ 禁止做

- ❌ 将 `.env` 文件分享给他人
- ❌ 在公开代码中硬编码密钥
- ❌ 将密钥上传到GitHub/GitLab
- ❌ 在截图/日志中暴露密钥

---

## 🐛 常见问题

### Q1: 提示"未找到API密钥"

**原因**：`.env` 文件不存在或密钥未填写

**解决**：
```powershell
# 检查 .env 文件是否存在
Test-Path .env

# 查看内容
Get-Content .env

# 确保填写了正确的密钥
DASHSCOPE_API_KEY=sk-your-real-key
```

### Q2: 密钥无效/401错误

**原因**：密钥填写错误或已过期

**解决**：
1. 检查密钥是否完整（通常以 `sk-` 开头）
2. 去API控制台验证密钥状态
3. 重新生成新密钥

### Q3: 如何验证密钥是否生效

**测试代码**：
```python
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("DASHSCOPE_API_KEY")
print(f"密钥前10位: {key[:10] if key else 'None'}")
print(f"密钥长度: {len(key) if key else 0}")
```

---

## 📂 项目文件结构

```
insight_demo/
├── .env                # 你的密钥文件（不提交Git）
├── .env.example        # 密钥模板（提交Git）
├── .gitignore          # 已包含 .env
├── market_insight_system.py
└── requirements.txt    # 已包含 python-dotenv
```

---

## 🚀 优势

使用 `.env` 文件的好处：

1. ✅ **安全**：密钥不会硬编码在代码中
2. ✅ **方便**：无需每次手动设置环境变量
3. ✅ **团队协作**：每人有自己的 `.env`，互不干扰
4. ✅ **多环境**：开发/测试/生产用不同的 `.env` 文件

---

**配置完成后**，直接运行系统即可，密钥会自动加载！🎉
