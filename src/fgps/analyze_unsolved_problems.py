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
25264   5       solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('A',)), ('cylinder_volume_formula_common', '1', ('A', 'B')), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
26020   6       solved  [('circle_area_formula', '1', ('P',)), ('circle_property_length_of_radius_and_diameter', '1', ('Q',)), ('circle_property_length_of_radius_and_diameter', '1', ('A',)), ('circle_area_formula', '1', ('A',)), ('cylinder_volume_formula_common', '1', ('A', 'B')), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
35772   7       solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
27484   8       solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
9764    9       solved  [('circle_area_formula', '1', ('O',)), ('cone_volume_formula_common', '1', ('O', 'P'))]
19416   10      solved  [('circle_area_formula', '1', ('O',)), ('cone_volume_formula_common', '1', ('O', 'P'))]
42200   11      solved  [('circle_property_length_of_radius_and_diameter', '1', ('O',)), ('circle_area_formula', '1', ('O',)), ('cone_volume_formula_common', '1', ('O', 'P'))]
24788   12      solved  [('circle_area_formula', '1', ('O',)), ('cone_volume_formula_common', '1', ('O', 'P'))]
20404   13      solved  [('circle_area_formula', '1', ('O',)), ('cone_volume_formula_common', '1', ('O', 'P'))]
4724    14      solved  [('sphere_volume_formula', '1', ('O',))]
3436    15      solved  [('sphere_property_length_of_radius_and_diameter', '1', ('O',)), ('sphere_volume_formula', '1', ('O',))]
21400   16      solved  [('sphere_property_length_of_radius_and_diameter', '1', ('O',)), ('sphere_volume_formula', '1', ('O',)), ('sphere_property_length_of_radius_and_diameter', '1', ('P',)), ('sphere_volume_formula', '1', ('P',))]
24236   17      solved  [('sphere_volume_formula', '1', ('O',))]
40896   18      solved  [('sphere_volume_formula', '1', ('O',))]
43360   19      solved  [('sphere_volume_formula', '1', ('O',))]
8376    20      solved  [('sphere_volume_formula', '1', ('O',))]
31676   21      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
36612   22      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
43388   23      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
43428   24      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
43052   25      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
43436   26      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
30760   27      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
43944   28      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('circle_area_formula', '1', ('A',)), ('circle_area_formula', '1', ('B',)), ('cylinder_area_formula', '1', ('A', 'B')), ('cylinder_area_formula', '1', ('P', 'Q'))]
23084   30      solved  [('sphere_area_formula', '1', ('O',))]
40568   31      solved  [('sphere_property_length_of_radius_and_diameter', '1', ('O',)), ('sphere_area_formula', '1', ('O',))]
44020   32      solved  [('sphere_area_formula', '1', ('O',))]
42428   33      solved  [('circle_area_formula', '1', ('O',))]
43688   34      solved  [('sphere_area_formula', '1', ('O',)), ('circle_area_formula', '1', ('O',))]
29764   35      solved  [('sphere_area_formula', '1', ('O',)), ('circle_area_formula', '1', ('O',))]
15344   38      solved  [('cone_area_formula', '1', ('O', 'P')), ('sphere_area_formula', '1', ('O',))]
37416   39      solved  [('sphere_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
40148   40      solved  [('sphere_area_formula', '1', ('A',))]
43472   41      solved  [('sphere_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('Q',)), ('cylinder_area_formula', '1', ('P', 'Q'))]
34152   29      unsolved        None
25452   49      error   TypeError("unsupported operand type(s) for ^: 'Symbol' and 'Add'")
7216    52      solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
42072   53      solved  [('circle_property_length_of_radius_and_diameter', '1', ('P',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
6588    54      solved  [('circle_property_length_of_radius_and_diameter', '1', ('P',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
26760   55      solved  [('circle_property_length_of_radius_and_diameter', '1', ('P',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
31884   56      solved  [('circle_property_length_of_radius_and_diameter', '1', ('P',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
27936   57      solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
43856   36      solved  [('circle_area_formula', '1', ('Q',)), ('cuboid_area_formula', '1', ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'))]
7224    58      solved  [('circle_area_formula', '1', ('P',)), ('circle_area_formula', '1', ('A',)), ('cylinder_volume_formula_common', '1', ('A', 'B')), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
34696   59      solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
18040   60      solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
37264   61      solved  [('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q'))]
38404   62      solved  [('circle_area_formula', '1', ('A',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q')), ('cylinder_volume_formula_common', '1', ('A', 'B'))]
3564    63      solved  [('circle_area_formula', '1', ('A',)), ('circle_property_length_of_radius_and_diameter', '1', ('C',)), ('circle_area_formula', '1', ('C',)), ('circle_area_formula', '1', ('P',)), ('cylinder_volume_formula_common', '1', ('P', 'Q')), ('cylinder_volume_formula_common', '1', ('A', 'B')), ('cylinder_volume_formula_common', '1', ('C', 'D'))]
16300   70      error   ValueError('not enough values to unpack (expected 2, got 1)')
28240   71      error   ValueError('not enough values to unpack (expected 2, got 1)')
42820   73      error   KeyError('type')
35392   74      error   IndexError('string index out of range')
8468    75      error   KeyError('type')
33120   76      error   KeyError('type')
42688   77      error   KeyError('type')
29140   78      error   KeyError('type')
25084   79      error   KeyError('type')
14688   65      solved  [('cube_area_formula', '1', ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'))]
35084   80      error   KeyError('type')
9764    81      error   KeyError('type')
16808   82      error   KeyError('type')
43768   83      error   KeyError('type')
21540   84      unsolved        None
18056   85      solved  [('sphere_volume_formula', '1', ('A',)), ('sphere_volume_formula', '1', ('B',))]
37048   86      solved  []
24464   87      error   SyntaxError('invalid syntax', ('<string>', 1, 14, "Integer (12 )Symbol ('x' )^Integer (2 )+Integer (144 )Symbol ('x' )+Integer (384 )", 1, 20))
33376   88      error   KeyError('type')
36328   89      error   Exception('Operator 3*pi*x* not defined, please check your expression.')
21332   90      error   KeyError('type')
23572   91      unsolved        None
43928   96      error   Exception("Predicate 'RightTriangularPyramid' not defined in current predicate GDL.")
17704   97      error   FileNotFoundError(2, 'No such file or directory')
42248   98      error   FileNotFoundError(2, 'No such file or directory')
17160   99      error   FileNotFoundError(2, 'No such file or directory')
43364   100     error   FileNotFoundError(2, 'No such file or directory')
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
