# -*- coding: utf-8 -*-
import json
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('chatgpt_test_results_1_357/_re_evaluated_log.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

target_ids = [29, 148, 373, 380, 206, 209, 551, 567]

for result in data:
    if result.get('problem_id') in target_ids:
        pid = result.get('problem_id')
        status = result.get('status')
        chatgpt = result.get('chatgpt_answer', '')[:60]
        standard = result.get('standard_answer', '')[:60]
        print(f"问题 {pid}: {status}")
        print(f"  ChatGPT: {chatgpt}")
        print(f"  标准: {standard}")
        print()

