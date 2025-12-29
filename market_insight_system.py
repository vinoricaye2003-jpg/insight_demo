"""
XHS-MarketAI System: 自进化数据挖掘机
集成 Qwen API 的市场洞察分析系统
"""

import pandas as pd
import json
import os
import re
from typing import Dict, List, Any, Tuple, Set
from difflib import SequenceMatcher
from openai import OpenAI
import numpy as np
from collections import Counter
from dotenv import load_dotenv

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
        self.max_iterations = 5
        self.insight_history = []  # 所有洞察历史（含审计失败项，用于完整报告和调试）
        self.insight_embeddings = []  # 向量存储（仅审计通过的洞察）
        self.evidence_pool = []  # 证据池
        self.keywords_pool = set()  # 已发现的关键词池
        self.high_similarity_count = 0  # 连续高相似度计数
        self.error_feedback = None  # 错误反馈信息
        
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
                
                data_dict[label] = df
                print(f"✓ 加载数据: {label} - {len(df)} 行, {len(df.columns)} 列")
                
            except Exception as e:
                print(f"✗ 加载失败 {path}: {e}")
                
        return data_dict
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        获取文本的向量表示 (Embedding)
        Args:
            text: 输入文本
        Returns:
            向量数组
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
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
        
        system_prompt = """你是一位资深市场战略分析师，专注于小红书电商数据挖掘和竞争情报分析。

## 【战略背景】
- **我方产品**：松达松子粉（婴儿爽身粉）
- **核心竞品**：贝亲桃子水
- **战略目标**：从竞品手中抢夺市场份额，寻找攻击缺口和蓝海机会
- **分析视角**：每个洞察都要回答"如何利用这个发现击败桃子水"

## 核心规则（严格遵守）：
1. **必须基于真实数据**：所有结论必须从下方提供的实际数据中提取，禁止凭空推测或编造数字
2. **证据必须精确**：引用的数字必须与原始数据完全一致（包括关键词、搜索指数、日期等）
3. **竞争思维**：每个洞察要分析"松达的机会"和"桃子水的弱点"
4. **战术落地**：不仅要说"发现了什么"，更要说"松达应该怎么做"
5. **输出格式严格**：必须按照 JSON 格式输出，字段名必须精确匹配

## 输出格式（严格遵守字段名）：
```json
{
  "insight": "桃子水在6月搜索指数为99300，而12月降至35858，下降63.9%。而'婴儿水'搜索指数从6月18211仅降至12月18698（+2.7%），季节性极弱，是淡季流量的蓝海入口。松达可截流这18698次/月搜索。",
  "evidence": [
    {"date": "6月", "keyword": "桃子水", "search_index": 99300, "original_row_index": 3},
    {"date": "12月", "keyword": "桃子水", "search_index": 35858, "original_row_index": 0},
    {"date": "6月", "keyword": "婴儿水", "search_index": 18211, "original_row_index": 15},
    {"date": "12月", "keyword": "婴儿水", "search_index": 18698, "original_row_index": 2}
  ],
  "tactical_recommendations": [
    "立即在小红书搜索'婴儿水'时投放松达广告，截流18698次/月的淡季搜索",
    "创作'婴儿水 vs 松子粉'对比内容，引导用户从桃子水转向松达",
    "在淡季（12月-次年5月）重点布局'婴儿水'关键词，抢占桃子水淡季流失的用户"
  ],
  "next_prompt": "深度挖掘：分析搜索'桃子水'的用户在12月淡季还搜索了哪些关联词？这些关联词中，哪些是'桃子水'品牌词未覆盖的空白市场？松达如何利用这些空白词截流桃子水用户？"
}
```

## ⚠️ 关键要求（必须严格遵守）：
- **evidence 字段名必须是**: date, keyword, search_index, original_row_index（不能使用 row）
- **keyword 必须从下方数据的'搜索词'列中精确复制**，不能修改或简化
- **search_index 必须从下方数据的'搜索次数指数'列中精确复制**，不能四舍五入或估算
- **original_row_index 是数据在表格中的行号**（从0开始，看数据示例左侧的序号）
- **date 必须是'6月'或'12月'**，对应数据来源
- **tactical_recommendations 必须包含3个可执行的战术建议**：具体到"在哪投广告"、"创作什么内容"、"布局哪些词"
- **next_prompt 必须深入且具有战略性**：不能只是"继续分析XXX"，而要提出"挖掘更深层价值"的问题，如"竞争盲区在哪"、"用户心理如何漂移"、"蓝海词的隐藏机会"
- **每个结论都要有2-4个证据支撑**，形成完整的数据链条
- **禁止编造数据**：如果数据中没有某个关键词，绝对不能虚构其搜索指数
"""
        
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
            print(f"JSON 解析失败: {e}")
            print(f"原始响应: {response}")
            return {
                "insight": "解析失败，请检查响应格式",
                "evidence": [],
                "tactical_recommendations": ["解析失败，无法生成战术建议"],
                "next_prompt": user_prompt,
                "raw_response": response
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
            summary_lines.append(f"\n【前20行数据示例】（含行号用于追溯）：")
            # 选择关键列展示
            if keyword_col and search_col:
                display_cols = [keyword_col, search_col]
                display_df = df[display_cols].head(20).copy()
                display_df.insert(0, 'row_index', df['_original_row_index'].head(20))
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
                # TOP 10 关键词
                top_keywords = df.nlargest(10, search_col)[[keyword_col, search_col, '_original_row_index']]
                summary_lines.append(f"\n【TOP 10 高搜索指数关键词】：")
                summary_lines.append(top_keywords.to_string(index=False))
        
        return "\n".join(summary_lines)
    
    # ==================== 组件 B: The Auditor ====================
    def auditor_verify_evidence(self, evidence: List[Dict], data_dict: Dict[str, pd.DataFrame], insight: str = "") -> Tuple[bool, str, str]:
        """
        事实审计员：硬核验证证据真实性（防止AI幻觉）
        Args:
            evidence: Analyst 提交的证据列表
            data_dict: 原始数据字典
        Returns:
            (is_passed, log_message, error_feedback)
        """
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
        audit_passed, audit_log, error_feedback = self.auditor_verify_evidence(
            analyst_result.get('evidence', []),
            data_dict,
            analyst_result.get('insight', '')
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
            "搜索词-2025-6月.xlsx",
            "搜索词-2025-12月.xlsx"
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
        with open("insight_result_round1.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("\n✅ JSON 结果已保存至: insight_result_round1.json")
        
        # 保存 Markdown
        markdown_report = system.generate_markdown_report(result, round_num=1)
        with open("insight_result_round1.md", "w", encoding="utf-8") as f:
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
        
        with open("insight_full_cycle.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("\n✅ JSON 结果已保存至: insight_full_cycle.json")
        
        # 保存 Markdown 报告
        markdown_report = system.generate_full_markdown_report(all_results, user_initial_prompt)
        with open("insight_full_cycle.md", "w", encoding="utf-8") as f:
            f.write(markdown_report)
        print("✅ Markdown 报告已保存至: insight_full_cycle.md")
        
        # 输出关键发现
        print("\n" + "="*80)
        print("🔍 关键发现汇总")
        print("="*80)
        for i, item in enumerate(system.insight_history, 1):
            insight_text = item['insight'] if isinstance(item, dict) else item
            print(f"\n第 {i} 轮: {insight_text[:150]}...")


if __name__ == "__main__":
    main()
