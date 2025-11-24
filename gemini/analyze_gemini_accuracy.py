# -*- coding: utf-8 -*-
"""
分析Gemini测试结果的准确率
"""
import json
import os
import sys
from collections import defaultdict

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def analyze_gemini_results(test_log_path: str):
    """
    分析Gemini测试结果的准确率
    """
    print(f"[分析] Gemini测试结果: {test_log_path}")
    
    # 读取测试日志
    with open(test_log_path, 'r', encoding='utf-8') as f:
        test_results = json.load(f)
    
    total = len(test_results)
    correct = 0
    wrong = 0
    error = 0
    skipped = 0
    
    status_breakdown = defaultdict(int)
    match_info_types = defaultdict(int)
    
    # 分析每个结果
    for result in test_results:
        status = result.get('status', 'unknown')
        status_breakdown[status] += 1
        
        match_info = result.get('match_info', '')
        if match_info:
            match_info_types[match_info] += 1
        
        if status == 'correct':
            correct += 1
        elif status == 'wrong':
            wrong += 1
        elif status in ['error', 'skipped']:
            if status == 'skipped':
                skipped += 1
            else:
                error += 1
    
    # 计算准确率
    valid_total = correct + wrong
    accuracy = (correct / valid_total * 100) if valid_total > 0 else 0
    
    # 生成报告
    report = {
        'summary': {
            'total_problems': total,
            'correct': correct,
            'wrong': wrong,
            'error': error,
            'skipped': skipped,
            'valid_total': valid_total,
            'accuracy': f"{accuracy:.2f}%"
        },
        'status_breakdown': dict(status_breakdown),
        'match_info_breakdown': dict(match_info_types)
    }
    
    # 打印报告
    print("\n" + "="*60)
    print("Gemini测试结果统计")
    print("="*60)
    print(f"总问题数: {total}")
    print(f"[正确] {correct}")
    print(f"[错误] {wrong}")
    print(f"[错误] {error}")
    print(f"[跳过] {skipped}")
    print(f"[有效答案数] {valid_total}")
    print(f"[准确率] {accuracy:.2f}%")
    print("\n状态分布:")
    for status, count in sorted(status_breakdown.items()):
        print(f"  {status}: {count}")
    
    print("\n匹配信息分布:")
    for match_info, count in sorted(match_info_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {match_info}: {count}")
    
    print("="*60)
    
    # 保存报告
    output_dir = os.path.dirname(test_log_path)
    report_path = os.path.join(output_dir, '_accuracy_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细报告已保存到: {report_path}")
    
    return report

if __name__ == '__main__':
    # 默认路径
    test_log_path = "gemini_test_results_all/_test_log_temp.json"
    
    if len(sys.argv) > 1:
        test_log_path = sys.argv[1]
    
    if not os.path.exists(test_log_path):
        print(f"错误: 找不到文件: {test_log_path}")
        sys.exit(1)
    
    analyze_gemini_results(test_log_path)

