"""
快速测试脚本 - 无需 API 调用（使用模拟数据）
用于测试系统架构是否正常工作
"""

import pandas as pd
import json
from market_insight_system import MarketInsightSystem


class MockMarketInsightSystem(MarketInsightSystem):
    """模拟版本 - 不调用真实 API"""
    
    def __init__(self):
        # 系统状态 (Context Buffer) - 与主系统保持一致
        self.iteration_count = 0
        self.max_iterations = 5
        self.insight_history = []
        self.insight_embeddings = []  # 向量历史
        self.evidence_pool = []
        self.keywords_pool = set()  # 关键词池
        self.high_similarity_count = 0  # 连续高相似度计数
        self.error_feedback = None  # 错误反馈
    
    def _get_embedding(self, text: str):
        """模拟 Embedding - 返回 None，使用备用方案"""
        return None
    
    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """模拟 LLM 响应 - 使用正确的字段名"""
        mock_response = {
            "insight": "桃子水在6月搜索指数为56516，12月降至23456，下降58.5%。这显示出明显的季节性特征，夏季高温期婴儿痱子护理需求旺盛。",
            "evidence": [
                {"date": "6月", "keyword": "桃子水", "search_index": 56516, "original_row_index": 0},
                {"date": "12月", "keyword": "桃子水", "search_index": 23456, "original_row_index": 0}
            ],
            "next_prompt": "深入分析：在12月淡季，搜索'婴儿湿疹'、'冬季护肤'、'松达'等关键词的数据，找出哪些长尾词仍保持稳定热度，作为淡季布局的切入点。"
        }
        
        return f"```json\n{json.dumps(mock_response, ensure_ascii=False, indent=2)}\n```"


def create_mock_data():
    """创建模拟数据用于测试"""
    data_june = pd.DataFrame({
        '关键词': ['桃子水', '爽身粉', '痱子粉', '松达', '婴儿护肤', '夏季护理'],
        '搜索指数': [56516, 12345, 8900, 3456, 15678, 7890],
        '笔记数': [1234, 567, 890, 234, 678, 345],
        '互动数': [12340, 5670, 8900, 2340, 6780, 3450]
    })
    data_june['_original_row_index'] = data_june.index
    data_june['_data_source'] = '6月'
    
    data_december = pd.DataFrame({
        '关键词': ['桃子水', '爽身粉', '痱子粉', '松达', '婴儿护肤', '冬季护理'],
        '搜索指数': [23456, 6789, 4567, 2345, 9876, 5432],
        '笔记数': [678, 234, 456, 123, 432, 234],
        '互动数': [6780, 2340, 4560, 1230, 4320, 2340]
    })
    data_december['_original_row_index'] = data_december.index
    data_december['_data_source'] = '12月'
    
    return {'6月': data_june, '12月': data_december}


def main():
    print("="*80)
    print("XHS-MarketAI System - 模拟测试（无需 API Key）")
    print("="*80)
    print("\n⚠️  这是模拟测试版本，使用预设响应数据")
    print("真实运行请使用: python market_insight_system.py\n")
    
    # 使用模拟系统
    system = MockMarketInsightSystem()
    
    # 创建模拟数据
    print("📊 加载模拟数据...")
    data_dict = create_mock_data()
    print(f"✓ 6月数据: {len(data_dict['6月'])} 行")
    print(f"✓ 12月数据: {len(data_dict['12月'])} 行")
    
    # 用户提示
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
    
    # 运行测试
    result = system.run_single_iteration(user_initial_prompt, data_dict)
    
    # 输出结果
    print("\n" + "="*80)
    print("📋 测试结果 (JSON)")
    print("="*80)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 保存 JSON 结果
    with open("test_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n✅ JSON 结果已保存至: test_result.json")
    
    # 保存 Markdown 报告
    markdown_report = system.generate_markdown_report(result, round_num=1)
    with open("test_result.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)
    print("✅ Markdown 报告已保存至: test_result.md")
    
    print("\n" + "="*80)
    print("✅ 系统架构测试完成！")
    print("="*80)
    print("\n下一步：")
    print("1. 设置 DeepSeek API Key")
    print("2. 运行真实系统: python market_insight_system.py")


if __name__ == "__main__":
    main()
