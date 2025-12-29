# XHS-MarketAI System - 自进化数据挖掘机 (Self-Evolving Data Miner)

## 📋 系统概述

**XHS-MarketAI 洞察闭环系统**是一个基于 DeepSeek API 的智能市场洞察系统，能够自动分析小红书/电商数据，通过迭代式挖掘生成可验证的市场洞察。

### 核心特性
- ✅ **Analyst (洞察生成专家)**: 基于 LLM 的智能数据分析，自动生成下一轮挖掘指令
- ✅ **Auditor (事实审计员)**: 
  - 数据验证：硬核校验防止 AI 幻觉
  - 逻辑审计：检查推理是否过度
  - 纠错反馈：发现错误自动反馈给 Analyst
- ✅ **Controller (逻辑控制器)**: 
  - 向量语义分析（Embedding + 余弦相似度）
  - 连续高相似度检测（连续2轮 > 0.9 自动停止）
  - 新关键词密度监测
  - 自动化迭代控制

### 系统架构

```
初始提示 → Analyst (生成洞察 + 证据 + 下一轮指令)
              ↓
         Auditor (数据验证 + 逻辑审计)
              ↓
         Controller (新鲜度检查: 向量相似度 + 关键词密度)
              ↓
      CONTINUE → 自动进入下一轮 / STOP → 输出完整结果
```

## 🚀 快速开始

### 1. 环境配置

#### 创建虚拟环境（推荐）

**Windows (PowerShell):**
```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到权限错误，执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**macOS/Linux:**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖包说明:**
- `pandas`: 数据处理和分析
- `openpyxl`: Excel 文件读取支持
- `openai`: DeepSeek API 客户端（兼容 OpenAI SDK）

### 3. 配置 API Key

#### 方法 1: 环境变量（推荐）

**Windows (PowerShell):**
```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
```

**macOS/Linux:**
```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

#### 方法 2: .env 文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
```

#### 方法 3: 代码中直接设置

在 `market_insight_system.py` 的 `main()` 函数中：
```python
system = MarketInsightSystem(api_key="your_api_key_here")
```

### 4. 运行系统

```bash
python market_insight_system.py
```

## 📊 数据文件要求

系统会自动加载以下文件：
- `搜索词-2025-6月.xlsx - Sheets1.csv`
- `搜索词-2025-12月.xlsx - Sheets1.csv`

**数据格式要求:**
- 必须包含 `关键词` 列
- 推荐包含 `搜索指数`、`笔记数`、`互动数` 等列
- CSV 文件编码：UTF-8

## 🔧 高级配置

### 修改模型参数

在代码中找到 `MarketInsightSystem` 类的初始化：

```python
system = MarketInsightSystem(
    api_key="your_key",
    model="deepseek-chat",  # 可选：deepseek-coder
)
```

### 调整迭代次数

```python
system.max_iterations = 5  # 默认 5 轮
```

### 自定义分析提示词

修改 `user_initial_prompt` 变量：
```python
user_initial_prompt = """
[核心背景]
你的产品和竞品信息...

[分析要求]
你的具体分析需求...
"""
```

## 📤 输出说明

### 控制台输出
- 实时显示每轮分析进度
- 显示审计验证结果
- 显示控制器决策

### JSON 文件输出
生成 `insight_result_round1.json`，包含：
```json
{
  "status": "Success",
  "iteration": 1,
  "audit_report": {
    "is_passed": true,
    "log": "验证日志..."
  },
  "analyst_result": {
    "insight": "洞察结论...",
    "evidence_trace": [...]
  },
  "system_generated_next_prompt": "下一轮分析建议...",
  "controller_decision": "CONTINUE"
}
```

## 🐛 常见问题

### 1. API 调用失败
- 检查 API Key 是否正确
- 检查网络连接
- 确认 DeepSeek API 余额

### 2. 数据加载失败
- 确认文件路径正确
- 检查 CSV 编码（推荐 UTF-8）
- 确认列名包含中文时没有乱码

### 3. 证据验证失败
- 检查数据列名是否正确（如 `关键词`、`搜索指数`）
- 确认数据中确实存在 LLM 提到的关键词
- 调低温度参数（temperature）提高精确度

## 📈 系统架构

```
用户输入 → Analyst (LLM 分析)
              ↓
         生成洞察 + 证据
              ↓
         Auditor (数据验证)
              ↓
         Controller (决策)
              ↓
      CONTINUE → 下一轮 / STOP → 输出结果
```

## 🎯 使用示例

### 案例：松达松子粉 vs 贝亲桃子水

系统会自动：
1. 对比 6 月和 12 月的搜索数据
2. 识别季节性差异
3. 发现淡季布局机会词
4. 验证所有数值证据
5. 生成下一轮挖掘建议

## 📝 开发说明

### 扩展系统

1. **添加新数据源**: 修改 `load_data()` 方法
2. **自定义验证逻辑**: 扩展 `auditor_verify_evidence()` 方法
3. **调整决策策略**: 修改 `controller_decide_next()` 方法

### 多轮迭代运行

```python
# 在 main() 函数中添加循环
current_prompt = user_initial_prompt
for i in range(5):
    result = system.run_single_iteration(current_prompt, data_dict)
    if result["controller_decision"] == "STOP":
        break
    current_prompt = result["system_generated_next_prompt"]
```

## 📞 支持

如有问题，请检查：
1. Python 版本 >= 3.8
2. 依赖包版本兼容性
3. API Key 权限
4. 数据文件格式

---

**版本**: 1.0.0  
**最后更新**: 2025-12-29
