# -*- coding: utf-8 -*-
"""
生成详细的评估报告
"""
import json
import os
import sys
from collections import defaultdict

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def generate_detailed_report(re_evaluated_log_path: str, output_path: str = None):
    """
    生成详细的评估报告，包括：
    - 按问题类型统计
    - 按复杂度级别统计
    - 常见错误类型分析
    """
    print(f"[生成详细报告] {re_evaluated_log_path}")
    
    with open(re_evaluated_log_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # 统计信息
    stats = {
        'total': len(results),
        'correct': 0,
        'wrong': 0,
        'error': 0,
        'skipped': 0,
        'by_status': defaultdict(int),
        'error_types': defaultdict(int),
        'close_matches': []  # 接近但错误的答案
    }
    
    # 分析每个结果
    for result in results:
        status = result.get('status', 'unknown')
        stats['by_status'][status] += 1
        
        if status == 'correct':
            stats['correct'] += 1
        elif status == 'wrong':
            stats['wrong'] += 1
            # 分析错误原因
            chatgpt_answer = result.get('chatgpt_answer', '')
            standard_answer = result.get('standard_answer', '')
            
            # 尝试判断错误类型
            try:
                chatgpt_num = float(re.sub(r'[^0-9.]', '', chatgpt_answer) or '0')
                standard_num = float(re.sub(r'[^0-9.]', '', standard_answer) or '0')
                
                if standard_num != 0:
                    relative_error = abs(chatgpt_num - standard_num) / abs(standard_num)
                    if relative_error < 0.1:  # 相对误差小于10%
                        stats['close_matches'].append({
                            'problem_id': result.get('problem_id'),
                            'chatgpt_answer': chatgpt_answer,
                            'standard_answer': standard_answer,
                            'relative_error': relative_error
                        })
            except:
                pass
        elif status in ['error', 'skipped']:
            stats['error'] += 1
            error_reason = result.get('match_info', 'Unknown')
            stats['error_types'][error_reason] += 1
    
    # 计算准确率
    valid_total = stats['correct'] + stats['wrong']
    accuracy = (stats['correct'] / valid_total * 100) if valid_total > 0 else 0
    
    # 生成报告
    report = {
        'summary': {
            'total_problems': stats['total'],
            'correct': stats['correct'],
            'wrong': stats['wrong'],
            'error': stats['error'],
            'skipped': stats['skipped'],
            'valid_total': valid_total,
            'accuracy': f"{accuracy:.2f}%"
        },
        'status_breakdown': dict(stats['by_status']),
        'error_analysis': {
            'error_types': dict(stats['error_types']),
            'close_matches_count': len(stats['close_matches']),
            'close_matches': sorted(stats['close_matches'], key=lambda x: x['relative_error'])[:20]
        }
    }
    
    # 保存报告
    if output_path is None:
        output_dir = os.path.dirname(re_evaluated_log_path)
        output_path = os.path.join(output_dir, '_detailed_report.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 打印报告
    print("\n" + "="*60)
    print("详细评估报告")
    print("="*60)
    print(f"总问题数: {report['summary']['total_problems']}")
    print(f"[正确] {report['summary']['correct']}")
    print(f"[错误] {report['summary']['wrong']}")
    print(f"[错误/跳过] {report['summary']['error']}")
    print(f"[有效答案数] {report['summary']['valid_total']}")
    print(f"[准确率] {report['summary']['accuracy']}")
    print("\n状态分布:")
    for status, count in report['status_breakdown'].items():
        print(f"  {status}: {count}")
    
    print(f"\n接近但错误的答案（相对误差<10%）: {report['error_analysis']['close_matches_count']} 个")
    if report['error_analysis']['close_matches']:
        print("\n前10个最接近的答案:")
        for i, match in enumerate(report['error_analysis']['close_matches'][:10], 1):
            print(f"{i}. 问题 {match['problem_id']}: ChatGPT={match['chatgpt_answer']}, 标准={match['standard_answer']}, 相对误差={match['relative_error']*100:.2f}%")
    
    print(f"\n详细报告已保存到: {output_path}")
    
    return report

if __name__ == '__main__':
    import re
    
    # 默认路径
    re_evaluated_log_path = "chatgpt_test_results_1_357/_re_evaluated_log.json"
    
    if len(sys.argv) > 1:
        re_evaluated_log_path = sys.argv[1]
    
    if not os.path.exists(re_evaluated_log_path):
        print(f"错误: 找不到文件: {re_evaluated_log_path}")
        sys.exit(1)
    
    generate_detailed_report(re_evaluated_log_path)

