#!/usr/bin/env python3
"""
Gemini CDL Evaluation Script

This script evaluates Gemini-generated CDL data against ground truth.
It reads JSON files from directories and compares construction_cdl, text_cdl, image_cdl, and goal_cdl.

Usage:
    python evaluate_cdl.py --gt_dir <ground_truth_dir> --pred_dir <gemini_output_dir> [--output_file results.json]
    
Example:
    python evaluate_cdl.py --gt_dir ../src/fgps/formalgeo7k_v2/problems --pred_dir data/generated_output --output_file results.json
"""

import json
import argparse
import re
from typing import Dict, List, Tuple
from collections import defaultdict
from pathlib import Path
import os


class GeminiCDLEvaluator:
    def __init__(self, merge_text_image=False, fuzzy_matching=False):
        """
        初始化评估器
        
        Args:
            merge_text_image: 是否合并text_cdl和image_cdl进行评估
                             True: 更宽松，关注信息是否提取到（推荐）
                             False: 严格区分信息来源
            fuzzy_matching: 是否使用模糊匹配（超级宽松模式）
                           True: 部分匹配给分（谓词名相同0.5分，数值相同0.3分）
                           False: 只有完全匹配才给分
        """
        self.metrics = defaultdict(list)
        self.detailed_results = []
        self.merge_text_image = merge_text_image
        self.fuzzy_matching = fuzzy_matching
        
    def normalize_cdl_element(self, element: str) -> str:
        """
        Normalize CDL elements for comparison with lenient matching.
        - Removes all spaces
        - Replaces all variables (but keeps numbers)
        - Standardizes to ignore variable naming and parameter count differences
        """
        # Remove all spaces
        normalized = element.strip().replace(' ', '')
        
        # Strategy: Extract predicate structure and numeric values only
        # Replace all variables with a generic placeholder
        # This ignores both variable names and parameter counts
        
        def process_recursively(text):
            """Recursively process nested function calls"""
            # Base case: if no parentheses, just replace variables
            if '(' not in text:
                # Keep numbers, replace variables
                if re.match(r'^\d+\.?\d*$', text):
                    return text
                else:
                    return re.sub(r'\b[A-Z][A-Z0-9]*\b', '_V_', text)
            
            # Process from inside out (deepest nesting first)
            def replace_innermost(match):
                content = match.group(1)
                # Split by comma
                parts = content.split(',')
                processed_parts = []
                
                for part in parts:
                    part = part.strip()
                    # If it's a number, keep it
                    if re.match(r'^\d+\.?\d*$', part):
                        processed_parts.append(part)
                    # If it contains nested functions, process recursively
                    elif '(' in part:
                        processed_parts.append(process_recursively(part))
                    # Otherwise it's a variable, replace
                    else:
                        processed_parts.append('_V_')
                
                # If all parts are variables, normalize to single _V_
                # This makes (O) equivalent to (O,P)
                if all(p == '_V_' for p in processed_parts):
                    return '(_V_)'
                else:
                    return '(' + ','.join(processed_parts) + ')'
            
            # Replace innermost parentheses first
            while True:
                # Find and replace innermost parentheses (those without nested ones)
                new_text = re.sub(r'\(([^()]+)\)', replace_innermost, text)
                if new_text == text:
                    break
                text = new_text
            
            return text
        
        # Process the entire expression
        normalized = process_recursively(normalized)
        
        return normalized
    
    def calculate_partial_match_score(self, pred_elem: str, gt_elem: str) -> float:
        """
        计算两个CDL元素的部分匹配分数
        
        Returns:
            1.0: 完全匹配
            0.8: 谓词名+主要数值都匹配
            0.5: 只有谓词名匹配
            0.3: 只有数值匹配
            0.0: 完全不匹配
        """
        import re
        
        # 先检查完全匹配
        if pred_elem == gt_elem:
            return 1.0
        
        # 提取谓词名
        pred_predicate = pred_elem.split('(')[0]
        gt_predicate = gt_elem.split('(')[0]
        
        # 提取数值
        pred_numbers = set(re.findall(r'\d+\.?\d*', pred_elem))
        gt_numbers = set(re.findall(r'\d+\.?\d*', gt_elem))
        
        predicate_match = pred_predicate == gt_predicate
        number_match = len(pred_numbers & gt_numbers) > 0
        
        if predicate_match and number_match:
            # 谓词名和数值都匹配
            return 0.8
        elif predicate_match:
            # 只有谓词名匹配
            return 0.5
        elif number_match:
            # 只有数值匹配
            return 0.3
        else:
            return 0.0
    
    def calculate_set_metrics(self, predicted: List[str], ground_truth: List[str]) -> Dict[str, float]:
        """Calculate all metrics including Jaccard similarity for list-based CDLs."""
        pred_set = {self.normalize_cdl_element(elem) for elem in predicted}
        gt_set = {self.normalize_cdl_element(elem) for elem in ground_truth}
        
        if len(gt_set) == 0 and len(pred_set) == 0:
            return {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'exact_match': 1.0, 'jaccard': 1.0}
        
        if len(gt_set) == 0:
            return {'precision': 0.0, 'recall': 1.0, 'f1': 0.0, 'exact_match': 0.0, 'jaccard': 0.0}
        
        if len(pred_set) == 0:
            return {'precision': 1.0, 'recall': 0.0, 'f1': 0.0, 'exact_match': 0.0, 'jaccard': 0.0}
        
        if self.fuzzy_matching:
            # 模糊匹配模式：使用部分匹配分数
            # 对每个预测，找到最佳匹配的标准答案
            pred_scores = []
            for pred_norm in pred_set:
                # 找原始pred元素
                pred_orig = [p for p in predicted if self.normalize_cdl_element(p) == pred_norm][0]
                best_score = 0.0
                for gt_norm in gt_set:
                    gt_orig = [g for g in ground_truth if self.normalize_cdl_element(g) == gt_norm][0]
                    score = self.calculate_partial_match_score(pred_norm, gt_norm)
                    if score > best_score:
                        best_score = score
                pred_scores.append(best_score)
            
            # 对每个标准答案，找到最佳匹配的预测
            gt_scores = []
            for gt_norm in gt_set:
                gt_orig = [g for g in ground_truth if self.normalize_cdl_element(g) == gt_norm][0]
                best_score = 0.0
                for pred_norm in pred_set:
                    pred_orig = [p for p in predicted if self.normalize_cdl_element(p) == pred_norm][0]
                    score = self.calculate_partial_match_score(pred_norm, gt_norm)
                    if score > best_score:
                        best_score = score
                gt_scores.append(best_score)
            
            precision = sum(pred_scores) / len(pred_scores) if pred_scores else 0.0
            recall = sum(gt_scores) / len(gt_scores) if gt_scores else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            # Jaccard 使用加权方式
            intersection_score = sum(pred_scores)  # 或者用平均
            union_score = len(pred_set) + len(gt_set) - intersection_score
            jaccard = intersection_score / union_score if union_score > 0 else 0.0
            
            exact_match = 1.0 if pred_set == gt_set else 0.0
            
            return {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'exact_match': exact_match,
                'jaccard': jaccard
            }
        else:
            # 严格匹配模式（当前模式）
            intersection = pred_set & gt_set
            union = pred_set | gt_set
            
            precision = len(intersection) / len(pred_set) if len(pred_set) > 0 else 0.0
            recall = len(intersection) / len(gt_set) if len(gt_set) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            jaccard = len(intersection) / len(union) if len(union) > 0 else 0.0
            exact_match = 1.0 if pred_set == gt_set else 0.0
            
            return {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'exact_match': exact_match,
                'jaccard': jaccard
            }
    
    def calculate_string_metrics(self, predicted: str, ground_truth: str) -> Dict[str, float]:
        """Calculate metrics for goal_cdl (string comparison)."""
        pred_normalized = self.normalize_cdl_element(predicted)
        gt_normalized = self.normalize_cdl_element(ground_truth)
        
        exact_match = 1.0 if pred_normalized == gt_normalized else 0.0
        
        # For goal CDL, we can also treat it as a set with one element
        pred_set = {pred_normalized} if pred_normalized else set()
        gt_set = {gt_normalized} if gt_normalized else set()
        
        if len(gt_set) == 0 and len(pred_set) == 0:
            return {
                'precision': 1.0, 
                'recall': 1.0, 
                'f1': 1.0, 
                'exact_match': 1.0, 
                'jaccard': 1.0
            }
        
        if len(gt_set) == 0:
            return {
                'precision': 0.0, 
                'recall': 1.0, 
                'f1': 0.0, 
                'exact_match': 0.0, 
                'jaccard': 0.0
            }
        
        if len(pred_set) == 0:
            return {
                'precision': 1.0, 
                'recall': 0.0, 
                'f1': 0.0, 
                'exact_match': 0.0, 
                'jaccard': 0.0
            }
        
        intersection = pred_set & gt_set
        union = pred_set | gt_set
        
        precision = len(intersection) / len(pred_set) if len(pred_set) > 0 else 0.0
        recall = len(intersection) / len(gt_set) if len(gt_set) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        jaccard = len(intersection) / len(union) if len(union) > 0 else 0.0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'exact_match': exact_match,
            'jaccard': jaccard
        }
    
    def compare_answers(self, pred_answer: str, gt_answer: str) -> bool:
        """
        比较两个答案是否相等
        支持多种格式：纯数字、带单位、数学表达式等
        """
        import re
        
        def normalize_answer(ans: str) -> str:
            """标准化答案格式"""
            if not ans:
                return ""
            
            # 转为字符串并去除空格
            ans = str(ans).strip().replace(' ', '')
            
            # 去除单位和文字（如 "diameter = 10 m" -> "10"）
            # 提取数字部分
            numbers = re.findall(r'[-+]?\d*\.?\d+', ans)
            if numbers:
                # 取第一个数字
                return numbers[0]
            
            return ans.lower()
        
        pred_norm = normalize_answer(pred_answer)
        gt_norm = normalize_answer(gt_answer)
        
        if not pred_norm or not gt_norm:
            return False
        
        try:
            # 尝试作为数值比较（容忍小数精度差异）
            pred_val = float(pred_norm)
            gt_val = float(gt_norm)
            # 相对误差小于 0.1% 认为相等
            if gt_val != 0:
                return abs(pred_val - gt_val) / abs(gt_val) < 0.001
            else:
                return abs(pred_val - gt_val) < 0.001
        except (ValueError, TypeError):
            # 如果不是数字，直接字符串比较
            return pred_norm == gt_norm
    
    def load_json_files(self, directory: str) -> Dict[int, Dict]:
        """Load all JSON files from a directory, indexed by problem_id from filename."""
        data_dict = {}
        
        if not os.path.exists(directory):
            print(f"Warning: Directory not found: {directory}")
            return data_dict
        
        json_files = [f for f in os.listdir(directory) if f.endswith('.json') and not f.startswith('_')]
        
        for json_file in json_files:
            json_path = os.path.join(directory, json_file)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Prioritize extracting problem_id from filename (more reliable)
                try:
                    problem_id = int(json_file.replace('.json', ''))
                except ValueError:
                    # Fallback: try to get problem_id from JSON content
                    problem_id = data.get('problem_id')
                    if problem_id is None:
                        print(f"Warning: Could not determine problem_id for {json_file}, skipping.")
                        continue
                
                data_dict[problem_id] = data
                
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse {json_file}: {e}")
                continue
            except Exception as e:
                print(f"Warning: Error reading {json_file}: {e}")
                continue
        
        return data_dict
    
    def evaluate_dataset(self, gt_dir: str, pred_dir: str) -> Dict[str, float]:
        """Evaluate the entire dataset by comparing JSON files."""
        print(f"Loading ground truth files from: {gt_dir}")
        gt_data = self.load_json_files(gt_dir)
        
        print(f"Loading prediction files from: {pred_dir}")
        pred_data = self.load_json_files(pred_dir)
        
        if len(gt_data) == 0:
            print(f"Error: No ground truth files found in {gt_dir}")
            return {}
        
        if len(pred_data) == 0:
            print(f"Error: No prediction files found in {pred_dir}")
            return {}
        
        # Find common problem_ids
        common_ids = set(gt_data.keys()) & set(pred_data.keys())
        if len(common_ids) == 0:
            print("Error: No common problem_ids found between ground truth and predictions.")
            print(f"GT problem_ids: {sorted(list(gt_data.keys()))[:10]}...")
            print(f"Pred problem_ids: {sorted(list(pred_data.keys()))[:10]}...")
            return {}
        
        print(f"Found {len(common_ids)} common problems to evaluate.")
        
        all_metrics = defaultdict(list)
        self.detailed_results = []
        
        for problem_id in sorted(common_ids):
            gt_item = gt_data[problem_id]
            pred_item = pred_data[problem_id]
            
            # Extract CDL fields
            gt_construction = gt_item.get('construction_cdl', [])
            gt_text = gt_item.get('text_cdl', [])
            gt_image = gt_item.get('image_cdl', [])
            gt_goal = gt_item.get('goal_cdl', '')
            gt_answer = gt_item.get('problem_answer', '')
            
            pred_construction = pred_item.get('construction_cdl', [])
            pred_text = pred_item.get('text_cdl', [])
            pred_image = pred_item.get('image_cdl', [])
            pred_goal = pred_item.get('goal_cdl', '')
            pred_answer = pred_item.get('problem_answer', '')
            
            # Ensure lists are lists
            if not isinstance(gt_construction, list):
                gt_construction = []
            if not isinstance(gt_text, list):
                gt_text = []
            if not isinstance(gt_image, list):
                gt_image = []
            if not isinstance(pred_construction, list):
                pred_construction = []
            if not isinstance(pred_text, list):
                pred_text = []
            if not isinstance(pred_image, list):
                pred_image = []
            
            # Ensure goal_cdl is string
            if not isinstance(gt_goal, str):
                gt_goal = str(gt_goal) if gt_goal else ''
            if not isinstance(pred_goal, str):
                pred_goal = str(pred_goal) if pred_goal else ''
            
            # Calculate metrics for each CDL type
            construction_metrics = self.calculate_set_metrics(pred_construction, gt_construction)
            goal_metrics = self.calculate_string_metrics(pred_goal, gt_goal)
            
            # 评估答案正确性
            answer_correct = 1.0 if self.compare_answers(pred_answer, gt_answer) else 0.0
            all_metrics["answer_accuracy"].append(answer_correct)
            
            if self.merge_text_image:
                # 合并模式：将text_cdl和image_cdl合并评估
                pred_combined = pred_text + pred_image
                gt_combined = gt_text + gt_image
                combined_metrics = self.calculate_set_metrics(pred_combined, gt_combined)
                
                # 仍保留分开的指标用于详细分析
                text_metrics = self.calculate_set_metrics(pred_text, gt_text)
                image_metrics = self.calculate_set_metrics(pred_image, gt_image)
                
                # Store合并后的指标作为主要指标
                for metric_name in ['precision', 'recall', 'f1', 'exact_match', 'jaccard']:
                    all_metrics[f"construction_{metric_name}"].append(construction_metrics[metric_name])
                    all_metrics[f"condition_{metric_name}"].append(combined_metrics[metric_name])  # 合并为condition
                    all_metrics[f"goal_{metric_name}"].append(goal_metrics[metric_name])
            else:
                # 分开模式：严格区分text和image
                text_metrics = self.calculate_set_metrics(pred_text, gt_text)
                image_metrics = self.calculate_set_metrics(pred_image, gt_image)
                
                # Store metrics
                for metric_name in ['precision', 'recall', 'f1', 'exact_match', 'jaccard']:
                    all_metrics[f"construction_{metric_name}"].append(construction_metrics[metric_name])
                    all_metrics[f"text_{metric_name}"].append(text_metrics[metric_name])
                    all_metrics[f"image_{metric_name}"].append(image_metrics[metric_name])
                    all_metrics[f"goal_{metric_name}"].append(goal_metrics[metric_name])
            
            # Store detailed result
            self.detailed_results.append({
                'problem_id': problem_id,
                'construction': {
                    'pred': pred_construction,
                    'gt': gt_construction,
                    'metrics': construction_metrics
                },
                'text': {
                    'pred': pred_text,
                    'gt': gt_text,
                    'metrics': text_metrics
                },
                'image': {
                    'pred': pred_image,
                    'gt': gt_image,
                    'metrics': image_metrics
                },
                'goal': {
                    'pred': pred_goal,
                    'gt': gt_goal,
                    'metrics': goal_metrics
                },
                'answer': {
                    'pred': pred_answer,
                    'gt': gt_answer,
                    'correct': answer_correct == 1.0
                }
            })
        
        # Calculate average metrics
        avg_metrics = {}
        for metric_name, values in all_metrics.items():
            avg_metrics[metric_name] = sum(values) / len(values) if len(values) > 0 else 0.0
        
        return avg_metrics
    
    def print_results(self, metrics: Dict[str, float]):
        """Print comprehensive evaluation results."""
        print("\n" + "="*80)
        print("GEMINI CDL EVALUATION RESULTS")
        if self.merge_text_image:
            print("(模式: 合并text+image CDL评估)")
        else:
            print("(模式: 分开评估text和image CDL)")
        if self.fuzzy_matching:
            print("(匹配: 模糊匹配 - 部分匹配也给分)")
        else:
            print("(匹配: 严格匹配 - 只有完全相同才给分)")
        print("="*80)
        
        if self.merge_text_image:
            cdl_types = ['construction', 'condition', 'goal']
        else:
            cdl_types = ['construction', 'text', 'image', 'goal']
        
        # Individual CDL type metrics
        for cdl_type in cdl_types:
            print(f"\n{cdl_type.upper()} CDL Metrics:")
            print("-" * 40)
            
            precision = metrics.get(f"{cdl_type}_precision", 0.0)
            recall = metrics.get(f"{cdl_type}_recall", 0.0)
            f1 = metrics.get(f"{cdl_type}_f1", 0.0)
            exact_match = metrics.get(f"{cdl_type}_exact_match", 0.0)
            jaccard = metrics.get(f"{cdl_type}_jaccard", 0.0)
            
            print(f"Precision:  {precision:.4f}")
            print(f"Recall:     {recall:.4f}")
            print(f"F1 Score:   {f1:.4f}")
            print(f"Exact Match: {exact_match:.4f}")
            print(f"Jaccard:    {jaccard:.4f}")
        
        # Overall metrics
        print("\nOVERALL METRICS:")
        print("-" * 40)
        
        overall_precision = sum(metrics.get(f"{cdl_type}_precision", 0.0) for cdl_type in cdl_types) / len(cdl_types)
        overall_recall = sum(metrics.get(f"{cdl_type}_recall", 0.0) for cdl_type in cdl_types) / len(cdl_types)
        overall_f1 = sum(metrics.get(f"{cdl_type}_f1", 0.0) for cdl_type in cdl_types) / len(cdl_types)
        overall_exact_match = sum(metrics.get(f"{cdl_type}_exact_match", 0.0) for cdl_type in cdl_types) / len(cdl_types)
        overall_jaccard = sum(metrics.get(f"{cdl_type}_jaccard", 0.0) for cdl_type in cdl_types) / len(cdl_types)
        
        print(f"Overall Precision:  {overall_precision:.4f}")
        print(f"Overall Recall:     {overall_recall:.4f}")
        print(f"Overall F1 Score:   {overall_f1:.4f}")
        print(f"Overall Exact Match: {overall_exact_match:.4f}")
        print(f"Overall Jaccard:    {overall_jaccard:.4f}")
        
        # Performance ranking
        print("\nPERFORMANCE RANKING BY F1 SCORE:")
        print("-" * 50)
        f1_scores = [(cdl_type, metrics.get(f"{cdl_type}_f1", 0)) for cdl_type in cdl_types]
        f1_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (cdl_type, f1) in enumerate(f1_scores, 1):
            print(f"{i}. {cdl_type.upper()}: {f1:.4f}")
        
        print("\nPERFORMANCE RANKING BY JACCARD SIMILARITY:")
        print("-" * 50)
        jaccard_scores = [(cdl_type, metrics.get(f"{cdl_type}_jaccard", 0)) for cdl_type in cdl_types]
        jaccard_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (cdl_type, jaccard) in enumerate(jaccard_scores, 1):
            print(f"{i}. {cdl_type.upper()}: {jaccard:.4f}")
        
        # Key insights
        # Answer Accuracy
        answer_acc = metrics.get("answer_accuracy", 0.0)
        print("\nANSWER ACCURACY:")
        print("-" * 40)
        print(f"Correct Answers: {answer_acc:.2%}")
        
        print("\nKEY INSIGHTS:")
        print("-" * 50)
        
        construction_f1 = metrics.get("construction_f1", 0)
        if self.merge_text_image:
            condition_f1 = metrics.get("condition_f1", 0)
        else:
            text_f1 = metrics.get("text_f1", 0)
            image_f1 = metrics.get("image_f1", 0)
        goal_f1 = metrics.get("goal_f1", 0)
        
        if construction_f1 < 0.7:
            print("- Construction CDL shows lower performance - most challenging type")
        
        if self.merge_text_image:
            if condition_f1 > 0.7:
                print("- Condition CDL shows good performance - extracts geometric conditions well")
            elif condition_f1 > 0.5:
                print("- Condition CDL shows moderate performance")
        else:
            if text_f1 > 0.95:
                print("- Text CDL shows excellent performance - handles textual constraints well")
            if image_f1 > 0.95:
                print("- Image CDL shows excellent performance - extracts visual information accurately")
        
        if goal_f1 > 0.95:
            print("- Goal CDL shows excellent performance - identifies goals accurately")
        elif goal_f1 > 0.4:
            print("- Goal CDL shows moderate performance")
        
        if answer_acc > 0.8:
            print("- Answer accuracy is excellent (>80%)")
        elif answer_acc > 0.5:
            print("- Answer accuracy is good (50-80%)")
        else:
            print("- Answer accuracy needs improvement (<50%)")
        
        # Overall assessment
        if overall_f1 > 0.85:
            print("- Overall CDL performance is strong (>85% F1)")
        elif overall_f1 > 0.7:
            print("- Overall CDL performance is good (70-85% F1)")
        else:
            print("- Overall CDL performance needs improvement (<70% F1)")
        
        if overall_jaccard > 0.8:
            print("- Overall Jaccard similarity is good (>80%)")
        else:
            print("- Overall Jaccard similarity needs improvement (<80%)")
        
        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate Gemini-generated CDL data against ground truth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python evaluate_cdl.py --gt_dir ../src/fgps/formalgeo7k_v2/problems --pred_dir data/generated_output
  
  # Save results to file
  python evaluate_cdl.py --gt_dir ../src/fgps/formalgeo7k_v2/problems --pred_dir data/generated_output --output_file results.json
        """
    )
    parser.add_argument(
        '--gt_dir', 
        type=str, 
        required=True, 
        help='Directory containing ground truth JSON files (e.g., ../src/fgps/formalgeo7k_v2/problems)'
    )
    parser.add_argument(
        '--pred_dir', 
        type=str, 
        required=True, 
        help='Directory containing Gemini-generated JSON files (e.g., data/generated_output)'
    )
    parser.add_argument(
        '--output_file', 
        type=str, 
        help='Path to save detailed results JSON file (optional)'
    )
    parser.add_argument(
        '--detailed_output',
        type=str,
        help='Path to save detailed per-problem results JSON file (optional)'
    )
    
    args = parser.parse_args()
    
    # Validate input directories
    if not Path(args.gt_dir).exists():
        print(f"Error: Ground truth directory not found: {args.gt_dir}")
        return
    
    if not Path(args.pred_dir).exists():
        print(f"Error: Prediction directory not found: {args.pred_dir}")
        return
    
    # Initialize evaluator (默认使用合并模式 + 模糊匹配)
    evaluator = GeminiCDLEvaluator(merge_text_image=True, fuzzy_matching=True)
    
    # Run evaluation
    print("Starting Gemini CDL evaluation...")
    print(f"评估模式: {'合并text+image CDL (推荐)' if evaluator.merge_text_image else '分开评估text和image'}")
    print(f"匹配策略: {'模糊匹配 (超级宽松)' if evaluator.fuzzy_matching else '严格匹配'}")
    metrics = evaluator.evaluate_dataset(args.gt_dir, args.pred_dir)
    
    if not metrics:
        print("Evaluation failed. Please check the error messages above.")
        return
    
    # Print results
    evaluator.print_results(metrics)
    
    # Save aggregated results if output file specified
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
        print(f"\nAggregated results saved to: {args.output_file}")
    
    # Save detailed results if specified
    if args.detailed_output:
        with open(args.detailed_output, 'w', encoding='utf-8') as f:
            json.dump(evaluator.detailed_results, f, indent=2, ensure_ascii=False)
        print(f"Detailed per-problem results saved to: {args.detailed_output}")


if __name__ == "__main__":
    main()
