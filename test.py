import random

# 用集合存储已出现的不同数字
appeared = set()

# 循环直到集合大小达到 43
while len(appeared) < 43:
    num = random.randint(1, 49)   # 生成 1~49 的随机整数
    appeared.add(num)             # 加入集合（自动去重）

# 转换为列表并排序
result = sorted(appeared)

# 输出结果（一行显示，空格分隔）
print("出现的 43 个不同数字（从小到大）：")
print(" ".join(map(str, result)))

# 可选：输出总共生成了多少次随机数（包括重复）
# print(f"共生成了 {total_attempts} 次随机数才达到 43 个不同数字。")