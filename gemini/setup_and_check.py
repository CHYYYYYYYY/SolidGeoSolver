#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查和设置脚本
自动创建必要的目录和检查配置
"""

import os
import sys
import json

def check_and_create_dirs():
    """检查并创建必要的目录"""
    print("="*60)
    print("检查和创建目录...")
    print("="*60)
    
    required_dirs = [
        "gemini/data/new_problems",
        "gemini/data/examples",
        "gemini/data/chatgpt_output",
        "gemini/data/deepseek_output",
        "gemini/data/generated_output",
        "gemini/evaluation_results",
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"[+] 创建目录: {dir_path}")
        else:
            print(f"[OK] 目录已存在: {dir_path}")

def check_ground_truth():
    """检查ground truth目录"""
    print("\n" + "="*60)
    print("检查Ground Truth数据...")
    print("="*60)
    
    possible_paths = [
        "src/fgps/formalgeo7k_v2/problems",
        "../src/fgps/formalgeo7k_v2/problems",
        "formalgeo/datasets/formalgeo7k_v2/problems",
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            json_files = [f for f in os.listdir(path) if f.endswith('.json')]
            print(f"[OK] 找到Ground Truth: {path}")
            print(f"  包含 {len(json_files)} 个问题文件")
            found = True
            return path
    
    if not found:
        print("[X] 未找到Ground Truth目录")
        print("  可能的位置:")
        for path in possible_paths:
            print(f"    - {path}")
        return None

def check_input_problems():
    """检查输入问题"""
    print("\n" + "="*60)
    print("检查输入问题...")
    print("="*60)
    
    input_dir = "gemini/data/new_problems"
    
    if not os.path.exists(input_dir):
        print(f"[X] 输入目录不存在: {input_dir}")
        return False
    
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    if len(json_files) == 0:
        print(f"[X] 输入目录为空: {input_dir}")
        print("\n建议:")
        print("1. 如果要测试，需要先准备输入数据")
        print("2. 可以从 gemini/data/generated_output 复制一些文件作为测试")
        return False
    
    print(f"[OK] 找到 {len(json_files)} 个输入问题")
    
    # 检查第一个文件的格式
    first_file = os.path.join(input_dir, json_files[0])
    try:
        with open(first_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_fields = ['problem_text_en', 'problem_img']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            print(f"[!] 文件格式可能不正确，缺少字段: {missing}")
        else:
            print(f"[OK] 文件格式正确")
        
        return True
    except Exception as e:
        print(f"[!] 无法读取文件 {first_file}: {e}")
        return False

def check_api_keys():
    """检查API密钥配置"""
    print("\n" + "="*60)
    print("检查API配置...")
    print("="*60)
    
    scripts = {
        "ChatGPT": "gemini/chatgpt_pro.py",
        "DeepSeek": "gemini/deepseek_pro.py",
        "Gemini": "gemini/gemini2.5_pro.py"
    }
    
    for model, script in scripts.items():
        if os.path.exists(script):
            print(f"[OK] {model} 脚本存在: {script}")
        else:
            print(f"[X] {model} 脚本不存在: {script}")

def create_sample_problem():
    """创建示例问题文件"""
    print("\n" + "="*60)
    print("创建示例问题...")
    print("="*60)
    
    sample_problem = {
        "problem_id": 999,
        "problem_text_en": "As shown in the figure, O is the center of a sphere with radius 5. What is the volume of the sphere?",
        "problem_img": ["images/999.png"],
        "problem_answer": "523.6"
    }
    
    output_path = "gemini/data/new_problems/999_sample.json"
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_problem, f, indent=2, ensure_ascii=False)
        print(f"[+] 创建示例问题: {output_path}")
        print("  注意: 这个示例没有实际图片，仅用于测试脚本结构")
        return True
    except Exception as e:
        print(f"[X] 创建示例失败: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("ChatGPT & DeepSeek 环境检查和设置")
    print("="*60 + "\n")
    
    # 1. 创建目录
    check_and_create_dirs()
    
    # 2. 检查ground truth
    gt_path = check_ground_truth()
    
    # 3. 检查输入问题
    has_input = check_input_problems()
    
    # 4. 如果没有输入，创建示例
    if not has_input:
        print("\n是否创建示例问题用于测试? (y/n)")
        # 自动创建
        create_sample_problem()
    
    # 5. 检查API配置
    check_api_keys()
    
    # 总结
    print("\n" + "="*60)
    print("检查完成！")
    print("="*60)
    
    if gt_path:
        print(f"\n[OK] Ground Truth路径: {gt_path}")
        print("\n下一步:")
        if has_input or os.path.exists("gemini/data/new_problems/999_sample.json"):
            print("1. 运行测试: python gemini/test_api_connection.py")
            print("2. 运行单个模型: python gemini/chatgpt_pro.py")
            print("3. 或跳过生成直接评估现有输出:")
            print("   python gemini/run_all_models.py --models all --skip-generation")
        else:
            print("1. 准备输入数据到 gemini/data/new_problems/")
            print("2. 或使用现有的generated_output进行评估")
    else:
        print("\n[!] 警告: 未找到Ground Truth数据")
        print("  如果只想测试生成功能，可以跳过评估步骤")
        print("  运行: python gemini/chatgpt_pro.py")
    
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()

