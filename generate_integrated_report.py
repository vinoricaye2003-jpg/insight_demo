#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速生成整合报告脚本
从已有的 insight_full_cycle.json 生成用户友好的整合报告
"""

import json
import sys
from market_insight_system import MarketInsightSystem
import os

def main():
    # 加载已有的分析结果
    try:
        with open("output/insight_full_cycle.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 output/insight_full_cycle.json")
        print("请先运行完整循环: python market_insight_system.py")
        return
    
    all_results = data.get('all_rounds', [])
    
    if not all_results:
        print("❌ JSON文件中没有分析结果")
        return
    
    # 初始化系统（只需要生成报告，不需要API key）
    api_key = os.getenv("DASHSCOPE_API_KEY", "dummy_key")
    system = MarketInsightSystem(api_key=api_key)
    
    # 用户提示词（从JSON中提取或使用默认）
    user_prompt = """
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
    
    print("="*80)
    print("📊 生成整合洞察报告")
    print("="*80)
    print(f"分析轮数: {len(all_results)}")
    
    # 生成整合报告
    integrated_report = system.generate_integrated_report(all_results, user_prompt)
    
    # 保存报告
    output_file = "output/INTEGRATED_REPORT.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(integrated_report)
    
    print(f"\n✅ 整合报告已保存至: {output_file}")
    print("\n📋 报告预览（前500字符）:")
    print("-"*80)
    print(integrated_report[:500])
    print("-"*80)
    print(f"\n📄 完整报告长度: {len(integrated_report)} 字符")


if __name__ == "__main__":
    main()
