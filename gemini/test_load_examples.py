# -*- coding: utf-8 -*-
"""测试few-shot示例加载功能"""
import sys
import os
sys.path.insert(0, 'gemini')

from chatgpt_pro import load_few_shot_examples

train_dir = "gemini/data/manual_train_set"
images_dir = "src/fgps/formalgeo7k_v2/images"

examples, count = load_few_shot_examples(train_dir, images_dir)
print(f"成功加载 {count} 个训练范例")
print(f"示例文本长度: {len(examples)} 字符")
if examples:
    print("\n前500个字符:")
    print(examples[:500])

