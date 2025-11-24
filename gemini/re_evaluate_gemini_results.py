# -*- coding: utf-8 -*-
"""
使用智能匹配逻辑重新评估Gemini测试结果
"""
import json
import os
import sys
import datetime

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入之前创建的智能匹配函数
sys.path.insert(0, 'gemini')
from re_evaluate_chatgpt_results import expressions_equal, normalize_answer

def re_evaluate_gemini_results(test_log_path: str):
    """
    使用智能匹配逻辑重新评估Gemini测试结果
    """
    try:
        print(f"[重新评估] Gemini测试结果: {test_log_path}")
    except:
        print("[重新评估] Gemini测试结果:", test_log_path)
    
    # 读取测试日志
    with open(test_log_path, 'r', encoding='utf-8') as f:
        test_results = json.load(f)
    
    total = len(test_results)
    correct = 0
    wrong = 0
    error = 0
    skipped = 0
    corrected = []  # 从错误改为正确的记录
    
    detailed_results = []
    
    for result in test_results:
        problem_id = result.get('problem_id', 0)
        standard_answer = result.get('standard_answer', '')
        gemini_answer = result.get('gemini_answer', '')
        original_status = result.get('status', 'unknown')
        
        new_result = result.copy()
        
        if not standard_answer:
            new_result['status'] = 'skipped'
            new_result['match_info'] = '标准答案为空'
            skipped += 1
        elif not gemini_answer or gemini_answer.lower() in ['none', 'null', '']:
            new_result['status'] = 'error'
            new_result['match_info'] = 'Gemini答案为空'
            error += 1
        else:
            # 使用更智能的匹配逻辑
            is_correct = expressions_equal(gemini_answer, standard_answer)
            
            if is_correct:
                new_result['status'] = 'correct'
                correct += 1
                
                # 如果原来是错误的，记录为修正
                if original_status == 'wrong':
                    corrected.append({
                        'problem_id': problem_id,
                        'original_status': original_status,
                        'gemini_answer': gemini_answer,
                        'standard_answer': standard_answer,
                        'match_info': result.get('match_info', '')
                    })
                    new_result['match_info'] = f"重新评估：正确 (Gemini: {gemini_answer}, 标准: {standard_answer})"
                else:
                    new_result['match_info'] = f"完全匹配 (Gemini: {gemini_answer}, 标准: {standard_answer})"
            else:
                new_result['status'] = 'wrong'
                wrong += 1
                new_result['match_info'] = f"不匹配 (Gemini: {gemini_answer}, 标准: {standard_answer})"
        
        detailed_results.append(new_result)
    
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
            'accuracy': f"{accuracy:.2f}%",
            'valid_total': valid_total,
            'corrected_count': len(corrected)
        },
        'corrected_cases': corrected[:50],  # 只显示前50个修正的案例
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 保存结果
    output_dir = os.path.dirname(test_log_path)
    output_path = os.path.join(output_dir, '_re_evaluation_report.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 保存详细结果
    detailed_output_path = os.path.join(output_dir, '_re_evaluated_log.json')
    with open(detailed_output_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # 打印统计
    print("\n" + "="*60)
    print("重新评估结果统计")
    print("="*60)
    print(f"总问题数: {total}")
    print(f"[正确] {correct}")
    print(f"[错误] {wrong}")
    print(f"[错误/跳过] {error + skipped}")
    print(f"[有效答案数] {valid_total}")
    print(f"[准确率] {accuracy:.2f}%")
    print(f"[修正的案例数] {len(corrected)}")
    print("="*60)
    
    if corrected:
        print(f"\n前10个修正的案例（从错误改为正确）:")
        for i, case in enumerate(corrected[:10], 1):
            print(f"{i}. 问题 {case['problem_id']}: Gemini={case['gemini_answer']}, 标准={case['standard_answer']}")
            print(f"   原匹配信息: {case.get('match_info', 'N/A')}")
    
    print(f"\n详细报告已保存到: {output_path}")
    print(f"详细日志已保存到: {detailed_output_path}")
    
    return report

if __name__ == '__main__':
    # 默认测试日志路径
    test_log_path = "../gemini_test_results_all/_test_log_temp.json"
    
    if len(sys.argv) > 1:
        test_log_path = sys.argv[1]
    elif not os.path.exists(test_log_path):
        # 尝试从项目根目录
        test_log_path = "gemini_test_results_all/_test_log_temp.json"
    
    if not os.path.exists(test_log_path):
        print("错误: 找不到测试日志文件:", test_log_path)
        sys.exit(1)
    
    re_evaluate_gemini_results(test_log_path)

