"""
测试增强版多维度分析系统
"""
import pandas as pd

# 测试数据加载和高级指标计算
print("="*60)
print("测试高级指标计算")
print("="*60)

df = pd.read_excel("搜索词-2025-12月.xlsx")

print(f"\n原始列数: {len(df.columns)}")
print(f"原始列名: {df.columns.tolist()[:10]}...")

# 模拟系统的指标计算
if '搜索次数指数' in df.columns and '自然笔记数' in df.columns:
    # 处理数值类型
    df['搜索次数指数'] = pd.to_numeric(df['搜索次数指数'], errors='coerce')
    
    # 处理"2.9万"这种格式
    notes = df['自然笔记数'].astype(str).str.replace('万', '0000').str.replace('k', '000')
    df['自然笔记数_数值'] = pd.to_numeric(notes, errors='coerce').fillna(0)
    
    df['内容空白度'] = df['搜索次数指数'] / (df['自然笔记数_数值'] + 1)
    df['竞争强度'] = df['自然笔记数_数值'] / (df['搜索次数指数'] + 1)
    
    if '广告消耗（元）' in df.columns:
        cost = pd.to_numeric(df['广告消耗（元）'], errors='coerce').fillna(0)
        df['广告性价比'] = df['搜索次数指数'] / (cost + 1)

print(f"\n增强后列数: {len(df.columns)}")

# 分析1: 内容空白度最高的词（蓝海机会）
print("\n" + "="*60)
print("【发现1】内容空白度TOP10（搜索高但笔记少 = 蓝海）")
print("="*60)
if '内容空白度' in df.columns:
    top_gap = df.nlargest(10, '内容空白度')[['搜索词', '搜索次数指数', '自然笔记数', '内容空白度']]
    print(top_gap.to_string(index=False))

# 分析2: 广告性价比最高的词
print("\n" + "="*60)
print("【发现2】广告性价比TOP10（搜索高但成本低）")
print("="*60)
if '广告性价比' in df.columns:
    valid_data = df[df['广告性价比'] < 999999]
    if len(valid_data) > 0:
        top_roi = valid_data.nlargest(10, '广告性价比')[['搜索词', '搜索次数指数', '广告消耗（元）', '广告性价比']]
        print(top_roi.to_string(index=False))

# 分析3: 搜索增速为正的词（逆势增长）
print("\n" + "="*60)
print("【发现3】逆势增长词（搜索增速>0的机会）")
print("="*60)
if '搜索增速' in df.columns:
    # 清理百分号
    df['搜索增速_数值'] = df['搜索增速'].astype(str).str.replace('%', '').astype(float)
    growth_positive = df[df['搜索增速_数值'] > 0].nlargest(10, '搜索增速_数值')[['搜索词', '搜索次数指数', '搜索增速']]
    if len(growth_positive) > 0:
        print(growth_positive.to_string(index=False))
    else:
        print("未发现搜索增速为正的词（全部下跌）")

# 分析4: 竞争强度分析
print("\n" + "="*60)
print("【发现4】竞争强度分析（蓝海 vs 红海）")
print("="*60)
if '竞争强度' in df.columns:
    print("\n蓝海词（竞争强度<0.3）：")
    blue_ocean = df[df['竞争强度'] < 0.3].nlargest(10, '搜索次数指数')[['搜索词', '搜索次数指数', '自然笔记数', '竞争强度']]
    print(blue_ocean.to_string(index=False))
    
    print("\n红海词（竞争强度>1.0）：")
    red_ocean = df[df['竞争强度'] > 1.0].nlargest(5, '搜索次数指数')[['搜索词', '搜索次数指数', '自然笔记数', '竞争强度']]
    if len(red_ocean) > 0:
        print(red_ocean.to_string(index=False))

# 分析5: 点击率分析
print("\n" + "="*60)
print("【发现5】自然点击率TOP10（内容吸引力强）")
print("="*60)
if '自然点击率' in df.columns:
    # 清理百分号
    df['自然点击率_数值'] = df['自然点击率'].astype(str).str.replace('%', '').str.split('-').str[0].astype(float)
    top_ctr = df.nlargest(10, '自然点击率_数值')[['搜索词', '搜索次数指数', '自然点击率']]
    print(top_ctr.to_string(index=False))

print("\n" + "="*60)
print("测试完成！系统已具备多维度分析能力")
print("="*60)
