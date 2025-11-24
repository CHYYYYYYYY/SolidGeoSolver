#!/usr/bin/env python3
"""分析评估结果，找出改进空间"""
import json
from collections import defaultdict

# 读取详细结果
with open('detailed_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("Gemini CDL 评估结果分析")
print("="*80)

# 1. TEXT CDL 分析
print("\n【1. TEXT CDL 分析 - 为什么只有8% F1？】")
print("-" * 60)
text_issues = []
for item in data:
    pred = item['text']['pred']
    gt = item['text']['gt']
    if item['text']['metrics']['f1'] < 1.0:
        text_issues.append({
            'id': item['problem_id'],
            'pred': pred,
            'gt': gt,
            'pred_types': set([p.split('(')[0] for p in pred]),
            'gt_types': set([g.split('(')[0] for g in gt])
        })

print(f"不完美匹配的题目数: {len(text_issues)}/{len(data)}")
for issue in text_issues[:3]:  # 显示前3个
    print(f"\n题目 {issue['id']}:")
    print(f"  预测: {issue['pred']}")
    print(f"  标准: {issue['gt']}")
    print(f"  问题: Gemini把实体声明 (如Cone) 放在text_cdl, 但标准答案期望是条件 (如Equal)")

# 2. IMAGE CDL 分析
print("\n\n【2. IMAGE CDL 分析 - 已经不错，但有提升空间】")
print("-" * 60)
image_recalls = [item['image']['metrics']['recall'] for item in data]
avg_recall = sum(image_recalls) / len(image_recalls)
print(f"平均召回率: {avg_recall:.2%}")

missing_predicates = defaultdict(int)
for item in data:
    pred_set = set(item['image']['pred'])
    gt_set = set(item['image']['gt'])
    missing = gt_set - pred_set
    for m in missing:
        predicate_name = m.split('(')[0]
        missing_predicates[predicate_name] += 1

print(f"\n最常遗漏的谓词:")
for pred, count in sorted(missing_predicates.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {pred}: {count} 次")

# 3. 改进建议
print("\n\n【3. 具体改进建议】")
print("-" * 60)

# 分析 text_cdl 和 image_cdl 的混淆
print("\n[问题1] text_cdl 和 image_cdl 分类混淆")
for item in data[:2]:
    print(f"\n题目 {item['problem_id']}:")
    print(f"  Gemini的text_cdl: {item['text']['pred']}")
    print(f"  标准的text_cdl: {item['text']['gt']}")
    print(f"  Gemini的image_cdl: {item['image']['pred'][:2]}")
    print(f"  标准的image_cdl: {item['image']['gt'][:2]}")

print("\n[改进建议]")
print("  1. Gemini倾向于把 Cone(), Circle() 等实体声明放在text_cdl")
print("  2. 标准答案期望text_cdl包含的是文本描述的数值条件（如高度=12）")
print("  3. 建议：优化Prompt，明确text_cdl应该是'文本中明确说明的数值/条件'")
print("  4. 建议：实体类型声明应该从图片推断，放在image_cdl")

# 4. 潜在的宽松匹配改进
print("\n\n【4. 可以进一步宽松的匹配策略】")
print("-" * 60)

print("\n策略A: 语义等价匹配")
print("  - Cone(C1) 在 text_cdl 和 Cone(O,P) 在 image_cdl 语义相同")
print("  - 可以允许跨字段的等价匹配")
print("  - 当前: text_cdl中的Cone不匹配任何东西 [NO]")
print("  - 改进: text_cdl中的Cone可以匹配image_cdl中的Cone [YES]")

print("\n策略B: 合并评估")
print("  - 将 text_cdl + image_cdl 合并为一个集合评估")
print("  - 只要谓词在任一字段出现都算正确")
print("  - 这更符合实际应用场景（我们关心信息是否提取，不太关心来源）")

# 5. 计算如果采用策略B的效果
print("\n\n【5. 模拟策略B效果】")
print("-" * 60)
print("如果将 text_cdl 和 image_cdl 合并评估：")

total_pred = []
total_gt = []
for item in data:
    pred_combined = set(item['text']['pred'] + item['image']['pred'])
    gt_combined = set(item['text']['gt'] + item['image']['gt'])
    total_pred.append(pred_combined)
    total_gt.append(gt_combined)

# 计算合并后的指标
from evaluate_cdl import GeminiCDLEvaluator
evaluator = GeminiCDLEvaluator()

combined_metrics = []
for pred_set, gt_set in zip(total_pred, total_gt):
    metrics = evaluator.calculate_set_metrics(list(pred_set), list(gt_set))
    combined_metrics.append(metrics)

avg_f1 = sum(m['f1'] for m in combined_metrics) / len(combined_metrics)
avg_precision = sum(m['precision'] for m in combined_metrics) / len(combined_metrics)
avg_recall = sum(m['recall'] for m in combined_metrics) / len(combined_metrics)

print(f"  合并后 F1: {avg_f1:.2%}")
print(f"  合并后 Precision: {avg_precision:.2%}")
print(f"  合并后 Recall: {avg_recall:.2%}")
print(f"\n  对比当前:")
print(f"  TEXT F1: 8.00% -> 合并后提升到 {avg_f1:.2%}")
print(f"  IMAGE F1: 65.32% -> 合并后 {avg_f1:.2%}")
print(f"  总体提升: {'显著' if avg_f1 > 0.65 else '有限'}")

print("\n" + "="*80)

