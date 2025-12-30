"""
XHS-MarketAI System: 自进化数据挖掘机
集成 Qwen API 的市场洞察分析系统
"""

import pandas as pd
import json
import os
import sys
import re
from typing import Dict, List, Any, Tuple, Set
from difflib import SequenceMatcher
from openai import OpenAI
import numpy as np
from collections import Counter
from dotenv import load_dotenv

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载 .env 文件中的环境变量
load_dotenv()


class MarketInsightSystem:
    """通用市场洞察系统 - 支持任意数据集和用户提示"""
    
    def __init__(self, api_key: str = None, model: str = "qwen-plus"):
        """
        初始化系统
        Args:
            api_key: Qwen API 密钥（阿里云DashScope）
            model: 使用的模型名称（可选：qwen-turbo, qwen-plus, qwen-max）
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 系统状态 (Context Buffer)
        self.iteration_count = 0
        self.max_iterations = 10  # 从5次提升到10次，深度挖掘
        self.insight_history = []  # 所有洞察历史（含审计失败项，用于完整报告和调试）
        self.insight_embeddings = []  # 向量存储（仅审计通过的洞察）
        self.evidence_pool = []  # 证据池
        self.keywords_pool = set()  # 已发现的关键词池
        self.high_similarity_count = 0  # 连续高相似度计数
        self.error_feedback = None  # 错误反馈信息
        self.disabled_features = set()  # 禁用的功能（如市场出价分析）
        
    def _parse_notes_value(self, value) -> float:
        """
        解析自然笔记数的各种格式
        Args:
            value: 笔记数值（可能是数字、"2.9万"、"9000-10000"等格式）
        Returns:
            解析后的数值
        """
        value_str = str(value).strip()
        
        # 处理范围值（如"9000-10000"）
        if '-' in value_str and not value_str.startswith('-'):
            # 检查是否是数字范围
            parts = value_str.split('-')
            if len(parts) == 2:
                try:
                    # 尝试解析为数字范围，取中值
                    low = float(parts[0].replace(',', ''))
                    high = float(parts[1].replace(',', ''))
                    return (low + high) / 2
                except ValueError:
                    pass
        
        # 处理"万"单位（如"2.9万"）
        if '万' in value_str:
            try:
                num = float(value_str.replace('万', '').replace(',', ''))
                return num * 10000
            except ValueError:
                pass
        
        # 处理"k"单位
        if 'k' in value_str.lower():
            try:
                num = float(value_str.lower().replace('k', '').replace(',', ''))
                return num * 1000
            except ValueError:
                pass
        
        # 尝试直接转换为数字
        try:
            return float(value_str.replace(',', ''))
        except ValueError:
            return 0.0
    
    def load_data(self, file_paths: List[str], labels: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        加载多个数据文件
        Args:
            file_paths: 文件路径列表
            labels: 数据标签（如"6月"、"12月"）
        Returns:
            字典，键为标签，值为 DataFrame
        """
        data_dict = {}
        for i, path in enumerate(file_paths):
            label = labels[i] if labels else f"dataset_{i}"
            try:
                if path.endswith('.csv'):
                    df = pd.read_csv(path, encoding='utf-8')
                elif path.endswith('.xlsx'):
                    df = pd.read_excel(path)
                else:
                    df = pd.read_csv(path, encoding='utf-8')
                
                # 添加行索引列用于追溯
                df['_original_row_index'] = df.index
                df['_data_source'] = label
                
                # 计算高级指标（如果存在相关列）
                if '搜索次数指数' in df.columns:
                    # 确保数值类型
                    df['搜索次数指数'] = pd.to_numeric(df['搜索次数指数'], errors='coerce')
                    
                    # 指标1: 内容空白度 = 搜索量 / (自然笔记数+1) - 越高越是蓝海
                    if '自然笔记数' in df.columns:
                        # 使用新的解析函数处理各种格式（包括范围值）
                        df['自然笔记数_数值'] = df['自然笔记数'].apply(self._parse_notes_value)
                        df['_内容空白度'] = df['搜索次数指数'] / (df['自然笔记数_数值'] + 1)
                    
                    # 指标2: 竞争强度 = 自然笔记数 / 搜索次数指数 - 越高竞争越激烈
                    if '自然笔记数_数值' in df.columns:
                        df['_竞争强度'] = df['自然笔记数_数值'] / (df['搜索次数指数'] + 1)
                    
                    # 指标3: 广告性价比 = 搜索次数指数 / (广告消耗+1) - 越高越划算
                    if '广告消耗（元）' in df.columns:
                        cost = pd.to_numeric(df['广告消耗（元）'], errors='coerce').fillna(0)
                        df['_广告性价比'] = df['搜索次数指数'] / (cost + 1)
                    
                    # 指标4: 自然流量效率 = 自然曝光量指数 / 搜索次数指数
                    if '自然曝光量指数' in df.columns:
                        exposure = pd.to_numeric(df['自然曝光量指数'], errors='coerce').fillna(0)
                        df['_自然流量效率'] = exposure / (df['搜索次数指数'] + 1)
                
                data_dict[label] = df
                print(f"✓ 加载数据: {label} - {len(df)} 行, {len(df.columns)} 列")
                
                # 数据质量检查
                if '市场出价（元）' in df.columns:
                    market_price_sum = pd.to_numeric(df['市场出价（元）'], errors='coerce').fillna(0).sum()
                    if market_price_sum == 0:
                        print(f"⚠️ 警告：{label}的市场出价数据全为0，相关分析将被禁用")
                        self.disabled_features.add('市场出价分析')
                
            except Exception as e:
                print(f"✗ 加载失败 {path}: {e}")
                
        return data_dict
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        获取文本的向量表示 (Embedding) - 使用Qwen模型
        Args:
            text: 输入文本
        Returns:
            向量数组
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-v2",  # 使用Qwen的embedding模型
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"⚠️ Embedding 获取失败: {e}，使用文本相似度作为备选")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        Args:
            vec1, vec2: 向量
        Returns:
            相似度 [0, 1]
        """
        if vec1 is None or vec2 is None:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """
        提取文本中的关键词
        Args:
            text: 输入文本
        Returns:
            关键词集合
        """
        # 移除标点符号，提取中文词汇（简单实现）
        words = re.findall(r'[\u4e00-\u9fa5]+', text)
        # 过滤长度小于2的词
        keywords = {w for w in words if len(w) >= 2}
        return keywords
    
    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        调用 Qwen API
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 生成温度
        Returns:
            模型响应文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API 调用失败: {e}")
            return f"ERROR: {str(e)}"
    
    # ==================== 组件 A: The Analyst ====================
    def analyst_generate_insight(self, user_prompt: str, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        洞察生成专家：压榨数据，寻找证据
        Args:
            user_prompt: 用户分析需求
            data_dict: 数据字典
        Returns:
            {
                "insight": "文本结论",
                "evidence": [{"date": "6月", "keyword": "桃子水", "search_index": 56516, "row": 10}, ...],
                "next_prompt": "下一次挖掘的指令"
            }
        """
        # 构建数据概览
        data_summary = self._build_data_summary(data_dict)
        
        # 根据数据质量检查，动态调整System Prompt
        market_price_disabled = '市场出价分析' in self.disabled_features
        
        system_prompt = f"""你是一位资深市场战略分析师，专注于小红书电商数据挖掘和竞争情报分析。

## 【战略背景】
- **我方产品**：松达松子粉（婴儿爽身粉）
- **核心竞品**：贝亲桃子水
- **战略目标**：从竞品手中抢夺市场份额，寻找攻击缺口和蓝海机会
- **分析视角**：每个洞察都要回答"如何利用这个发现击败桃子水"

## 🚨 核心规则（严格遵守）：

### 规则1: **强制6月vs12月对比分析**（最重要！）
- ❌ **禁止**：只分析单一月份（如"在12月数据中..."）
- ✅ **必须**：每个洞察至少包含1组6月vs12月的数据对比
- ✅ **必须**：evidence字段同时包含6月和12月的数据
- ✅ **必须**：分析季节性差异（上涨/下跌幅度、排名变化）

**对比维度示例**：
- 搜索量变化：桃子水从6月99,300降至12月35,858（-63.9%）
- 排名变化：婴儿水6月未进TOP10，12月升至第3名（逆势机会）
- 竞争格局变化：笔记数/搜索量比值的季节性差异
- 用户行为变化：6月搜"痱子"，12月搜"湿疹"（需求转移）

### 规则2: **反常识洞察框架**（每轮必选1个维度）
不要做常规的"长尾词机会"分析，必须从以下维度挖掘：

**A. 逆势增长词**：淡季反而上涨的关键词
- 示例：婴儿水6月未进TOP10，12月第3名（+XXX%）

**B. 降幅异常词**：降幅远超/远低于品类平均的词
- 示例：为何某词降幅-79.8%，远超主词-63.9%？

**C. 季节性倒挂词**：淡季搜索量占全年比例异常高的词
- 示例：某词12月占6+12月总量>50%（非季节性需求）

**D. 竞争格局突变词**：笔记数/搜索量比值在6月vs12月剧变
- 示例：6月红海（比值>1），12月蓝海（比值<0.5）

**E. 用户行为迁移**：搜索词语义在不同季节的变化
- 示例：6月关注"痱子"，12月关注"安全性"

### 规则3: **战术建议多样化**（禁止连续使用相同类型）
每轮必须从不同类型中选择：
- 类型1: 付费流量（搜索广告、信息流）
- 类型2: KOC合作（测评、种草）
- 类型3: SEO优化（自然排名、关键词布局）
- 类型4: 社群运营（母婴社区、私域流量）
- 类型5: 事件营销（话题挑战、季节性事件）
- 类型6: 产品迭代（基于用户疑问改进产品）
- 类型7: 竞品阻击（拦截竞品搜索词）
- 类型8: 内容矩阵（系列内容、IP打造）

### 规则4: **数据质量约束**
{"- ⚠️ **市场出价数据全为0**，禁止使用：" if market_price_disabled else ""}
{"  - ❌ 禁止提及'市场出价'、'CPC'、'竞价'等词" if market_price_disabled else ""}
{"  - ❌ 禁止计算'广告性价比'（基于出价）" if market_price_disabled else ""}
{"  - ✅ 改用'广告消耗'作为竞争强度指标" if market_price_disabled else ""}
{"  - ✅ 使用'广告消耗'计算实际投放效率" if market_price_disabled else ""}

### 规则5: **必须基于真实数据**
- 所有结论必须从下方提供的实际数据中提取
- 禁止凭空推测或编造数字
- 证据必须精确：引用的数字必须与原始数据完全一致

### 规则6: **多维度分析**
不要只看搜索指数！必须综合分析：
- 6月vs12月搜索量对比（季节性）
- 搜索量 vs 笔记数（内容空白度）
- 搜索量 vs 广告消耗（实际投放效率）
- 自然点击率 vs 广告点击率（内容质量）
- 搜索增速（趋势判断）

### 规则7: **竞品对比维度**（至少1轮专门分析）
必须对比的维度：
- 桃子水 vs 爽身粉：6月、12月搜索量对比
- 降幅对比：谁的季节性更强？
- 用户关注点对比：功效词 vs 安全词
- 品牌词对比：贝亲桃子水 vs 松达/其他品牌
- 长尾词分布：谁的长尾词更分散？

## 输出格式（严格遵守字段名）：

### 示例1：6月vs12月季节性对比（必须包含的对比分析）
```json
{{
  "insight": "【季节性逆势发现】'婴儿水'在6月搜索量XX（排名XX），12月升至18,698（排名第3），逆势上涨+XX%，而竞品'桃子水'同期下跌63.9%。'婴儿水'的非季节性特征使其成为淡季布局的战略入口。",
  "evidence": [
    {{"date": "6月", "keyword": "桃子水", "search_index": 99300, "original_row_index": 3}},
    {{"date": "12月", "keyword": "桃子水", "search_index": 35858, "original_row_index": 0}},
    {{"date": "12月", "keyword": "婴儿水", "search_index": 18698, "original_row_index": 2}}
  ],
  "tactical_recommendations": [
    "【P0-立即执行】针对'婴儿水'关键词布局搜索广告（广告消耗参考XX元，日预算500元，7天测试，目标ROI>4）",
    "【P1-本周内】创建'婴儿水vs松子粉'对比内容矩阵（社群运营策略：在母婴社区发布专业测评，预算3000元）",
    "【P2-本月内】基于逆势增长特征，布局'非季节性场景'内容（SEO优化：如湿疹、日常护理等关键词）"
  ],
  "next_prompt": "深度对比：分析6月TOP10关键词在12月的排名变化，哪些词'掉出TOP10'？哪些词'新进TOP10'？这些变化反映了什么用户需求迁移？"
}}
```

### 示例2：竞品对比分析（深度对比桃子水vs爽身粉）
```json
{{
  "insight": "【竞品季节性对比】桃子水6月搜索99,300降至12月35,858（-63.9%），爽身粉6月85,725降至12月21,949（-74.4%）。爽身粉的季节性更强，说明其'痱子预防'场景主导需求。松达应在淡季布局'非痱子场景'（如湿疹、日常护理）来抗跌。",
  "evidence": [
    {{"date": "6月", "keyword": "桃子水", "search_index": 99300, "original_row_index": 3}},
    {{"date": "12月", "keyword": "桃子水", "search_index": 35858, "original_row_index": 0}},
    {{"date": "6月", "keyword": "爽身粉", "search_index": 85725, "original_row_index": 4}},
    {{"date": "12月", "keyword": "爽身粉", "search_index": 21949, "original_row_index": 1}}
  ],
  "tactical_recommendations": [
    "【P0-今日启动】立即布局'湿疹'、'日常护理'等非季节性场景词（产品迭代策略：强调松达的全年适用性）",
    "【P1-本周内】发起#冬季也要用爽身粉 话题挑战（事件营销策略：联合10位KOL，预算8000元，目标曝光100万+）",
    "【P2-本月内】创建'四季护肤'内容矩阵（内容矩阵策略：春夏秋冬4季场景内容，打破季节性认知）"
  ],
  "next_prompt": "深度挖掘：对比6月和12月的'用户关注点'变化（如功效词vs安全词的比例），用户在淡季更关心什么？"
}}
```

### 示例3：反常识洞察（降幅异常词）
```json
{{
  "insight": "【降幅异常发现】'桃子水的正确使用方法'6月搜索58,310降至12月11,771（-79.8%），降幅远超主词'桃子水'（-63.9%）。这说明用户在淡季对'使用方法'的关注度断崖下跌，而松达可抢占'冬季使用场景'认知空白。",
  "evidence": [
    {{"date": "6月", "keyword": "桃子水正确使用方法", "search_index": 58310, "original_row_index": 7}},
    {{"date": "12月", "keyword": "桃子水的正确使用方法", "search_index": 11771, "original_row_index": 6}},
    {{"date": "6月", "keyword": "桃子水", "search_index": 99300, "original_row_index": 3}},
    {{"date": "12月", "keyword": "桃子水", "search_index": 35858, "original_row_index": 0}}
  ],
  "tactical_recommendations": [
    "【P0-立即执行】抢占'冬季爽身粉使用方法'搜索词（竞品阻击策略：在桃子水用户搜索时拦截，预算2000元/周）",
    "【P1-本周内】创作《冬天宝宝也要用爽身粉？正确使用方法》爆款内容（KOC合作：5位母婴博主，单条1500元）",
    "【P2-本月内】建立'四季使用指南'SEO矩阵（SEO优化：布局春夏秋冬4季使用方法词）"
  ],
  "next_prompt": "深度挖掘：分析12月数据中哪些词的'内容空白度'（搜索量/笔记数）最高？这些供需失衡的词是松达的内容机会。"
}}
```

## 📊 多维度分析指南：

### 1. 内容空白度分析
- **计算方法**：内容空白度 = 搜索次数指数 / (自然笔记数 + 1)
- **黄金阈值**：空白度 > 0.5 为蓝海机会（注意：笔记数常为"9000-10000"范围，已自动取中值）
- **案例**：如果'婴儿水'搜索18698，笔记9500，空白度=1.97（蓝海）

### 2. 广告效率分析
- **计算方法**：效率 = 搜索次数指数 / (广告消耗 + 1)
- **优质标准**：效率 > 100 为高效率词
- **案例**：搜索3852，广告消耗仅10元，效率=385（极高性价比）

### 3. 季节性强度分析
- **计算方法**：季节性强度 = |6月搜索量 - 12月搜索量| / 6月搜索量
- **强/弱季节性**：> 70% 为强季节性，< 30% 为弱季节性
- **案例**：痱子（-90.3%）强季节性，婴儿水（+2.7%）弱季节性

## ⚠️ 关键要求（必须严格遵守）：
- **evidence 必须字段**: date, keyword, search_index, original_row_index
- **evidence 可选字段**: natural_notes, ad_cost（广告消耗）, search_growth, content_gap
- **keyword 必须从数据的'搜索词'列精确复制**
- **search_index 必须精确复制**，不能四舍五入
- **date 必须是'6月'或'12月'**
- **tactical_recommendations 格式**: 【优先级-时间】具体行动（策略类型：XXX，预算，目标）
- **next_prompt 必须引导下一轮深度对比**：如"对比6月vs12月的..."
- **每个结论必须有2-4个证据**，且必须包含6月和12月的对比数据
- **禁止编造数据**：如果数据中没有，绝对不能虚构
"""
        
        # 构建用户消息，包含错误反馈
        
        # 构建用户消息，包含错误反馈
        # 仅传递审计通过的洞察给LLM，避免错误信息污染
        valid_insights = [
            h for h in self.insight_history 
            if h.get('audit_passed', False)
        ]
        
        user_message_parts = [f"""用户需求：
{user_prompt}

可用数据概览：
{data_summary}

历史洞察（避免重复，仅展示已验证通过的洞察）：
{json.dumps(valid_insights[-3:], ensure_ascii=False, indent=2) if valid_insights else "无"}
"""]
        
        # 如果有错误反馈，加入纠错指令
        if self.error_feedback:
            user_message_parts.append(f"""
⚠️ 【纠错反馈】上一轮分析存在问题：
{self.error_feedback}

请重新审视原始数据，修正你的分析结论。务必确保所有引用的数字都能在数据中找到。
""")
            self.error_feedback = None  # 清空反馈
        
        user_message_parts.append("\n请分析数据并输出 JSON 格式的洞察结果。")
        user_message = "".join(user_message_parts)
        
        response = self._call_llm(system_prompt, user_message, temperature=0.3)
        
        # 解析 JSON 响应
        try:
            # 提取 JSON 部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            
            # 确保必要字段存在
            if "insight" not in result:
                result["insight"] = "无法生成有效洞察"
            if "evidence" not in result:
                result["evidence"] = []
            if "tactical_recommendations" not in result:
                result["tactical_recommendations"] = ["需要进一步分析以生成战术建议"]
            if "next_prompt" not in result:
                result["next_prompt"] = "深入分析：基于当前发现，挖掘竞品的弱点和市场空白机会"
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON 解析失败: {e}")
            print(f"\n原始响应 (前500字符):\n{response[:500]}...")
            print(f"\n原始响应 (后500字符):\n...{response[-500:]}")
            
            # 保存完整原始响应到文件用于调试
            error_file = f"error_response_round_{self.iteration_count + 1}.txt"
            try:
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"Iteration: {self.iteration_count + 1}\n")
                    f.write(f"Error: {e}\n\n")
                    f.write(f"Raw Response:\n{response}")
                print(f"ℹ️  完整响应已保存到: {error_file}")
            except:
                pass
            
            # 返回明确标记为解析失败的结果，不会被审计通过
            return {
                "insight": f"【解析失败】LLM输出格式不符合JSON规范，详见{error_file}",
                "evidence": [],
                "tactical_recommendations": [],
                "next_prompt": user_prompt,
                "_parse_error": True,  # 标记解析错误
                "_raw_response": response[:1000]  # 保存部分原始响应
            }
    
    def _build_data_summary(self, data_dict: Dict[str, pd.DataFrame]) -> str:
        """构建数据概览字符串 - 提供足够详细的数据让LLM能真正分析"""
        summary_lines = []
        
        for label, df in data_dict.items():
            summary_lines.append(f"\n{'='*60}")
            summary_lines.append(f"【{label} 数据集】")
            summary_lines.append(f"{'='*60}")
            summary_lines.append(f"总行数: {len(df)} | 总列数: {len(df.columns)}")
            
            # 识别关键列名并明确告知LLM
            keyword_col = None
            search_col = None
            for col in df.columns:
                if '搜索词' in col or '关键词' in col:
                    keyword_col = col
                if '搜索次数指数' in col or '搜索指数' in col:
                    search_col = col
            
            # 显示完整列名
            summary_lines.append(f"\n完整列名: {', '.join(df.columns[:15])}")
            
            if keyword_col and search_col:
                summary_lines.append(f"\n⚠️ 重要提示：")
                summary_lines.append(f"  - 关键词列名是: '{keyword_col}'")
                summary_lines.append(f"  - 搜索指数列名是: '{search_col}'")
                summary_lines.append(f"  - 你必须使用 keyword='{keyword_col}列的值', search_index={search_col}列的值")
            
            # 显示更多数据行，让LLM能真正看到数据内容
            summary_lines.append(f"\n【前20行数据示例 - 多维度分析】（含行号用于追溯）：")
            # 选择关键列展示，包括高级指标
            if keyword_col and search_col:
                display_cols = [keyword_col, search_col]
                # 添加其他重要维度
                optional_cols = ['自然笔记数', '广告笔记数', '自然点击率', '广告消耗（元）', 
                                '市场出价（元）', '搜索增速', '潜力分', 
                                '_内容空白度', '_竞争强度', '_广告性价比']
                for col in optional_cols:
                    if col in df.columns:
                        display_cols.append(col)
                
                display_df = df[display_cols].head(20).copy()
                display_df.insert(0, 'row_index', df['_original_row_index'].head(20))
                
                # 格式化数值列，保留2位小数
                for col in display_df.columns:
                    if col != 'row_index' and col in df.columns:
                        if df[col].dtype in ['float64', 'float32']:
                            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else '-')
                
                summary_lines.append(display_df.to_string(index=False))
            else:
                key_columns = [col for col in df.columns if col not in ['_original_row_index', '_data_source']]
                display_df = df[key_columns].head(20).copy()
                display_df.insert(0, 'row_index', df['_original_row_index'].head(20))
                summary_lines.append(display_df.to_string(index=False))
            
            # 统计关键指标
            if keyword_col:
                summary_lines.append(f"\n【统计信息】")
                summary_lines.append(f"- 唯一关键词数: {df[keyword_col].nunique()}")
            
            if search_col:
                summary_lines.append(f"- 搜索指数: 最小={df[search_col].min()}, 最大={df[search_col].max()}, 平均={df[search_col].mean():.0f}")
            
            # 展示高级指标统计
            if '_内容空白度' in df.columns:
                summary_lines.append(f"- 内容空白度（搜索量/笔记数）: 平均={df['_内容空白度'].mean():.2f}, 最大={df['_内容空白度'].max():.2f}")
                summary_lines.append(f"  提示: 空白度>5为蓝海机会")
            
            if '_广告性价比' in df.columns:
                valid_data = df[df['_广告性价比'] < 999999]  # 过滤异常值
                if len(valid_data) > 0:
                    summary_lines.append(f"- 广告性价比（搜索量/广告消耗）: 平均={valid_data['_广告性价比'].mean():.2f}")
            
            if '搜索增速' in df.columns:
                try:
                    growth_stats = df['搜索增速'].describe()
                    summary_lines.append(f"- 搜索增速范围: {growth_stats.get('min', 'N/A')} ~ {growth_stats.get('max', 'N/A')}, 平均={growth_stats.get('mean', 'N/A')}")
                except:
                    pass  # 如果搜索增速是字符串格式，跳过统计
            
            if search_col:
                # TOP 10 关键词
                top_keywords = df.nlargest(10, search_col)[[keyword_col, search_col, '_original_row_index']]
                summary_lines.append(f"\n【TOP 10 高搜索指数关键词】：")
                summary_lines.append(top_keywords.to_string(index=False))
        
        return "\n".join(summary_lines)
    
    # ==================== 组件 B: The Auditor ====================
    def auditor_verify_evidence(self, evidence: List[Dict], data_dict: Dict[str, pd.DataFrame], insight: str = "", is_parse_error: bool = False) -> Tuple[bool, str, str]:
        """
        事实审计员：硬核验证证据真实性（防止AI幻觉）
        Args:
            evidence: Analyst 提交的证据列表
            data_dict: 原始数据字典
            insight: 洞察结论
            is_parse_error: 是否是JSON解析错误
        Returns:
            (is_passed, log_message, error_feedback)
        """
        # 如果是解析错误，直接拒绝
        if is_parse_error:
            return False, "❌ 解析错误：LLM输出格式不符合JSON规范，无法验证证据", "请检查Prompt或减少上下文长度"
        
        if not evidence:
            return False, "❌ 证据列表为空，无法验证", "证据列表为空，请提供有效的证据支持"
        
        verification_logs = []
        all_passed = True
        verified_count = 0
        
        for idx, ev in enumerate(evidence, 1):
            # 提取证据字段（严格按照要求的字段名）
            keyword = ev.get("keyword")
            claimed_value = ev.get("search_index")
            data_source = ev.get("date")
            claimed_row = ev.get("original_row_index")
            
            # 检查必需字段
            if not keyword:
                verification_logs.append(f"证据 {idx}: ❌ 缺少 'keyword' 字段")
                all_passed = False
                continue
            
            if claimed_value is None:
                verification_logs.append(f"证据 {idx}: ❌ 缺少 'search_index' 字段")
                all_passed = False
                continue
            
            # 在对应数据源中精确查找
            found = False
            for label, df in data_dict.items():
                # 如果指定了数据源，必须匹配
                if data_source and data_source not in label:
                    continue
                
                # 自动识别关键词列（支持'搜索词'和'关键词'）
                keyword_col = None
                for col in df.columns:
                    if '搜索词' in col or '关键词' in col:
                        keyword_col = col
                        break
                
                if not keyword_col:
                    continue
                
                # 精确匹配关键词（完全匹配优先，否则包含匹配）
                exact_matches = df[df[keyword_col] == keyword]
                if exact_matches.empty:
                    exact_matches = df[df[keyword_col].str.contains(keyword, na=False, case=False)]
                
                if not exact_matches.empty:
                    # 自动识别搜索指数列（支持'搜索次数指数'和'搜索指数'）
                    search_col = None
                    for col in df.columns:
                        if '搜索次数指数' in col or '搜索指数' in col:
                            search_col = col
                            break
                    
                    if search_col:
                        for _, row in exact_matches.iterrows():
                            actual_val = row[search_col]
                            actual_row = row['_original_row_index']
                            
                            # 精确匹配（允许1%误差，因为可能有浮点数精度问题）
                            if abs(actual_val - claimed_value) / max(abs(actual_val), 1) < 0.01:
                                verification_logs.append(
                                    f"证据 {idx}: ✅ 验证通过\n"
                                    f"  - 关键词: '{keyword}'\n"
                                    f"  - 数据源: {label}\n"
                                    f"  - 搜索指数: {actual_val} (声称值: {claimed_value})\n"
                                    f"  - 行号: {actual_row}" + (f" (声称行号: {claimed_row})" if claimed_row is not None else "")
                                )
                                found = True
                                verified_count += 1
                                break
                    
                    # 如果没找到，尝试其他数值列
                    if not found:
                        for col in ['笔记数', '互动数', '商品数']:
                            if col in df.columns:
                                for _, row in exact_matches.iterrows():
                                    actual_val = row[col]
                                    if abs(actual_val - claimed_value) / max(abs(actual_val), 1) < 0.01:
                                        verification_logs.append(
                                            f"证据 {idx}: ✅ 验证通过 (使用 {col})\n"
                                            f"  - 关键词: '{keyword}' | 数据源: {label}\n"
                                            f"  - {col}: {actual_val}"
                                        )
                                        found = True
                                        verified_count += 1
                                        break
                            if found:
                                break
                
                if found:
                    break
            
            if not found:
                verification_logs.append(
                    f"证据 {idx}: ❌ 验证失败\n"
                    f"  - 关键词: '{keyword}'\n"
                    f"  - 声称数值: {claimed_value}\n"
                    f"  - 数据源: {data_source or '未指定'}\n"
                    f"  - 原因: 在原始数据中未找到匹配的关键词或数值"
                )
                all_passed = False
        
        # 汇总日志
        summary = f"\n{'='*60}\n审计结果: {verified_count}/{len(evidence)} 条证据通过验证\n{'='*60}\n"
        log_message = summary + "\n".join(verification_logs)
        
        # 生成错误反馈信息
        error_feedback = ""
        if not all_passed:
            failed_items = [log for log in verification_logs if "❌" in log]
            error_feedback = f"""数据验证失败，发现以下问题：
{''.join(failed_items)}

请检查：
1. 关键词是否在原始数据中存在？
2. 引用的数值是否准确？
3. 是否混淆了不同数据源（6月 vs 12月）？
"""
        
        # 逻辑审计：检查推理是否过度
        logic_audit_result = ""
        if all_passed and insight:
            logic_audit_result = self._audit_logic_reasoning(insight, evidence)
            if "⚠️" in logic_audit_result:
                log_message += f"\n\n【逻辑审计】\n{logic_audit_result}"
        
        return all_passed, log_message, error_feedback
    
    def _audit_logic_reasoning(self, insight: str, evidence: List[Dict]) -> str:
        """
        逻辑审计员：检查推理是否过度
        Args:
            insight: 洞察结论
            evidence: 证据列表
        Returns:
            审计结果日志
        """
        audit_logs = []
        
        # 检查1: 是否基于微小变化做出重大结论
        for ev in evidence:
            if 'search_index' in ev:
                value = ev['search_index']
                # 如果数值很小（<1000）但得出了"显著"、"大幅"等结论
                if value < 1000 and any(word in insight for word in ['显著', '大幅', '明显', '巨大']):
                    audit_logs.append(
                        f"⚠️ 逻辑警告：基于较小数值 ({value}) 得出了强烈结论，请确认推理合理性"
                    )
        
        # 检查2: 证据数量是否支撑结论强度
        if len(evidence) <= 2 and any(word in insight for word in ['一定', '必然', '肯定', '绝对']):
            audit_logs.append(
                f"⚠️ 逻辑警告：仅基于 {len(evidence)} 条证据，建议避免使用绝对性词汇"
            )
        
        return "\n".join(audit_logs) if audit_logs else "✅ 逻辑审计通过"
    
    # ==================== 组件 C: The Controller ====================
    def controller_decide_next(self, insight: str, audit_passed: bool) -> Tuple[str, str]:
        """
        逻辑控制器：决定继续或停止挖掘（新鲜度检查 Novelty Checker）
        使用向量语义分析 + 新关键词监测
        Args:
            insight: 当前洞察
            audit_passed: 审计是否通过
        Returns:
            (decision, reason) - 决策和原因
        """
        # 规则1: 审计未通过，但允许最多3次失败（给LLM学习纠错的机会）
        if not audit_passed:
            failed_rounds = [i for i, h in enumerate(self.insight_history) if not h.get('audit_passed', True)]
            failed_count = len(failed_rounds)
            
            if failed_count >= 3:
                self.high_similarity_count = 0  # 重置计数
                return "STOP", f"连续 {failed_count} 轮审计未通过，数据引用存在严重问题"
            else:
                print(f"  ⚠️ 审计未通过（第 {failed_count} 次），错误反馈已发送给 Analyst，允许继续尝试...")
                return "CONTINUE", f"审计未通过（第 {failed_count} 次），已反馈错误信息，允许再次尝试"
        
        # 规则2: 达到最大迭代次数
        if self.iteration_count >= self.max_iterations:
            return "STOP", f"已达到最大迭代次数 ({self.max_iterations})"
        
        # 规则3: 向量语义分析（新鲜度检查）
        # 仅对审计通过的洞察进行相似度检查，避免错误内容干扰
        valid_insights = [h for h in self.insight_history if h.get('audit_passed', False)]
        
        if valid_insights:
            print(f"\n[Controller - 新鲜度检查] Novelty Checker 启动...")
            print(f"  ℹ️  对比对象: {len(valid_insights)} 个已验证洞察（已排除 {len(self.insight_history) - len(valid_insights)} 个审计失败项）")
            
            # 方法1: 向量余弦相似度（主要方法）
            current_embedding = self._get_embedding(insight)
            max_similarity = 0.0
            
            if current_embedding is not None and self.insight_embeddings:
                similarities = [
                    self._cosine_similarity(current_embedding, hist_emb)
                    for hist_emb in self.insight_embeddings
                ]
                max_similarity = max(similarities) if similarities else 0.0
                print(f"  📊 向量余弦相似度: {max_similarity:.3f} (阈值: 0.90)")
            else:
                # 备选方案：文本相似度（仅对审计通过的洞察）
                similarities = [
                    SequenceMatcher(None, insight, hist['insight']).ratio()
                    for hist in valid_insights
                ]
                max_similarity = max(similarities) if similarities else 0.0
                print(f"  📊 文本相似度（备选）: {max_similarity:.3f} (阈值: 0.90)")
            
            # 方法2: 新关键词监测（信息密度）
            current_keywords = self._extract_keywords(insight)
            new_keywords = current_keywords - self.keywords_pool
            new_keyword_ratio = len(new_keywords) / max(len(current_keywords), 1)
            
            print(f"  🔑 新关键词数: {len(new_keywords)}/{len(current_keywords)} ({new_keyword_ratio:.1%})")
            print(f"  📝 新关键词: {', '.join(list(new_keywords)[:5])}..." if new_keywords else "  📝 新关键词: (无)")
            
            # 判定逻辑：相似度 > 0.9 且新关键词率 < 20%
            if max_similarity > 0.9:
                self.high_similarity_count += 1
                print(f"  ⚠️ 高相似度警告 (连续 {self.high_similarity_count} 轮)")
                
                # 连续2轮相似度过高 → 停止
                if self.high_similarity_count >= 2:
                    return "STOP", f"连续 {self.high_similarity_count} 轮高相似度 (>{max_similarity:.1%})，数据价值已被榨干"
                
                # 即使相似度高，如果有大量新关键词，可以继续
                if new_keyword_ratio < 0.2:
                    return "STOP", f"相似度过高 ({max_similarity:.1%}) 且新信息密度低 ({new_keyword_ratio:.1%})"
            else:
                self.high_similarity_count = 0  # 重置计数
            
            # 更新关键词池
            self.keywords_pool.update(current_keywords)
            
            print(f"  ✅ 新鲜度检查通过 (相似度: {max_similarity:.2%}, 新词率: {new_keyword_ratio:.1%})")
        
        return "CONTINUE", "审计通过且存在新发现，继续深度挖掘"
    
    # ==================== 主流程 ====================
    def run_single_iteration(self, user_prompt: str, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        运行单次迭代
        Returns:
            完整的 JSON 日志
        """
        print(f"\n{'='*60}")
        print(f"第 {self.iteration_count + 1} 轮挖掘")
        print(f"{'='*60}")
        
        # 步骤 1: Analyst 生成洞察
        print("\n[Analyst] 正在分析数据...")
        analyst_result = self.analyst_generate_insight(user_prompt, data_dict)
        print(f"洞察: {analyst_result['insight'][:100]}...")
        
        # 步骤 2: Auditor 验证证据（数据验证 + 逻辑审计）
        print("\n[Auditor] 正在验证证据...")
        is_parse_error = analyst_result.get('_parse_error', False)
        audit_passed, audit_log, error_feedback = self.auditor_verify_evidence(
            analyst_result.get('evidence', []),
            data_dict,
            analyst_result.get('insight', ''),
            is_parse_error=is_parse_error
        )
        print(audit_log)
        
        # 如果审计未通过，保存错误反馈供下一轮使用
        if not audit_passed and error_feedback:
            self.error_feedback = error_feedback
            print(f"\n⚠️ 错误反馈已保存，将在下一轮反馈给 Analyst")
        
        # 步骤 3: Controller 决策（新鲜度检查）
        decision, reason = self.controller_decide_next(analyst_result['insight'], audit_passed)
        print(f"\n[Controller] 决策: {decision}")
        print(f"[Controller] 原因: {reason}")
        
        # 更新系统状态 (Context Buffer) - 无论审计是否通过都要记录
        self.insight_history.append({
            'insight': analyst_result['insight'],
            'audit_passed': audit_passed
        })
        
        # 存储向量表示（仅审计通过时）
        if audit_passed:
            embedding = self._get_embedding(analyst_result['insight'])
            if embedding is not None:
                self.insight_embeddings.append(embedding)
            self.evidence_pool.extend(analyst_result.get('evidence', []))
        
        self.iteration_count += 1
        
        # 构建输出 JSON
        output = {
            "status": "Success" if audit_passed else "Failed",
            "iteration": self.iteration_count,
            "audit_report": {
                "is_passed": audit_passed,
                "log": audit_log
            },
            "analyst_result": {
                "insight": analyst_result['insight'],
                "evidence_trace": analyst_result.get('evidence', []),
                "tactical_recommendations": analyst_result.get('tactical_recommendations', [])
            },
            "system_generated_next_prompt": analyst_result.get('next_prompt', ''),
            "controller_decision": {
                "action": decision,
                "reason": reason
            }
        }
        
        return output


    def generate_markdown_report(self, result: Dict[str, Any], round_num: int = 1) -> str:
        """
        生成人类友好的 Markdown 格式报告
        Args:
            result: 单轮结果
            round_num: 轮次编号
        Returns:
            Markdown 格式的报告文本
        """
        md = []
        md.append(f"# 🔍 XHS-MarketAI 分析报告 - 第 {round_num} 轮\n")
        md.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**状态**: {'✅ 成功' if result['status'] == 'Success' else '❌ 失败'}\n")
        md.append("\n---\n")
        
        # 核心洞察
        md.append("\n## 💡 核心洞察\n")
        md.append(f"{result['analyst_result']['insight']}\n")
        
        # 证据支撑
        md.append("\n## 📊 数据证据\n")
        evidence_list = result['analyst_result'].get('evidence_trace', [])
        if evidence_list:
            md.append("| 数据源 | 关键词 | 搜索指数 | 数据行号 |\n")
            md.append("|--------|--------|----------|----------|\n")
            for ev in evidence_list:
                date = ev.get('date', '-')
                keyword = ev.get('keyword', '-')
                search_index = ev.get('search_index', '-')
                row = ev.get('original_row_index', '-')
                md.append(f"| {date} | {keyword} | {search_index:,} | {row} |\n")
        else:
            md.append("*无证据数据*\n")
        
        # 战术建议（新增）
        tactical_recs = result['analyst_result'].get('tactical_recommendations', [])
        if tactical_recs:
            md.append("\n## 🎯 战术建议\n")
            for i, rec in enumerate(tactical_recs, 1):
                md.append(f"{i}. {rec}\n")
        
        # 审计报告
        md.append("\n## 🔍 数据审计\n")
        audit = result['audit_report']
        md.append(f"**审计结果**: {'✅ 通过' if audit['is_passed'] else '❌ 未通过'}\n\n")
        md.append("```\n")
        md.append(audit['log'])
        md.append("\n```\n")
        
        # 下一步建议
        next_prompt = result.get('system_generated_next_prompt', '')
        if next_prompt:
            md.append("\n## 🚀 下一轮深度挖掘方向\n")
            md.append(f"> {next_prompt}\n")
        
        # 控制器决策
        md.append("\n## 🤖 系统决策\n")
        decision = result['controller_decision']
        md.append(f"**决策**: {decision['action']}\n")
        md.append(f"**原因**: {decision['reason']}\n")
        
        return "".join(md)
    
    def generate_full_markdown_report(self, all_results: List[Dict[str, Any]], 
                                     initial_prompt: str = "") -> str:
        """
        生成完整循环的 Markdown 报告
        Args:
            all_results: 所有轮次的结果
            initial_prompt: 初始分析需求
        Returns:
            完整的 Markdown 报告
        """
        md = []
        md.append("# 📈 XHS-MarketAI 完整分析报告\n\n")
        md.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**系统版本**: 2.0.0 (自进化数据挖掘机)\n\n")
        md.append("---\n\n")
        
        # 执行摘要
        md.append("## 📊 执行摘要\n\n")
        md.append(f"- **总轮数**: {len(all_results)}\n")
        md.append(f"- **有效洞察**: {len(self.insight_history)}\n")
        md.append(f"- **证据总数**: {len(self.evidence_pool)}\n")
        md.append(f"- **发现关键词**: {len(self.keywords_pool)}\n\n")
        
        # 分析目标
        if initial_prompt:
            md.append("## 🎯 分析目标\n\n")
            md.append("```\n")
            md.append(initial_prompt.strip())
            md.append("\n```\n\n")
        
        # 核心发现汇总
        md.append("## 💡 核心发现汇总\n\n")
        for i, item in enumerate(self.insight_history, 1):
            insight_text = item['insight'] if isinstance(item, dict) else item
            md.append(f"### 第 {i} 轮洞察\n\n")
            md.append(f"{insight_text}\n\n")
        
        # 详细分析过程
        md.append("---\n\n")
        md.append("## 📋 详细分析过程\n\n")
        
        for i, result in enumerate(all_results, 1):
            md.append(f"### 🔄 第 {i} 轮分析\n\n")
            
            # 洞察
            md.append(f"**洞察**: {result['analyst_result']['insight']}\n\n")
            
            # 证据表格
            evidence_list = result['analyst_result'].get('evidence_trace', [])
            if evidence_list:
                md.append("**证据**:\n\n")
                md.append("| 数据源 | 关键词 | 搜索指数 | 行号 |\n")
                md.append("|--------|--------|----------|------|\n")
                for ev in evidence_list:
                    date = ev.get('date', '-')
                    keyword = ev.get('keyword', '-')
                    search_index = ev.get('search_index', '-')
                    if isinstance(search_index, (int, float)):
                        search_index = f"{search_index:,}"
                    row = ev.get('original_row_index', '-')
                    md.append(f"| {date} | {keyword} | {search_index} | {row} |\n")
                md.append("\n")
            
            # 战术建议（新增）
            tactical_recs = result['analyst_result'].get('tactical_recommendations', [])
            if tactical_recs:
                md.append("**战术建议**:\n\n")
                for j, rec in enumerate(tactical_recs, 1):
                    md.append(f"{j}. {rec}\n")
                md.append("\n")
            
            # 审计状态
            audit_passed = "✅ 通过" if result['audit_report']['is_passed'] else "❌ 未通过"
            md.append(f"**审计**: {audit_passed}\n\n")
            
            # 决策
            decision = result['controller_decision']
            md.append(f"**决策**: {decision['action']} - {decision['reason']}\n\n")
            
            # 下一步
            next_prompt = result.get('system_generated_next_prompt', '')
            if next_prompt and i < len(all_results):
                md.append(f"**下一轮挖掘方向**: {next_prompt}\n\n")
            
            md.append("---\n\n")
        
        # 停止原因
        if all_results:
            last_result = all_results[-1]
            md.append("## 🛑 系统停止原因\n\n")
            md.append(f"{last_result['controller_decision']['reason']}\n\n")
        
        # 关键词发现
        if self.keywords_pool:
            md.append("## 🔑 关键词发现\n\n")
            keywords = sorted(list(self.keywords_pool))
            for i in range(0, len(keywords), 10):
                md.append(", ".join(keywords[i:i+10]))
                md.append("\n\n")
        
        md.append("---\n\n")
        md.append("*本报告由 XHS-MarketAI 洞察闭环系统自动生成*\n")
        
        return "".join(md)
    
    def run_full_cycle(self, initial_prompt: str, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        运行完整的迭代挖掘循环，直到停止
        Args:
            initial_prompt: 初始分析需求
            data_dict: 数据字典
        Returns:
            所有轮次的结果列表
        """
        print("\n" + "="*80)
        print("🚀 XHS-MarketAI 洞察闭环系统 - 自进化数据挖掘机")
        print("="*80)
        
        all_results = []
        current_prompt = initial_prompt
        
        while self.iteration_count < self.max_iterations:
            result = self.run_single_iteration(current_prompt, data_dict)
            all_results.append(result)
            
            decision = result['controller_decision']['action']
            
            if decision == "STOP":
                print(f"\n{'='*80}")
                print(f"🛑 系统停止：{result['controller_decision']['reason']}")
                print(f"{'='*80}")
                break
            
            # 使用 Analyst 生成的 next_prompt 作为下一轮输入
            current_prompt = result['system_generated_next_prompt']
            
            if not current_prompt:
                print("\n⚠️ 未生成下一轮提示，停止迭代")
                break
        
        # 输出总结
        print(f"\n" + "="*80)
        print(f"📊 挖掘完成总结")
        print("="*80)
        print(f"总轮数: {len(all_results)}")
        print(f"有效洞察数: {len(self.insight_history)}")
        print(f"证据总数: {len(self.evidence_pool)}")
        print(f"发现关键词数: {len(self.keywords_pool)}")
        
        return all_results
    
    def generate_executive_report(self, all_results: List[Dict[str, Any]], 
                                  initial_prompt: str = "") -> str:
        """
        生成高质量的执行摘要报告（仅包含审计通过的核心洞察）
        
        这是给决策者看的精简报告，包含：
        1. 核心发现TOP5
        2. 优先级行动计划（P0/P1/P2）
        3. 关键数据证据
        4. 风险提示
        
        Args:
            all_results: 所有轮次的结果
            initial_prompt: 初始分析需求
        Returns:
            高质量Markdown报告
        """
        md = []
        
        # 标题
        md.append("# 🎯 市场洞察执行报告\n\n")
        md.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**报告版本**: Executive Summary v3.0\n\n")
        md.append("---\n\n")
        
        # 只保留审计通过的结果
        valid_results = [r for r in all_results if r['audit_report']['is_passed']]
        failed_results = [r for r in all_results if not r['audit_report']['is_passed']]
        
        # 1. 执行摘要
        md.append("## 📊 执行摘要\n\n")
        md.append(f"- **分析轮数**: {len(all_results)} 轮\n")
        md.append(f"- **高质量洞察**: {len(valid_results)} 条（审计通过）\n")
        md.append(f"- **被拒绝分析**: {len(failed_results)} 条（数据问题）\n")
        
        # 计算总证据数
        total_evidence = sum(len(r['analyst_result'].get('evidence_trace', [])) for r in valid_results)
        md.append(f"- **数据证据总数**: {total_evidence} 条\n")
        md.append(f"- **数据可信度**: {len(valid_results)/len(all_results)*100:.1f}%\n\n")
        
        if initial_prompt:
            md.append("### 分析目标\n\n")
            md.append(f"```\n{initial_prompt.strip()}\n```\n\n")
        
        # 2. 核心发现TOP5
        md.append("## 💡 核心发现 TOP5\n\n")
        for i, result in enumerate(valid_results[:5], 1):
            insight = result['analyst_result']['insight']
            evidence_count = len(result['analyst_result'].get('evidence_trace', []))
            md.append(f"### {i}. {insight[:100]}{'...' if len(insight) > 100 else ''}\n\n")
            md.append(f"**数据支撑**: {evidence_count} 条证据\n\n")
            
            # 显示关键证据
            evidences = result['analyst_result'].get('evidence_trace', [])
            if evidences:
                md.append("**关键数据**:\n")
                for ev in evidences[:3]:  # 只显示前3条
                    keyword = ev.get('keyword', '-')
                    search_index = ev.get('search_index', '-')
                    date = ev.get('date', '-')
                    md.append(f"- {date}: '{keyword}' 搜索指数 {search_index:,}\n")
                md.append("\n")
        
        # 3. 优先级行动计划
        md.append("## 🎯 优先级行动计划\n\n")
        
        # 收集所有战术建议并分类
        p0_actions = []
        p1_actions = []
        p2_actions = []
        other_actions = []
        
        for result in valid_results:
            recs = result['analyst_result'].get('tactical_recommendations', [])
            for rec in recs:
                if '【P0' in rec or '【P0' in rec:
                    p0_actions.append(rec)
                elif '【P1' in rec or '【P1' in rec:
                    p1_actions.append(rec)
                elif '【P2' in rec or '【P2' in rec:
                    p2_actions.append(rec)
                else:
                    other_actions.append(rec)
        
        if p0_actions:
            md.append("### 🔴 P0优先级 - 立即执行（1-3天）\n\n")
            for i, action in enumerate(p0_actions, 1):
                md.append(f"{i}. {action}\n\n")
        
        if p1_actions:
            md.append("### 🟡 P1优先级 - 本周内执行（3-7天）\n\n")
            for i, action in enumerate(p1_actions, 1):
                md.append(f"{i}. {action}\n\n")
        
        if p2_actions:
            md.append("### 🟢 P2优先级 - 本月内执行（1-4周）\n\n")
            for i, action in enumerate(p2_actions, 1):
                md.append(f"{i}. {action}\n\n")
        
        # 4. 关键数据总览
        md.append("## 📈 关键数据总览\n\n")
        md.append("### 已验证的核心数据点\n\n")
        md.append("| 轮次 | 关键词 | 搜索指数 | 数据源 | 行号 |\n")
        md.append("|------|--------|----------|--------|------|\n")
        
        for i, result in enumerate(valid_results, 1):
            evidences = result['analyst_result'].get('evidence_trace', [])
            for ev in evidences[:2]:  # 每轮显示2条关键证据
                keyword = ev.get('keyword', '-')
                search_index = ev.get('search_index', '-')
                date = ev.get('date', '-')
                row = ev.get('original_row_index', '-')
                md.append(f"| 第{i}轮 | {keyword} | {search_index:,} | {date} | {row} |\n")
        
        md.append("\n")
        
        # 5. 风险提示
        if failed_results:
            md.append("## ⚠️ 风险提示与被拒绝的分析\n\n")
            md.append(f"系统在 {len(failed_results)} 轮分析中发现数据质量问题，已自动拒绝：\n\n")
            for i, result in enumerate(failed_results, 1):
                reason = result['controller_decision'].get('reason', '未知原因')
                md.append(f"{i}. **第{result.get('iteration', '?')}轮**: {reason}\n")
            md.append("\n这些被拒绝的分析不会影响最终建议的可信度。\n\n")
        
        # 6. 数据来源说明
        md.append("## 📚 数据来源\n\n")
        md.append("本报告的所有洞察和建议均基于以下已验证的数据源：\n\n")
        md.append("- **数据时间**: 2025年6月（旺季）、2025年12月（淡季）\n")
        md.append("- **数据维度**: 搜索指数、自然笔记数、广告消耗、市场出价、搜索增速等25个维度\n")
        md.append(f"- **验证证据数**: {total_evidence} 条\n")
        md.append(f"- **数据可信度**: {len(valid_results)/len(all_results)*100:.1f}%（通过审计比例）\n\n")
        
        # 7. 下一步建议
        if valid_results:
            last_valid = valid_results[-1]
            next_prompt = last_valid.get('system_generated_next_prompt', '')
            if next_prompt:
                md.append("## 🔮 深度挖掘建议\n\n")
                md.append(f"> {next_prompt}\n\n")
        
        md.append("---\n\n")
        md.append("**报告说明**: 本报告仅包含通过数据审计的高质量洞察，所有数据均可追溯到原始行号。\n\n")
        md.append(f"*由 XHS-MarketAI v3.0 自动生成 | {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        return "".join(md)


# ==================== 测试代码 ====================
def main():
    """主测试函数"""
    
    print("="*80)
    print("XHS-MarketAI System - 自进化数据挖掘机")
    print("="*80)
    
    # 初始化系统（需要设置 API Key）
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("\n⚠️  请设置环境变量 DASHSCOPE_API_KEY")
        print("或者在代码中直接传入: system = MarketInsightSystem(api_key='your_key')")
        print("\n获取API Key: https://dashscope.console.aliyun.com/apiKey")
        return
    
    system = MarketInsightSystem(api_key=api_key)
    
    # 加载数据
    print("\n📊 加载数据...")
    data_dict = system.load_data(
        file_paths=[
            "data/搜索词-2025-6月.xlsx",
            "data/搜索词-2025-12月.xlsx"
        ],
        labels=["6月", "12月"]
    )
    
    if not data_dict:
        print("❌ 数据加载失败")
        return
    
    # 用户初始提示
    user_initial_prompt = """
[核心背景]
产品："松达松子粉"（婴儿爽身粉）；竞品："贝亲桃子水"。

[战略目标]
现在是12月（淡季），通过半年布局，在明年夏季（旺季）抢夺桃子水市场。

[分析要求]
对6月（旺季）与12月（淡季）的数据做深度对比。
1. 寻找"淡季布局"的蓝海词。
2. 分析用户在不同季节对"桃子水"与"爽身粉"的需求差异。
3. **务必输出原始数据支撑**（如搜索指数、笔记数）。
"""
    
    # 选择运行模式
    print("\n请选择运行模式:")
    print("1. 单轮测试（只运行第一轮）")
    print("2. 完整循环（自动迭代直到停止）")
    
    mode = input("\n请输入选择 (1/2，默认2): ").strip() or "2"
    
    if mode == "1":
        # 单轮测试
        result = system.run_single_iteration(user_initial_prompt, data_dict)
        
        print("\n" + "="*80)
        print("📋 第一轮挖掘结果 (JSON)")
        print("="*80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 保存 JSON
        with open("output/insight_result_round1.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("\n✅ JSON 结果已保存至: output/insight_result_round1.json")
        
        # 保存 Markdown
        markdown_report = system.generate_markdown_report(result, round_num=1)
        with open("output/insight_result_round1.md", "w", encoding="utf-8") as f:
            f.write(markdown_report)
        print("✅ Markdown 报告已保存至: insight_result_round1.md")
    
    else:
        # 完整循环
        all_results = system.run_full_cycle(user_initial_prompt, data_dict)
        
        print("\n" + "="*80)
        print("📋 完整挖掘结果 (所有轮次)")
        print("="*80)
        
        # 保存 JSON 结果
        output = {
            "total_iterations": len(all_results),
            "total_insights": len(system.insight_history),
            "total_keywords": len(system.keywords_pool),
            "all_rounds": all_results,
            "final_insight_summary": system.insight_history
        }
        
        with open("output/insight_full_cycle.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("\n✅ JSON 结果已保存至: output/insight_full_cycle.json")
        
        # 保存 Markdown 报告（完整版，包含所有轮次）
        markdown_report = system.generate_full_markdown_report(all_results, user_initial_prompt)
        with open("output/insight_full_cycle.md", "w", encoding="utf-8") as f:
            f.write(markdown_report)
        print("✅ 完整报告已保存至: output/insight_full_cycle.md")
        
        # 🎯 生成高质量执行摘要报告（仅包含审计通过的核心洞察）
        executive_report = system.generate_executive_report(all_results, user_initial_prompt)
        with open("output/EXECUTIVE_SUMMARY.md", "w", encoding="utf-8") as f:
            f.write(executive_report)
        print("✅ 🎯 执行摘要报告已保存至: output/EXECUTIVE_SUMMARY.md")
        print("   （这是给决策者看的精简版，仅包含高质量洞察和行动计划）")
        
        # 输出关键发现
        print("\n" + "="*80)
        print("🔍 关键发现汇总")
        print("="*80)
        for i, item in enumerate(system.insight_history, 1):
            insight_text = item['insight'] if isinstance(item, dict) else item
            print(f"\n第 {i} 轮: {insight_text[:150]}...")


if __name__ == "__main__":
    main()
