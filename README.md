# XHS-MarketAI 市场洞察系统 v4.0

**自进化数据挖掘机 - 三智能体协同洞察引擎**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 系统概览

XHS-MarketAI 是一个基于多智能体架构的市场洞察系统，专为小红书(XHS)搜索数据分析设计。通过 **Analyst（分析师）**、**Auditor（审计师）** 和 **Controller（控制器）** 三个智能体的协同工作，实现数据驱动的深度洞察挖掘。

### 核心特性

- ✅ **三智能体协同架构**：分析→审计→决策闭环
- ✅ **自动证据验证**：100%数据溯源，杜绝幻觉
- ✅ **智能新鲜度检查**：自动识别重复洞察，保证内容独特性
- ✅ **反常识洞察框架**：5维分析（逆势增长、反季节、非主流、空白机会、对抗性趋势）
- ✅ **强制6月vs12月对比**：季节性分析内置
- ✅ **数据质量自适应**：自动检测并禁用缺失维度分析
- ✅ **战术建议多样化**：8种策略类型（SEO优化、内容营销、竞品对标等）

---

## 🚀 快速开始

### 1. 环境设置

```bash
# Windows
setup.bat

# Linux/macOS
chmod +x setup.sh
./setup.sh
```

### 2. 配置API密钥

复制 `.env.example` 为 `.env`，填入你的 DashScope API Key：

```bash
DASHSCOPE_API_KEY=sk-your-api-key-here
```

> 获取API Key: [https://dashscope.console.aliyun.com/](https://dashscope.console.aliyun.com/)

### 3. 准备数据

将Excel数据文件放入 `data/` 目录，格式要求：

```
data/
├── 搜索词-2025-6月.xlsx
└── 搜索词-2025-12月.xlsx
```

必需列：`搜索词`, `搜索次数指数`, `自然笔记数`, `商业笔记数`, `标题`, `内容`

### 4. 运行系统

```bash
# 单轮测试（仅第一轮）
python market_insight_system.py

# 或使用批处理脚本
run.bat
```

---

## 📊 输出文件

运行后会在 `output/` 目录生成：

| 文件 | 说明 |
|------|------|
| `EXECUTIVE_SUMMARY.md` | 🎯 **执行摘要**（决策者首选） |
| `insight_full_cycle.md` | 完整分析报告（所有轮次） |
| `insight_full_cycle.json` | 结构化数据（可编程调用） |
| `insight_result_round1.md` | 单轮测试报告 |

---

## 🧪 测试验证

运行改进测试套件：

```bash
python test_improvements.py
```

验证内容：
- ✅ 自然笔记数范围值解析（"9000-10000" → 9500）
- ✅ 数据质量检查（市场出价全0自动禁用）
- ✅ 6月vs12月对比数据准备
- ✅ System Prompt核心改进点

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   Controller（控制器）                    │
│  • 证据验证（100%溯源）                                   │
│  • 新鲜度检查（去重）                                     │
│  • 决策引擎（CONTINUE/STOP）                             │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
      ┌──────▼──────┐            ┌───────▼───────┐
      │   Analyst   │◄───────────┤    Auditor    │
      │  （分析师）  │   错误反馈   │   （审计师）  │
      │  生成洞察    │            │   验证证据    │
      └─────────────┘            └───────────────┘
```

### 工作流程

1. **Analyst** 分析数据，生成洞察（包含6月vs12月对比）
2. **Auditor** 逐条验证证据（关键词、数值、行号）
3. **Controller** 审查结果：
   - 证据通过 → 新鲜度检查 → 决策是否继续
   - 证据失败 → 反馈错误 → Analyst修正（最多2次）

---

## 📚 项目结构

```
insight_demo/
├── market_insight_system.py    # 主系统（1418行）
├── test_improvements.py         # 测试套件
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量模板
├── data/                        # 📁 数据文件
│   ├── 搜索词-2025-6月.xlsx
│   └── 搜索词-2025-12月.xlsx
├── output/                      # 📁 输出结果
│   ├── EXECUTIVE_SUMMARY.md
│   ├── insight_full_cycle.md
│   └── insight_full_cycle.json
└── docs/                        # 📁 技术文档
    ├── SYSTEM_ARCHITECTURE.md   # 架构详解
    ├── ENV_SETUP.md             # 环境配置
    ├── OUTPUT_FORMATS.md        # 输出格式说明
    ├── QWEN_SETUP.md            # Qwen API配置
    └── history/                 # 历史报告
        ├── SELF_AUDIT_REPORT.md
        ├── IMPROVEMENT_COMPLETION_REPORT.md
        └── ...
```

---

## 🔧 技术栈

- **Python 3.8+**
- **通义千问 (Qwen-Plus)**: 多智能体推理引擎
- **Pandas**: 数据处理
- **OpenAI SDK**: DashScope API调用
- **Python-dotenv**: 环境变量管理

---

## 📖 文档索引

| 文档 | 说明 |
|------|------|
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | 系统架构详解（三智能体设计） |
| [ENV_SETUP.md](docs/ENV_SETUP.md) | 环境配置指南 |
| [OUTPUT_FORMATS.md](docs/OUTPUT_FORMATS.md) | 输出文件格式说明 |
| [QWEN_SETUP.md](docs/QWEN_SETUP.md) | 通义千问API配置 |
| [运行指南.md](运行指南.md) | 中文详细运行手册 |

---

## 💡 使用技巧

### 1. 单轮测试 vs 完整循环

- **单轮测试**：快速验证系统功能，生成第一轮洞察（约1-2分钟）
- **完整循环**：自动迭代5-10轮，直到无新发现（约5-15分钟）

### 2. 读取输出

优先级：`EXECUTIVE_SUMMARY.md` > `insight_full_cycle.md` > JSON

**EXECUTIVE_SUMMARY.md** 仅包含高质量洞察（审计通过+新鲜度合格），适合决策者快速阅读。

### 3. 自定义配置

修改 `market_insight_system.py` 第1390-1404行：

```python
# 自定义输出路径
output_json = "output/my_result.json"
output_md = "output/my_result.md"
summary_path = "output/MY_SUMMARY.md"
```

---

## ⚠️ 常见问题

### Q1: API Key错误

**问题**: `AuthenticationError: Incorrect API key provided`

**解决**: 检查 `.env` 文件中 `DASHSCOPE_API_KEY` 是否正确，确保已充值。

---

### Q2: 数据文件找不到

**问题**: `FileNotFoundError: 搜索词-2025-6月.xlsx`

**解决**: 确保数据文件在 `data/` 目录下，且文件名完全匹配。

---

### Q3: Embedding模型404错误

**问题**: `Error code: 404 - The model 'text-embedding-3-small' does not exist`

**解决**: 这是正常的，系统会自动降级到文本相似度算法，不影响功能。

---

## 🔮 版本历史

### v4.0 (当前版本)
- ✅ 6月vs12月强制对比分析
- ✅ 自然笔记数范围值智能解析
- ✅ 市场出价数据质量自动检测
- ✅ 反常识洞察框架（5维分析）
- ✅ 战术建议多样化（8类策略）
- ✅ 竞品对比维度强化

### v3.0
- 三智能体协同架构
- 证据验证系统
- 新鲜度检查机制

---

## 📜 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题或建议，请提交 GitHub Issue。

---

**Made with ❤️ for Data-Driven Marketing**
