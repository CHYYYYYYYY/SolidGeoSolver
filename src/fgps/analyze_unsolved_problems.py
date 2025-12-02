#!/usr/bin/env python3
"""
分析未解决的问题
"""

import json
import os
from pathlib import Path

def load_json(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_terminal_output():
    """分析终端输出中的问题状态"""
    # 您的最新终端输出数据
    terminal_data = """
43396   1       solved  [('circle_property_length_of_radius_and_diameter', '1', ('O',))]
8556    2       solved  []
.....   ....    ........... 
"""

    solved_problems = set()
    unsolved_problems = set()
    error_problems = set()
    
    # 解析终端输出
    lines = terminal_data.strip().split('\n')
    for line in lines:
        if line.strip():
            parts = line.split()
            if len(parts) >= 3:
                try:
                    problem_id = int(parts[1])
                    result = parts[2]
                    
                    if result == 'solved':
                        solved_problems.add(problem_id)
                    elif result == 'unsolved':
                        unsolved_problems.add(problem_id)
                    elif result == 'error':
                        error_problems.add(problem_id)
                
                except (ValueError, IndexError):
                    continue
    
    return solved_problems, unsolved_problems, error_problems

def check_problem_files(problems_dir, max_problem_id=119):
    """检查问题文件的状态"""
    solved_in_files = set()
    missing_files = set()
    empty_theorem_seqs = set()
    
    for problem_id in range(1, max_problem_id + 1):
        problem_file = os.path.join(problems_dir, f"{problem_id}.json")
        
        if not os.path.exists(problem_file):
            missing_files.add(problem_id)
            continue
        
        try:
            problem_data = load_json(problem_file)
            theorem_seqs = problem_data.get("theorem_seqs", [])
            
            # 检查是否有非空的解题步骤
            if theorem_seqs and len(theorem_seqs) > 0:
                non_empty_seqs = [seq for seq in theorem_seqs if seq and str(seq).strip()]
                if non_empty_seqs:
                    solved_in_files.add(problem_id)
                else:
                    empty_theorem_seqs.add(problem_id)
            else:
                empty_theorem_seqs.add(problem_id)
        
        except Exception as e:
            print(f"读取问题 {problem_id} 时出错: {e}")
            empty_theorem_seqs.add(problem_id)
    
    return solved_in_files, missing_files, empty_theorem_seqs

def main():
    """主函数"""
    print("🔍 分析未解决的问题...")
    
    # 分析终端输出
    solved_terminal, unsolved_terminal, error_terminal = analyze_terminal_output()
    
    # 检查问题文件状态
    base_dir = Path(__file__).parent
    problems_dir = base_dir / "formalgeo7k_v2" / "problems"
    solved_files, missing_files, empty_files = check_problem_files(problems_dir, 119)
    
    print(f"\n📊 终端输出统计 (1-119题范围):")
    print(f"  ✅ 已解决: {len(solved_terminal)} 题")
    print(f"  ❌ 未解决: {len(unsolved_terminal)} 题")
    print(f"  ⚠️ 错误: {len(error_terminal)} 题")
    
    print(f"\n📁 问题文件统计 (1-119题范围):")
    print(f"  ✅ 有解题步骤: {len(solved_files)} 题")
    print(f"  📝 无解题步骤: {len(empty_files)} 题")
    print(f"  📄 文件缺失: {len(missing_files)} 题")
    
    # 找出所有未处理的问题
    all_problems = set(range(1, 120))  # 1-119
    processed_problems = solved_terminal | solved_files
    unprocessed_problems = all_problems - processed_problems
    
    print(f"\n🎯 总体统计 (1-119题):")
    print(f"  ✅ 已处理: {len(processed_problems)} 题")
    print(f"  ⏳ 未处理: {len(unprocessed_problems)} 题")
    
    # 详细列出各类问题
    if unsolved_terminal:
        print(f"\n❌ 终端显示未解决的题目 ({len(unsolved_terminal)}题):")
        print(f"  {sorted(unsolved_terminal)}")
    
    if error_terminal:
        error_in_range = error_terminal & set(range(1, 120))
        if error_in_range:
            print(f"\n⚠️ 终端显示错误的题目 ({len(error_in_range)}题):")
            print(f"  {sorted(error_in_range)}")
    
    if missing_files:
        print(f"\n📄 缺失文件的题目 ({len(missing_files)}题):")
        print(f"  {sorted(missing_files)}")
    
    if unprocessed_problems:
        print(f"\n🔄 完全未处理的题目 ({len(unprocessed_problems)}题):")
        unprocessed_list = sorted(list(unprocessed_problems))
        print(f"  {unprocessed_list}")
        
        # 按范围显示
        print(f"\n📋 未处理题目详细列表:")
        for i in range(0, len(unprocessed_list), 10):
            chunk = unprocessed_list[i:i+10]
            print(f"  {chunk}")
    
    # 生成建议
    print(f"\n💡 建议:")
    if unprocessed_problems:
        print(f"  - 使用 enhanced_search.py 继续处理这 {len(unprocessed_problems)} 个未解决的问题")
        print(f"  - 可以先尝试处理较简单的问题，如: {sorted(list(unprocessed_problems))[:5]}")
    
    if error_terminal:
        error_in_range = error_terminal & set(range(1, 120))
        if error_in_range:
            print(f"  - 有 {len(error_in_range)} 个问题出现错误，可能需要检查问题定义或定理库")
    
    if missing_files:
        print(f"  - 有 {len(missing_files)} 个问题文件缺失，需要补充")

if __name__ == "__main__":
    main()
