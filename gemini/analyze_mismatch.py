#!/usr/bin/env python3
"""分析未匹配的CDL，找出可以进一步宽松的规则"""
import json

with open('detailed_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("未匹配CDL分析 - 寻找宽松化机会")
print("="*80)

# 分析IMAGE CDL的不匹配
print("\n【IMAGE CDL 不匹配分析】")
for item in data[:3]:
    pred_set = set(item['image']['pred'])
    gt_set = set(item['image']['gt'])
    
    missing = gt_set - pred_set  # 标准答案有，但预测没有的
    extra = pred_set - gt_set     # 预测有，但标准答案没有的
    
    if missing or extra:
        print(f"\n题目 {item['problem_id']}:")
        if missing:
            print(f"  缺失的CDL: {list(missing)[:3]}")
        if extra:
            print(f"  多余的CDL: {list(extra)[:3]}")

print("\n\n【可能的宽松化策略】")
print("-" * 60)

# 1. 提取所有谓词类型
all_pred_predicates = set()
all_gt_predicates = set()

for item in data:
    for cdl in item['image']['pred']:
        pred_name = cdl.split('(')[0]
        all_pred_predicates.add(pred_name)
    for cdl in item['image']['gt']:
        pred_name = cdl.split('(')[0]
        all_gt_predicates.add(pred_name)

print("\n策略1: 谓词类型匹配")
print(f"  Gemini使用的谓词: {sorted(all_pred_predicates)}")
print(f"  标准答案的谓词: {sorted(all_gt_predicates)}")
print(f"  不在标准答案的谓词: {sorted(all_pred_predicates - all_gt_predicates)}")
print(f"  Gemini未使用的谓词: {sorted(all_gt_predicates - all_pred_predicates)}")

# 2. 数值匹配分析
import re

print("\n策略2: 数值提取匹配")
print("  原理: 只要提取到相同的数值，就认为部分正确")
print("  示例:")

for item in data[:2]:
    print(f"\n  题目 {item['problem_id']}:")
    
    # 提取预测中的所有数值
    pred_numbers = set()
    for cdl in item['image']['pred']:
        nums = re.findall(r'\d+\.?\d*', cdl)
        pred_numbers.update(nums)
    
    # 提取标准答案中的所有数值
    gt_numbers = set()
    for cdl in item['image']['gt']:
        nums = re.findall(r'\d+\.?\d*', cdl)
        gt_numbers.update(nums)
    
    print(f"    预测中的数值: {sorted(pred_numbers)}")
    print(f"    标准答案的数值: {sorted(gt_numbers)}")
    common = pred_numbers & gt_numbers
    if common:
        print(f"    共同数值: {sorted(common)} - 可给予部分分数")

# 3. 谓词名称匹配
print("\n策略3: 谓词名称部分匹配")
print("  原理: 相同谓词名的CDL给予部分分数，不管参数是否完全相同")

pred_type_counts = {}
gt_type_counts = {}

for item in data:
    for cdl in item['image']['pred']:
        pred_name = cdl.split('(')[0]
        pred_type_counts[pred_name] = pred_type_counts.get(pred_name, 0) + 1
    for cdl in item['image']['gt']:
        pred_name = cdl.split('(')[0]
        gt_type_counts[pred_name] = gt_type_counts.get(pred_name, 0) + 1

print(f"\n  预测中最常见的谓词:")
for pred, count in sorted(pred_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"    {pred}: {count}次")

print(f"\n  标准答案最常见的谓词:")
for pred, count in sorted(gt_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"    {pred}: {count}次")

print("\n" + "="*80)
print("\n推荐宽松化方案:")
print("1. 谓词名称匹配: 相同谓词名给0.5分")
print("2. 数值匹配: 提取到相同数值给0.3分")  
print("3. 组合匹配: 谓词名+数值都匹配给0.8分")
print("4. 完全匹配: 保持1.0分")
print("\n这样可以更好地反映Gemini的实际提取能力")




