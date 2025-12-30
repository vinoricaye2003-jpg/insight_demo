# 📋 输出报告格式说明

系统现在会**同时生成两种格式**的报告：

## 1. JSON 格式（机器可读）

### 单轮测试
- **文件名**: `insight_result_round1.json`
- **用途**: API 集成、数据分析、后续处理

### 完整循环
- **文件名**: `insight_full_cycle.json`
- **用途**: 完整数据记录、批量处理

**JSON 结构**:
```json
{
  "status": "Success",
  "iteration": 1,
  "audit_report": {
    "is_passed": true,
    "log": "详细审计日志..."
  },
  "analyst_result": {
    "insight": "核心洞察...",
    "evidence_trace": [
      {
        "date": "6月",
        "keyword": "桃子水",
        "search_index": 56516,
        "original_row_index": 0
      }
    ]
  },
  "system_generated_next_prompt": "下一轮分析方向...",
  "controller_decision": {
    "action": "CONTINUE",
    "reason": "审计通过且存在新发现"
  }
}
```

---

## 2. Markdown 格式（人类友好）

### 单轮测试
- **文件名**: `insight_result_round1.md`
- **用途**: 阅读、展示、分享

### 完整循环
- **文件名**: `insight_full_cycle.md`
- **用途**: 完整报告、汇报材料

**Markdown 包含内容**:

### 单轮报告结构
```markdown
# 🔍 XHS-MarketAI 分析报告 - 第 X 轮

## 💡 核心洞察
[文字描述的洞察结论]

## 📊 数据证据
[表格展示证据数据]
| 数据源 | 关键词 | 搜索指数 | 数据行号 |
|--------|--------|----------|----------|
| 6月    | 桃子水 | 56,516   | 25       |

## 🔍 数据审计
[审计结果和详细日志]

## 🎯 下一步挖掘方向
[系统生成的下一轮分析建议]

## 🤖 系统决策
[决策和原因]
```

### 完整循环报告结构
```markdown
# 📈 XHS-MarketAI 完整分析报告

## 📊 执行摘要
- 总轮数
- 有效洞察数
- 证据总数
- 发现关键词数

## 🎯 分析目标
[初始分析需求]

## 💡 核心发现汇总
### 第 1 轮洞察
[洞察内容]

### 第 2 轮洞察
[洞察内容]

## 📋 详细分析过程
### 🔄 第 1 轮分析
[详细内容：洞察 + 证据表格 + 审计 + 决策]

### 🔄 第 2 轮分析
[详细内容]

## 🛑 系统停止原因
[为什么停止挖掘]

## 🔑 关键词发现
[所有发现的关键词列表]
```

---

## 3. 输出文件对比

| 格式 | 优势 | 适用场景 |
|------|------|----------|
| **JSON** | 结构化、可编程处理 | API 集成、数据分析、自动化流程 |
| **Markdown** | 易读、美观、可分享 | 阅读报告、团队分享、汇报展示 |

---

## 4. 查看方式

### JSON 文件
```powershell
# 查看内容
cat insight_result_round1.json

# 或用 VS Code 打开
code insight_result_round1.json
```

### Markdown 文件
```powershell
# 在 VS Code 中打开并预览
code insight_result_round1.md

# 按 Ctrl+Shift+V 切换到预览模式
```

---

## 5. 使用建议

### 对于开发者
- 使用 **JSON** 进行数据处理和分析
- 编写脚本读取 JSON 提取关键信息
- 集成到其他系统或工作流

### 对于业务人员
- 直接阅读 **Markdown** 报告
- 在支持 Markdown 的平台（如 GitHub、Notion）查看
- 复制粘贴到文档或演示文稿

### 对于团队协作
- 开发：基于 JSON 构建仪表板
- 产品：阅读 Markdown 理解洞察
- 管理：使用 Markdown 做决策汇报

---

## 6. 示例输出

### 测试模式
```
test_result.json      # 机器可读
test_result.md        # 人类友好
```

### 单轮模式
```
insight_result_round1.json    # 机器可读
insight_result_round1.md      # 人类友好
```

### 完整循环模式
```
insight_full_cycle.json    # 完整数据（所有轮次）
insight_full_cycle.md      # 完整报告（格式化展示）
```

---

## 7. 报告特色

### Markdown 报告亮点
- ✅ **表格展示证据**：清晰的数据表格，包含千分位分隔符
- ✅ **Emoji 图标**：视觉友好的章节标识
- ✅ **代码块**：审计日志使用代码块展示
- ✅ **分隔线**：清晰的章节分隔
- ✅ **时间戳**：记录生成时间
- ✅ **完整追溯**：每轮分析的完整记录

### JSON 报告亮点
- ✅ **结构化数据**：易于程序解析
- ✅ **完整信息**：包含所有原始数据
- ✅ **嵌套结构**：保留层级关系
- ✅ **统一格式**：便于批量处理

---

**现在系统会自动生成两种格式，满足不同需求！** 🎉
