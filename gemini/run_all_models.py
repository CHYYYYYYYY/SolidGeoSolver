#!/usr/bin/env python3
"""
统一运行所有模型(Gemini, ChatGPT, DeepSeek)并评估F1准确率
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# 配置路径
INPUT_PROBLEM_DIR = "gemini/data/new_problems"
FEW_SHOT_EXAMPLE_DIR = "gemini/data/examples"
GROUND_TRUTH_DIR = "src/fgps/formalgeo7k_v2/problems"  # 修正路径
PREDICATE_GDL_PATH = "gemini/predicate_GDL.json"

# 输出目录配置
OUTPUT_DIRS = {
    "gemini": "gemini/data/generated_output",
    "chatgpt": "gemini/data/chatgpt_output",
    "deepseek": "gemini/data/deepseek_output"
}

# 结果文件配置
RESULTS_DIR = "gemini/evaluation_results"
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

def run_model(model_name):
    """运行指定模型生成CDL"""
    print(f"\n{'='*80}")
    print(f"运行 {model_name.upper()} 模型...")
    print(f"{'='*80}\n")
    
    if model_name == "gemini":
        script = "gemini/gemini2.5_pro.py"
    elif model_name == "chatgpt":
        script = "gemini/chatgpt_pro.py"
    elif model_name == "deepseek":
        script = "gemini/deepseek_pro.py"
    else:
        print(f"未知模型: {model_name}")
        return False
    
    try:
        # 运行对应的脚本
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'  # 忽略编码错误
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"警告/错误输出:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"\n✓ {model_name.upper()} 运行成功!")
            return True
        else:
            print(f"\n✗ {model_name.upper()} 运行失败!")
            return False
            
    except Exception as e:
        print(f"运行 {model_name} 时出错: {e}")
        return False

def evaluate_model(model_name):
    """评估指定模型的输出"""
    print(f"\n{'='*80}")
    print(f"评估 {model_name.upper()} 模型...")
    print(f"{'='*80}\n")
    
    output_dir = OUTPUT_DIRS[model_name]
    
    if not os.path.exists(output_dir):
        print(f"错误: 输出目录不存在: {output_dir}")
        return None
    
    # 检查是否有生成的文件
    json_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and not f.startswith('_')]
    if len(json_files) == 0:
        print(f"错误: 输出目录中没有生成的JSON文件: {output_dir}")
        return None
    
    print(f"找到 {len(json_files)} 个生成的文件")
    
    try:
        # 使用evaluate_cdl进行评估
        from evaluate_cdl import GeminiCDLEvaluator
        
        # 使用合并模式和模糊匹配
        evaluator = GeminiCDLEvaluator(merge_text_image=True, fuzzy_matching=True)
        metrics = evaluator.evaluate_dataset(GROUND_TRUTH_DIR, output_dir)
        
        if not metrics:
            print(f"评估失败: {model_name}")
            return None
        
        # 打印结果
        evaluator.print_results(metrics)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f"results_{model_name}_{timestamp}.json")
        detailed_file = os.path.join(RESULTS_DIR, f"detailed_{model_name}_{timestamp}.json")
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(evaluator.detailed_results, f, indent=2, ensure_ascii=False)
        
        print("\n结果已保存:")
        print("  聚合结果: {}".format(results_file))
        print("  详细结果: {}".format(detailed_file))
        
        return metrics
        
    except Exception as e:
        print(f"评估 {model_name} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_comparison_header():
    """打印对比表格头部"""
    print("\n\n" + "="*80)
    print("所有模型性能对比")
    print("="*80 + "\n")
    print("{:<15} {:<18} {:<18} {:<18} {:<15}".format(
        '模型', 'Construction F1', 'Condition F1', 'Goal F1', 'Answer Acc'))
    print("-" * 84)

def print_model_metrics(model_name, metrics):
    """打印单个模型的指标"""
    construction_f1 = metrics.get('construction_f1', 0.0)
    condition_f1 = metrics.get('condition_f1', 0.0)
    goal_f1 = metrics.get('goal_f1', 0.0)
    answer_acc = metrics.get('answer_accuracy', 0.0)
    print("{:<15} {:<18.4f} {:<18.4f} {:<18.4f} {:<15.4f}".format(
        model_name.upper(), construction_f1, condition_f1, goal_f1, answer_acc))

def print_average_f1(all_metrics):
    """打印平均F1分数"""
    print("\n" + "-" * 84)
    print("{:<15} {:<18}".format('模型', '平均 F1'))
    print("-" * 84)
    
    for model_name, metrics in all_metrics.items():
        avg_f1 = (
            metrics.get('construction_f1', 0.0) +
            metrics.get('condition_f1', 0.0) +
            metrics.get('goal_f1', 0.0)
        ) / 3
        print("{:<15} {:<18.4f}".format(model_name.upper(), avg_f1))

def find_best_models(all_metrics, metric_names):
    """找出每个指标的最佳模型"""
    best_models = {}
    for metric in metric_names:
        best_score = -1
        best_model = None
        for model_name, metrics in all_metrics.items():
            score = metrics.get(metric, 0.0)
            if score > best_score:
                best_score = score
                best_model = model_name
        best_models[metric] = (best_model, best_score)
    return best_models

def compare_models(all_metrics):
    """比较所有模型的性能"""
    if not all_metrics:
        print("没有可比较的模型结果")
        return
    
    # 提取关键指标
    metric_names = ['construction_f1', 'condition_f1', 'goal_f1', 'answer_accuracy']
    
    # 打印对比表格
    print_comparison_header()
    for model_name, metrics in all_metrics.items():
        print_model_metrics(model_name, metrics)
    
    # 打印平均F1
    print_average_f1(all_metrics)
    
    # 找出并打印最佳模型
    print("\n" + "="*80)
    print("最佳模型:")
    print("-" * 84)
    
    best_models = find_best_models(all_metrics, metric_names)
    for metric, (best_model, best_score) in best_models.items():
        print("{:<30}: {:<15} ({:.4f})".format(metric, best_model.upper(), best_score))
    
    # 保存对比结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = os.path.join(RESULTS_DIR, "comparison_{}.json".format(timestamp))
    
    comparison_data = {
        "timestamp": timestamp,
        "all_metrics": all_metrics,
        "best_models": {k: {"model": v[0], "score": v[1]} for k, v in best_models.items()}
    }
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print("\n对比结果已保存: {}".format(comparison_file))

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='运行和评估多个模型的CDL生成性能',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--models',
        nargs='+',
        choices=['gemini', 'chatgpt', 'deepseek', 'all'],
        default=['all'],
        help='要运行的模型 (默认: all)'
    )
    parser.add_argument(
        '--skip-generation',
        action='store_true',
        help='跳过生成步骤，仅评估现有输出'
    )
    parser.add_argument(
        '--skip-evaluation',
        action='store_true',
        help='跳过评估步骤，仅生成输出'
    )
    
    args = parser.parse_args()
    
    # 确定要运行的模型
    if 'all' in args.models:
        models_to_run = ['gemini', 'chatgpt', 'deepseek']
    else:
        models_to_run = args.models
    
    print(f"将要处理的模型: {', '.join(m.upper() for m in models_to_run)}")
    
    all_metrics = {}
    
    for model in models_to_run:
        try:
            # 生成步骤
            if not args.skip_generation:
                success = run_model(model)
                if not success:
                    print("跳过 {} 的评估（生成失败）".format(model))
                    continue
            
            # 评估步骤
            if not args.skip_evaluation:
                metrics = evaluate_model(model)
                if metrics:
                    all_metrics[model] = metrics
                else:
                    print(f"跳过 {model} 的对比（评估失败）")
        
        except KeyboardInterrupt:
            print(f"\n\n用户中断，已完成的模型: {list(all_metrics.keys())}")
            break
        except Exception as e:
            print(f"\n处理 {model} 时发生错误: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 对比所有模型
    if not args.skip_evaluation and len(all_metrics) > 1:
        compare_models(all_metrics)
    
    print(f"\n\n{'='*80}")
    print("所有任务完成!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

