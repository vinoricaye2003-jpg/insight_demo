# XHS-MarketAI 洞察闭环系统 - 完整架构说明

## 🎯 系统定位

**自进化数据挖掘机 (Self-Evolving Data Miner)**

利用大模型的逻辑推理能力来寻找"未知的未知"，同时利用确定性的代码逻辑和辅助模型来充当"刹车"和"质检员"。

---

## 🏗️ 系统架构

### 整体流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    初始战略目标 + CSV 数据                    │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  第一部分：迭代式洞察生成链 (Generation Loop)                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [The Analyst] 洞察生成专家                                   │
│  ├─ 输出 1: Insight（结论）                                   │
│  ├─ 输出 2: Evidence（数据溯源标记 [Data Trace]）             │
│  └─ 输出 3: Next Prompt（自主推演下一步）                     │
│                                                               │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  第二部分：校验与逻辑控制系统 (Validation System)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [The Auditor] 事实审计员                                     │
│  ├─ 确定性校验: 提取 [Data Trace]，在 CSV 中硬核验证          │
│  ├─ 逻辑审计: 检查推理是否过度（如基于1%增长得出重大结论）     │
│  └─ 纠错反馈: 发现幻觉 → 反馈给 Analyst → 重新分析            │
│                                                               │
│  [The Controller] 逻辑控制器                                  │
│  ├─ 新鲜度检查 (Novelty Checker):                            │
│  │  ├─ 向量语义分析: Embedding + 余弦相似度                   │
│  │  ├─ 阈值判定: 相似度 > 0.9 → 判定为重复                    │
│  │  └─ 连续监测: 连续 2 轮高相似度 → STOP                     │
│  └─ 信息密度监测: 新关键词出现率                              │
│                                                               │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
                   决策分支
                        ↓
         ┌──────────────┴──────────────┐
         ↓                              ↓
    CONTINUE                         STOP
  (进入下一轮)                  (输出完整结果)
```

---

## 📦 三大核心组件详解

### 1️⃣ 组件 A: The Analyst (洞察生成专家)

**职责**: "压榨"数据，自主推演挖掘方向

**输入**:
- Current Prompt: 当前分析指令
- Data Context: 完整数据集（前20行 + TOP10关键词）
- History: 历史洞察（避免重复）
- Error Feedback: 上一轮错误反馈（如有）

**核心逻辑**:
```python
def analyst_generate_insight(user_prompt, data_dict):
    # 1. 构建数据概览（不是样例，是真实数据）
    data_summary = _build_data_summary(data_dict)
    
    # 2. 如果有错误反馈，加入纠错指令
    if self.error_feedback:
        prompt += f"上一轮你引用的数字不存在，请重新审视数据..."
    
    # 3. 调用 LLM
    response = _call_llm(system_prompt, user_message)
    
    # 4. 解析 JSON 输出
    return {
        "insight": "发现的趋势或机会点",
        "evidence": [
            {"date": "6月", "keyword": "桃子水", 
             "search_index": 56516, "original_row_index": 25}
        ],
        "next_prompt": "下一步应该挖掘的具体方向..."
    }
```

**输出结构**:
```json
{
  "insight": "桃子水在6月搜索指数为56516，12月降至23456，下降58.5%...",
  "evidence": [
    {
      "date": "6月",
      "keyword": "桃子水",
      "search_index": 56516,
      "original_row_index": 25
    }
  ],
  "next_prompt": "深入分析：在12月淡季，搜索'婴儿湿疹'、'冬季护肤'等关键词..."
}
```

**关键特性**:
- ✅ 自动生成下一轮挖掘指令（Next Prompt）
- ✅ 所有结论必须有数据溯源（[Data Trace]）
- ✅ 接收错误反馈并自我修正

---

### 2️⃣ 组件 B: The Auditor (事实审计员)

**职责**: 防止幻觉，确保数据闭环

#### A. 确定性校验 (Deterministic Check)

**逻辑**:
```python
def auditor_verify_evidence(evidence, data_dict):
    for ev in evidence:
        keyword = ev['keyword']
        claimed_value = ev['search_index']
        
        # 1. 在原始 DataFrame 中查找关键词
        matches = df[df['关键词'].str.contains(keyword)]
        
        # 2. 比对数值（容忍1%误差）
        actual_value = matches['搜索指数'].values[0]
        if abs(actual_value - claimed_value) / actual_value > 0.01:
            return False, "数值不匹配", error_feedback
        
    return True, "验证通过", ""
```

**验证步骤**:
1. 提取 Analyst 输出的 Evidence
2. 在 CSV 中精确查找该关键词
3. 对比数值是否一致（1%误差容忍）
4. 如果不一致 → 生成错误反馈

#### B. 逻辑审计员 (Logic Auditor)

**检查项**:
- ❌ 基于微小变化做出重大结论
  - 例: 数值<1000，但用了"显著"、"大幅"等词
- ❌ 证据不足的绝对性结论
  - 例: 仅2条证据，但得出"一定"、"必然"结论

**示例**:
```python
def _audit_logic_reasoning(insight, evidence):
    for ev in evidence:
        if ev['search_index'] < 1000:
            if any(word in insight for word in ['显著', '大幅', '明显']):
                return "⚠️ 逻辑警告: 基于较小数值得出了强烈结论"
    
    if len(evidence) <= 2:
        if any(word in insight for word in ['一定', '必然', '绝对']):
            return "⚠️ 逻辑警告: 证据不足以支撑绝对性结论"
    
    return "✅ 逻辑审计通过"
```

#### C. 纠错反馈机制

**流程**:
```
Auditor 发现错误
    ↓
生成详细错误反馈
    ↓
保存到 self.error_feedback
    ↓
下一轮 Analyst 接收反馈
    ↓
Analyst 重新分析数据
    ↓
输出修正后的结论
```

**错误反馈示例**:
```
⚠️ 【纠错反馈】上一轮分析存在问题：
证据 1: ❌ 验证失败
  - 关键词: '桃子水'
  - 声称数值: 12345
  - 原因: 在原始数据中未找到匹配的数值

请检查：
1. 关键词是否在原始数据中存在？
2. 引用的数值是否准确？
3. 是否混淆了不同数据源（6月 vs 12月）？
```

---

### 3️⃣ 组件 C: The Controller (逻辑控制器)

**职责**: 判定何时停止挖掘

#### A. 新鲜度检查 (Novelty Checker)

**方法 1: 向量语义分析** ⭐ 主要方法

```python
def controller_decide_next(insight, audit_passed):
    # 1. 将当前洞察转为向量
    current_embedding = _get_embedding(insight)
    
    # 2. 与历史洞察计算余弦相似度
    similarities = [
        _cosine_similarity(current_embedding, hist_emb)
        for hist_emb in self.insight_embeddings
    ]
    max_similarity = max(similarities)
    
    # 3. 判定逻辑
    if max_similarity > 0.9:
        self.high_similarity_count += 1
        
        # 连续 2 轮高相似度 → 停止
        if self.high_similarity_count >= 2:
            return "STOP", "连续2轮高相似度，数据价值已被榨干"
    
    return "CONTINUE", "存在新发现，继续挖掘"
```

**技术细节**:
- 使用 OpenAI `text-embedding-3-small` 模型
- 余弦相似度阈值: 0.9
- 连续监测: 2轮
- 备用方案: 如 Embedding 失败，使用 `difflib.SequenceMatcher`

**方法 2: 新关键词密度监测**

```python
# 提取当前洞察的关键词
current_keywords = _extract_keywords(insight)

# 计算新关键词比例
new_keywords = current_keywords - self.keywords_pool
new_keyword_ratio = len(new_keywords) / len(current_keywords)

# 判定: 即使相似度高，如果有大量新关键词，可以继续
if max_similarity > 0.9 and new_keyword_ratio < 0.2:
    return "STOP", "相似度高且新信息密度低"
```

#### B. 停止条件汇总

| 条件 | 说明 |
|------|------|
| 审计未通过 | Auditor 发现数据不一致或幻觉 |
| 达到最大迭代次数 | 默认 5 轮 |
| 向量相似度 > 0.9 | 与历史洞察高度重复 |
| 连续 2 轮高相似度 | 持续重复，无新发现 |
| 新关键词率 < 20% | 信息密度低 |

---

## 🔄 完整工作流程

### 单轮迭代流程

```python
def run_single_iteration(user_prompt, data_dict):
    # 1. Analyst: 生成洞察
    analyst_result = analyst_generate_insight(user_prompt, data_dict)
    
    # 2. Auditor: 验证证据 + 逻辑审计
    audit_passed, audit_log, error_feedback = auditor_verify_evidence(
        analyst_result['evidence'],
        data_dict,
        analyst_result['insight']
    )
    
    # 3. 如果审计未通过，保存错误反馈
    if not audit_passed:
        self.error_feedback = error_feedback
    
    # 4. Controller: 新鲜度检查
    decision, reason = controller_decide_next(
        analyst_result['insight'],
        audit_passed
    )
    
    # 5. 更新 Context Buffer
    if audit_passed:
        self.insight_history.append(analyst_result['insight'])
        self.insight_embeddings.append(embedding)
        self.keywords_pool.update(keywords)
    
    return output_json
```

### 完整循环流程

```python
def run_full_cycle(initial_prompt, data_dict):
    current_prompt = initial_prompt
    
    while iteration_count < max_iterations:
        # 运行单轮
        result = run_single_iteration(current_prompt, data_dict)
        
        # 判定是否停止
        if result['controller_decision']['action'] == "STOP":
            break
        
        # 使用 Analyst 生成的 next_prompt 进入下一轮
        current_prompt = result['system_generated_next_prompt']
    
    return all_results
```

---

## 💾 Context Buffer (状态存储)

系统维护以下状态：

```python
self.insight_history = []        # 文本历史
self.insight_embeddings = []     # 向量历史（用于相似度计算）
self.evidence_pool = []          # 所有证据池
self.keywords_pool = set()       # 已发现的关键词集合
self.high_similarity_count = 0   # 连续高相似度计数
self.error_feedback = None       # 错误反馈信息
```

---

## 🎯 关键创新点

### 1. 自主推演能力
- Analyst 不仅分析当前数据，还生成 `next_prompt`
- 系统无需人工干预，自动进行多轮深度挖掘

### 2. 纠错反馈机制
- 传统系统：发现错误 → 停止
- 本系统：发现错误 → 反馈 → Analyst 自我修正 → 继续

### 3. 双重新鲜度检测
- 语义层面：向量余弦相似度
- 信息层面：新关键词密度
- 双保险确保不会过早停止或无限循环

### 4. 逻辑审计
- 不仅验证数据真实性
- 还检查推理合理性
- 防止"小数据大结论"

---

## 📊 输出格式

### 单轮输出

```json
{
  "status": "Success",
  "iteration": 1,
  "audit_report": {
    "is_passed": true,
    "log": "审计详情..."
  },
  "analyst_result": {
    "insight": "洞察结论...",
    "evidence_trace": [
      {"date": "6月", "keyword": "...", "search_index": 12345, "original_row_index": 10}
    ]
  },
  "system_generated_next_prompt": "下一轮挖掘指令...",
  "controller_decision": {
    "action": "CONTINUE",
    "reason": "存在新发现"
  }
}
```

### 完整循环输出

```json
{
  "total_iterations": 3,
  "total_insights": 3,
  "total_keywords": 45,
  "all_rounds": [
    { /* 第1轮结果 */ },
    { /* 第2轮结果 */ },
    { /* 第3轮结果 */ }
  ],
  "final_insight_summary": [
    "第1轮洞察...",
    "第2轮洞察...",
    "第3轮洞察..."
  ]
}
```

---

## 🚀 运行示例

```bash
# 设置 API Key
$env:DEEPSEEK_API_KEY="sk-your-key"

# 运行系统
python market_insight_system.py

# 选择模式
# 1. 单轮测试（只运行第一轮）
# 2. 完整循环（自动迭代直到停止）
```

---

## 📈 系统优势

| 传统分析 | XHS-MarketAI |
|----------|--------------|
| 一次性分析 | 迭代式深度挖掘 |
| 人工指定下一步 | AI 自主推演 |
| 发现错误即停止 | 纠错反馈自我修正 |
| 简单文本相似度 | 向量语义 + 关键词密度 |
| 无逻辑审计 | 双重审计（数据+逻辑） |
| 人工判断停止 | 自动判定数据价值耗尽 |

---

**版本**: 2.0.0 (完整架构版)  
**更新日期**: 2025-12-29  
**系统名称**: XHS-MarketAI 洞察闭环系统 - 自进化数据挖掘机
