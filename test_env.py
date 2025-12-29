"""测试 .env 文件加载"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

print("=" * 60)
print("环境变量加载测试")
print("=" * 60)

# 检查 Qwen API Key
dashscope_key = os.getenv("DASHSCOPE_API_KEY")
if dashscope_key:
    print(f"✅ DASHSCOPE_API_KEY: {dashscope_key[:15]}...{dashscope_key[-5:] if len(dashscope_key) > 20 else ''}")
    print(f"   密钥长度: {len(dashscope_key)}")
else:
    print("❌ 未找到 DASHSCOPE_API_KEY")

# 检查 DeepSeek API Key
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
if deepseek_key:
    print(f"✅ DEEPSEEK_API_KEY: {deepseek_key[:15]}...{deepseek_key[-5:]}")
    print(f"   密钥长度: {len(deepseek_key)}")
else:
    print("⚠️  未设置 DEEPSEEK_API_KEY（可选）")

print("\n" + "=" * 60)
print("测试完成！如果显示✅，说明 .env 文件加载成功")
print("=" * 60)
