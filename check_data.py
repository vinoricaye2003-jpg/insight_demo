import pandas as pd

df6 = pd.read_excel("搜索词-2025-6月.xlsx")
df12 = pd.read_excel("搜索词-2025-12月.xlsx")

test_words = ["婴儿爽身粉推荐新生儿", "婴儿湿疹怎么护理", "松达面霜", "贝亲爽身粉"]

print("=" * 60)
print("关键词在6月和12月数据中的存在情况")
print("=" * 60)

for word in test_words:
    in_6 = word in df6["搜索词"].values
    in_12 = word in df12["搜索词"].values
    
    val_6 = "不存在"
    val_12 = "不存在"
    
    if in_6:
        val_6 = int(df6[df6["搜索词"]==word]["搜索次数指数"].values[0])
    if in_12:
        val_12 = int(df12[df12["搜索词"]==word]["搜索次数指数"].values[0])
    
    print(f"\n{word}:")
    print(f"  6月: {val_6}")
    print(f"  12月: {val_12}")
