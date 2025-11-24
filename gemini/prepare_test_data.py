# -*- coding: utf-8 -*-
"""
准备测试数据脚本：从原始问题目录复制1-700题目的JSON文件到测试目录
"""
import os
import shutil
import json
from tqdm import tqdm

def prepare_test_data(source_dir, target_dir, start_id=1, end_id=700):
    """
    从源目录复制指定范围的JSON文件到目标目录
    
    Args:
        source_dir: 源目录（原始问题文件目录）
        target_dir: 目标目录（测试数据目录）
        start_id: 起始问题ID
        end_id: 结束问题ID
    """
    if not os.path.exists(source_dir):
        print(f"错误: 源目录不存在: {source_dir}")
        return
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"已创建目标目录: {target_dir}")
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"准备复制问题 {start_id} 到 {end_id} 的JSON文件...")
    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_dir}")
    print()
    
    for problem_id in tqdm(range(start_id, end_id + 1), desc="复制进度"):
        source_file = os.path.join(source_dir, f"{problem_id}.json")
        target_file = os.path.join(target_dir, f"{problem_id}.json")
        
        if not os.path.exists(source_file):
            skipped_count += 1
            continue
        
        try:
            # 读取源文件，验证JSON格式
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 确保文件包含必要的字段
            if 'problem_text_en' not in data or not data.get('problem_text_en'):
                skipped_count += 1
                continue
            
            # 复制文件
            shutil.copy2(source_file, target_file)
            copied_count += 1
            
        except json.JSONDecodeError as e:
            print(f"警告: 问题 {problem_id} 的JSON格式错误: {e}")
            error_count += 1
        except Exception as e:
            print(f"警告: 复制问题 {problem_id} 时出错: {e}")
            error_count += 1
    
    print()
    print("=" * 60)
    print("复制完成！")
    print(f"成功复制: {copied_count} 个文件")
    print(f"跳过（文件不存在或缺少必要字段）: {skipped_count} 个文件")
    print(f"错误: {error_count} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    # 配置路径
    SOURCE_DIR = "src/fgps/formalgeo7k_v2/problems"  # 原始问题文件目录
    TARGET_DIR = "gemoni/data/new_problems"  # 测试数据目录
    START_ID = 1
    END_ID = 700
    
    prepare_test_data(SOURCE_DIR, TARGET_DIR, START_ID, END_ID)

