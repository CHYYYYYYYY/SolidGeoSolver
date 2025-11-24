# -*- coding: utf-8 -*-
"""
重新评估ChatGPT测试结果，使用更智能的答案匹配逻辑
"""
import json
import os
import re
import sys
from typing import Dict, List, Any
from decimal import Decimal, getcontext

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 设置高精度计算
getcontext().prec = 50

def normalize_answer(answer: str) -> str:
    """
    标准化答案格式，提取纯数字或数学表达式
    """
    if not answer:
        return ""
    
    # 转为字符串并去除首尾空格
    answer = str(answer).strip()
    
    # 移除常见的标记文本
    answer = re.sub(r'^(FINAL ANSWER|Answer|ANSWER|Result|RESULT|答案)[:\s]*', '', answer, flags=re.IGNORECASE)
    # 注意：不要移除**，因为这是幂运算符号
    # 只移除markdown的**加粗（前后都有空格的情况）
    answer = re.sub(r'\s+\*\*\s+', ' ', answer)  # 移除markdown加粗（保留空格）
    answer = re.sub(r'^[:\s]*', '', answer)  # 移除开头的冒号和空格
    answer = re.sub(r'[:\s]*$', '', answer)  # 移除结尾的冒号和空格
    
    # 移除单位（保留数字和pi）
    answer = re.sub(r'\s*(cm|m|meter|meters|units?|degrees?|°|cm²|cm³|m²|m³|square|square\s+units?)\s*$', '', answer, flags=re.IGNORECASE)
    
    # 移除多余的空白字符（但保留必要的空格用于分隔）
    answer = re.sub(r'\s+', ' ', answer).strip()
    
    return answer

def extract_number_from_text(text: str) -> str:
    """
    从文本中提取数字（包括小数和表达式）
    """
    if not text:
        return ""
    
    # 先尝试提取完整的数学表达式（包含pi）
    pi_pattern = r'([0-9]+\.?[0-9]*\s*\*?\s*[πpi]+|[0-9]+\.?[0-9]*\s*[πpi]+)'
    match = re.search(pi_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 提取所有数字（包括小数）
    numbers = re.findall(r'[-+]?\d+\.?\d*', text)
    if numbers:
        # 返回最后一个数字（通常是最终答案）
        return numbers[-1]
    
    return ""

def normalize_math_expression(expr: str) -> str:
    """
    标准化数学表达式格式
    """
    if not expr:
        return ""
    
    expr = expr.strip().lower()
    
    # 替换LaTeX格式的sqrt
    expr = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', expr)
    expr = re.sub(r'√([0-9]+)', r'sqrt(\1)', expr)
    expr = re.sub(r'\\\(|\\\)', '', expr)  # 移除LaTeX括号
    
    # 统一pi的表示
    expr = expr.replace('π', 'pi').replace('\\pi', 'pi')
    
    # 统一幂次表示：x^2 -> x**2, x^{2} -> x**2
    expr = re.sub(r'\^(\d+)', r'**\1', expr)
    expr = re.sub(r'\^\{(\d+)\}', r'**\1', expr)
    
    # 统一变量名（R->r, L->l, 但保留大小写信息用于后续处理）
    # 注意：这里先不统一，因为可能需要区分大小写
    
    # 统一乘法表示：移除多余的空格
    expr = re.sub(r'\s*\*\s*', '*', expr)
    expr = re.sub(r'\s+\*\s+', '*', expr)
    
    # 移除所有空格
    expr = re.sub(r'\s+', '', expr)
    
    return expr

def normalize_variables(expr: str) -> str:
    """
    归一化变量名（R->r, L->l等），用于等价性比较
    """
    # 将大写变量名转为小写（用于等价性比较）
    expr = expr.replace('R', 'r').replace('L', 'l')
    return expr

def expand_and_normalize_expression(expr: str) -> str:
    """
    展开并标准化表达式，用于等价性比较
    例如：2*pi*r*(l+r) -> 2*pi*r*l+2*pi*r*r
    """
    # 先归一化变量
    expr = normalize_variables(expr)
    
    # 简化分数：4/3*pi -> 4*pi/3
    expr = re.sub(r'(\d+)/(\d+)\*pi', r'\1*pi/\2', expr)
    
    # 简化括号内的加法：*(r+r) -> *r+*r
    # 但这里简化处理，主要是归一化格式
    # 注意：完全展开括号需要更复杂的解析，这里只做基本处理
    
    return expr

def extract_polynomial_coefficients(expr: str) -> dict:
    """
    提取多项式的系数
    例如：12x^2+144x+384 -> {2: 12, 1: 144, 0: 384}
    """
    coeffs = {}
    # 归一化变量
    expr = normalize_variables(expr)
    # 移除空格
    expr = re.sub(r'\s+', '', expr)
    
    # 先统一格式：x^2 -> x**2
    expr = re.sub(r'x\^(\d+)', r'x**\1', expr)
    expr = re.sub(r'x\^\{(\d+)\}', r'x**\1', expr)
    
    # 分割成项（按+或-分割，但要保留符号）
    # 先添加分隔符
    expr = re.sub(r'([+-])', r'|\1', expr)
    if not expr.startswith('|'):
        expr = '|+' + expr
    terms = expr.split('|')[1:]  # 跳过第一个空元素
    
    for term in terms:
        if not term:
            continue
        
        # 提取符号
        sign = 1
        if term.startswith('-'):
            sign = -1
            term = term[1:]
        elif term.startswith('+'):
            term = term[1:]
        
        # 匹配 x**n 或 x 或 纯数字
        if 'x**' in term:
            # x**n 形式
            match = re.match(r'(\d*\.?\d*)\*?x\*\*(\d+)', term)
            if match:
                coeff_str = match.group(1)
                power = int(match.group(2))
                coeff_val = float(coeff_str) if coeff_str else 1.0
                coeffs[power] = coeffs.get(power, 0) + sign * coeff_val
        elif 'x' in term and '**' not in term:
            # x 形式（一次项）
            match = re.match(r'(\d*\.?\d*)\*?x', term)
            if match:
                coeff_str = match.group(1)
                coeff_val = float(coeff_str) if coeff_str else 1.0
                coeffs[1] = coeffs.get(1, 0) + sign * coeff_val
        else:
            # 纯数字（常数项）
            match = re.match(r'(\d+\.?\d*)', term)
            if match:
                coeff_val = float(match.group(1))
                coeffs[0] = coeffs.get(0, 0) + sign * coeff_val
    
    return coeffs

def expressions_equal(pred: str, gold: str) -> bool:
    """
    比较两个数学表达式是否相等
    支持：
    - 纯数字比较（容忍精度差异，但更严格）
    - 包含pi的表达式
    - 包含sqrt的表达式
    - 多项式表达式（考虑乘法交换律）
    """
    pred = normalize_answer(pred)
    gold = normalize_answer(gold)
    
    if not pred or not gold:
        return False
    
    # 完全匹配（忽略大小写和空格）
    pred_clean = re.sub(r'\s+', '', pred.lower())
    gold_clean = re.sub(r'\s+', '', gold.lower())
    if pred_clean == gold_clean:
        return True
    
    # 标准化数学表达式格式
    pred_norm = normalize_math_expression(pred)
    gold_norm = normalize_math_expression(gold)
    
    if pred_norm == gold_norm:
        return True
    
    # 归一化变量名后比较（R->r, L->l）
    pred_var_norm = normalize_variables(pred_norm)
    gold_var_norm = normalize_variables(gold_norm)
    
    if pred_var_norm == gold_var_norm:
        return True
    
    # 展开并归一化后比较
    pred_expanded = expand_and_normalize_expression(pred_norm)
    gold_expanded = expand_and_normalize_expression(gold_norm)
    
    if pred_expanded == gold_expanded:
        return True
    
    # 尝试数值比较（仅当两者都是纯数字时）
    try:
        # 检查是否都是纯数字（可能带小数点）
        pred_is_num = bool(re.match(r'^[-+]?\d+\.?\d*$', pred_clean))
        gold_is_num = bool(re.match(r'^[-+]?\d+\.?\d*$', gold_clean))
        
        if pred_is_num and gold_is_num:
            pred_val = float(pred_clean)
            gold_val = float(gold_clean)
            
            # 更严格的数值比较：
            # 1. 如果都是整数，必须完全相等
            if pred_val == int(pred_val) and gold_val == int(gold_val):
                return pred_val == gold_val
            
            # 2. 对于小数，相对误差小于0.01%或绝对误差小于0.001
            if gold_val != 0:
                relative_error = abs(pred_val - gold_val) / abs(gold_val)
                if relative_error < 0.0001:  # 更严格：0.01%
                    return True
            else:
                if abs(pred_val - gold_val) < 0.001:
                    return True
            
            # 3. 检查四舍五入到相同小数位后是否相等
            # 根据标准答案的小数位数决定精度
            gold_str = str(gold_val)
            if '.' in gold_str:
                decimal_places = len(gold_str.split('.')[1])
                if abs(round(pred_val, decimal_places) - round(gold_val, decimal_places)) < 0.0001:
                    return True
    except (ValueError, AttributeError):
        pass
    
    # 尝试计算包含pi和sqrt的表达式
    try:
        import math
        
        def safe_eval(expr: str, substitute_vars: bool = False) -> float:
            """安全地计算数学表达式"""
            # 归一化变量名
            if substitute_vars:
                expr = normalize_variables(expr)
                # 如果包含变量，尝试用1替换（用于等价性检查）
                expr = re.sub(r'\b[rl]\b', '1', expr)
            
            # 替换sqrt
            expr = expr.replace('sqrt', 'math.sqrt')
            # 替换pi
            expr = expr.replace('pi', 'math.pi')
            # 替换**为Python的幂运算
            # 移除不安全的字符
            allowed_chars = set('0123456789+-*/.()math.sqrtpi')
            if all(c in allowed_chars or c.isalnum() or c in ' _' for c in expr):
                try:
                    return eval(expr)
                except:
                    return None
            return None
        
        # 先尝试直接计算
        pred_val = safe_eval(pred_norm)
        gold_val = safe_eval(gold_norm)
        
        # 如果pred包含pi但gold是纯数字，尝试计算pred的数值
        if pred_val is None and 'pi' in pred_norm.lower() and gold_val is not None:
            pred_val = safe_eval(pred_norm, substitute_vars=False)
            # 如果pred有变量，尝试用1替换变量后计算
            if pred_val is None and re.search(r'\b[rl]\b', pred_norm.lower()):
                pred_val = safe_eval(pred_norm, substitute_vars=True)
        
        # 如果gold包含pi但pred是纯数字，尝试计算gold的数值
        if gold_val is None and 'pi' in gold_norm.lower() and pred_val is not None:
            gold_val = safe_eval(gold_norm, substitute_vars=False)
            if gold_val is None and re.search(r'\b[rl]\b', gold_norm.lower()):
                gold_val = safe_eval(gold_norm, substitute_vars=True)
        
        if pred_val is not None and gold_val is not None:
            # 对于计算结果，使用更严格的比较
            if gold_val != 0:
                relative_error = abs(pred_val - gold_val) / abs(gold_val)
                if relative_error < 0.0001:  # 0.01%
                    return True
            else:
                if abs(pred_val - gold_val) < 0.001:
                    return True
    except:
        pass
    
    # 特殊处理：如果pred有pi但gold没有，尝试计算pred的数值与gold比较
    try:
        import math
        
        def safe_eval_helper(expr: str) -> float:
            """辅助函数：安全计算表达式"""
            expr = expr.replace('sqrt', 'math.sqrt').replace('pi', 'math.pi')
            allowed_chars = set('0123456789+-*/.()math.sqrtpi')
            if all(c in allowed_chars or c.isalnum() or c in ' _' for c in expr):
                try:
                    return eval(expr)
                except:
                    return None
            return None
        
        if 'pi' in pred_norm.lower() and 'pi' not in gold_norm.lower():
            # 检查gold是否是纯数字
            gold_is_num = bool(re.match(r'^[-+]?\d+\.?\d*$', gold_clean))
            if gold_is_num:
                # 尝试计算pred（如果有变量，用1替换）
                pred_with_vars = normalize_variables(pred_norm)
                pred_with_vars = re.sub(r'\b[rl]\b', '1', pred_with_vars)
                pred_val = safe_eval_helper(pred_with_vars)
                gold_val = float(gold_clean)
                if pred_val is not None:
                    if gold_val != 0:
                        relative_error = abs(pred_val - gold_val) / abs(gold_val)
                        if relative_error < 0.0001:
                            return True
                    else:
                        if abs(pred_val - gold_val) < 0.001:
                            return True
    except:
        pass
    
    # 对于多项式表达式，尝试提取系数进行比较
    # 例如：12x^2+144x+384 vs 12*x**2+144*x+384
    try:
        # 归一化变量名后提取token
        pred_var_norm = normalize_variables(pred_norm)
        gold_var_norm = normalize_variables(gold_norm)
        
        # 提取所有数字和运算符
        pred_tokens = re.findall(r'[-+]?\d+\.?\d*|\*|\+|-|x|\*\*|sqrt|pi|[rl]', pred_var_norm)
        gold_tokens = re.findall(r'[-+]?\d+\.?\d*|\*|\+|-|x|\*\*|sqrt|pi|[rl]', gold_var_norm)
        
        # 如果token数量相同，可能是格式不同但内容相同
        if len(pred_tokens) == len(gold_tokens) and len(pred_tokens) > 3:
            # 尝试重新组合并比较
            pred_recombined = ''.join(pred_tokens)
            gold_recombined = ''.join(gold_tokens)
            if pred_recombined == gold_recombined:
                return True
            
            # 尝试排序后比较（考虑乘法交换律）
            # 例如：2*pi*sqrt(13) vs 2*sqrt(13)*pi
            pred_sorted = ''.join(sorted(pred_tokens))
            gold_sorted = ''.join(sorted(gold_tokens))
            if pred_sorted == gold_sorted:
                return True
    except:
        pass
    
    # 特殊处理：处理分数等价性
    # 例如：4/3*pi vs 4*pi/3
    try:
        # 检查是否都是分数形式
        pred_frac = re.sub(r'(\d+)/(\d+)\*pi', r'\1*pi/\2', pred_norm)
        gold_frac = re.sub(r'(\d+)/(\d+)\*pi', r'\1*pi/\2', gold_norm)
        
        pred_frac = normalize_variables(pred_frac)
        gold_frac = normalize_variables(gold_frac)
        
        if pred_frac == gold_frac:
            return True
    except:
        pass
    
    # 特殊处理：多项式系数比较
    # 例如：12x^2+144x+384 vs 12*x**2+144*x+384
    try:
        if 'x' in pred_norm.lower() and 'x' in gold_norm.lower():
            pred_coeffs = extract_polynomial_coefficients(pred_norm)
            gold_coeffs = extract_polynomial_coefficients(gold_norm)
            
            if pred_coeffs == gold_coeffs:
                return True
    except:
        pass
    
    # 特殊处理：处理包含括号的表达式
    # 例如：2*pi*R*(L+R) vs 2*pi*(r+R)*(R+L-r)
    # 如果变量归一化后结构相似，尝试数值验证
    try:
        import math
        
        def safe_eval_helper2(expr: str) -> float:
            """辅助函数：安全计算表达式"""
            expr = expr.replace('sqrt', 'math.sqrt').replace('pi', 'math.pi')
            allowed_chars = set('0123456789+-*/.()math.sqrtpi')
            if all(c in allowed_chars or c.isalnum() or c in ' _' for c in expr):
                try:
                    return eval(expr)
                except:
                    return None
            return None
        
        # 归一化变量后，如果都包含相同的因子，尝试用具体数值验证
        pred_var = normalize_variables(pred_norm)
        gold_var = normalize_variables(gold_norm)
        
        # 如果都包含pi和相同的变量组合，尝试计算
        if 'pi' in pred_var and 'pi' in gold_var:
            # 尝试用具体数值替换变量（r=1, l=1等）
            test_values = {'r': 1, 'l': 1, 'x': 1}
            pred_test = pred_var
            gold_test = gold_var
            
            for var, val in test_values.items():
                pred_test = re.sub(rf'\b{var}\b', str(val), pred_test)
                gold_test = re.sub(rf'\b{var}\b', str(val), gold_test)
            
            pred_val = safe_eval_helper2(pred_test)
            gold_val = safe_eval_helper2(gold_test)
            
            if pred_val is not None and gold_val is not None:
                if gold_val != 0:
                    relative_error = abs(pred_val - gold_val) / abs(gold_val)
                    if relative_error < 0.0001:
                        return True
                else:
                    if abs(pred_val - gold_val) < 0.001:
                        return True
    except:
        pass
    
    return False

def re_evaluate_results(test_log_path: str, output_path: str = None):
    """
    重新评估测试结果，使用更智能的答案匹配
    """
    print(f"[重新评估] 测试结果: {test_log_path}")
    
    # 读取测试日志
    with open(test_log_path, 'r', encoding='utf-8') as f:
        test_results = json.load(f)
    
    total = len(test_results)
    correct = 0
    wrong = 0
    error = 0
    corrected = []  # 从错误改为正确的记录
    
    detailed_results = []
    
    for result in test_results:
        problem_id = result.get('problem_id', 0)
        standard_answer = result.get('standard_answer', '')
        chatgpt_answer = result.get('chatgpt_answer', '')
        original_status = result.get('status', 'unknown')
        
        new_result = result.copy()
        
        if not standard_answer:
            new_result['status'] = 'skipped'
            new_result['match_info'] = '标准答案为空'
            error += 1
        elif not chatgpt_answer:
            new_result['status'] = 'error'
            new_result['match_info'] = 'ChatGPT答案为空'
            error += 1
        else:
            # 使用更智能的匹配逻辑
            is_correct = expressions_equal(chatgpt_answer, standard_answer)
            
            if is_correct:
                new_result['status'] = 'correct'
                correct += 1
                
                # 如果原来是错误的，记录为修正
                if original_status == 'wrong':
                    corrected.append({
                        'problem_id': problem_id,
                        'original_status': original_status,
                        'chatgpt_answer': chatgpt_answer,
                        'standard_answer': standard_answer,
                        'match_info': result.get('match_info', '')
                    })
                    new_result['match_info'] = f"重新评估：正确 (ChatGPT: {chatgpt_answer}, 标准: {standard_answer})"
                else:
                    new_result['match_info'] = f"完全匹配 (ChatGPT: {chatgpt_answer}, 标准: {standard_answer})"
            else:
                new_result['status'] = 'wrong'
                wrong += 1
                new_result['match_info'] = f"不匹配 (ChatGPT: {chatgpt_answer}, 标准: {standard_answer})"
        
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
            'skipped': 0,
            'accuracy': f"{accuracy:.2f}%",
            'valid_total': valid_total,
            'corrected_count': len(corrected)
        },
        'corrected_cases': corrected[:50],  # 只显示前50个修正的案例
        'timestamp': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 保存结果
    if output_path is None:
        output_dir = os.path.dirname(test_log_path)
        output_path = os.path.join(output_dir, '_re_evaluation_report.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 保存详细结果
    detailed_output_path = output_path.replace('_re_evaluation_report.json', '_re_evaluated_log.json')
    with open(detailed_output_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # 打印统计
    print("\n" + "="*60)
    print("重新评估结果统计")
    print("="*60)
    print(f"总问题数: {total}")
    print(f"[正确] {correct}")
    print(f"[错误] {wrong}")
    print(f"[错误/跳过] {error}")
    print(f"[有效答案数] {valid_total}")
    print(f"[准确率] {accuracy:.2f}%")
    print(f"[修正的案例数] {len(corrected)}")
    print("="*60)
    
    if corrected:
        print(f"\n前10个修正的案例（从错误改为正确）:")
        for i, case in enumerate(corrected[:10], 1):
            print(f"{i}. 问题 {case['problem_id']}: ChatGPT={case['chatgpt_answer']}, 标准={case['standard_answer']}")
            print(f"   原匹配信息: {case.get('match_info', 'N/A')}")
    
    print(f"\n详细报告已保存到: {output_path}")
    print(f"详细日志已保存到: {detailed_output_path}")
    
    return report

if __name__ == '__main__':
    import sys
    
    # 默认测试日志路径
    test_log_path = "chatgpt_test_results_1_357/_test_log.json"
    
    if len(sys.argv) > 1:
        test_log_path = sys.argv[1]
    
    if not os.path.exists(test_log_path):
        print(f"错误: 找不到测试日志文件: {test_log_path}")
        sys.exit(1)
    
    re_evaluate_results(test_log_path)

