#!/usr/bin/env python3
"""
DeepSeek CDL Generation Script
基于Gemini实现改造,使用DeepSeek API生成几何问题的CDL表示
"""

from openai import OpenAI
import PIL.Image
import os
import json
import time
import base64
from io import BytesIO
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- 配置 ---
DEEPSEEK_API_KEY = "sk-zjNMg4BgRLaUy2LqaGGlggpvNcnSWzo3ejIosJGrZE92eNdX"
DEEPSEEK_API_BASE = "https://aicanapi.com/v1"
# 使用GPT-4o-mini作为备用（支持视觉且便宜）
DEEPSEEK_MODEL = "gpt-4o-mini"  # 使用支持视觉的模型

if not DEEPSEEK_API_KEY:
    raise ValueError("API密钥不能为空")

# 初始化OpenAI兼容客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_BASE
)

# --- 1. 使用Pydantic定义严格的JSON输出结构 (Schema) ---
# 完整Schema（用于最终输出）
class ProblemSchema(BaseModel):
    problem_id: int = Field(default=0, description="问题的唯一标识符")
    annotation: str = Field(default="", description="标注信息")
    source: str = Field(default="SolidGeo", description="问题的来源")
    problem_text_en: str = Field(default="", description="问题的完整英文自然语言描述")
    construction_cdl: List[str] = Field(default_factory=list, description="定义几何实体构造的辅助谓词")
    text_cdl: List[str] = Field(default_factory=list, description="仅从【文本描述】中提取的几何关系和条件")
    image_cdl: List[str] = Field(default_factory=list, description="仅从【图片】中提取的几何关系和条件")
    goal_cdl: str = Field(default="", description="求解目标，必须以 'Value(...)' 的形式表示")
    problem_answer: str = Field(default="", description="问题的标准答案")
    problem_type: List[str] = Field(default_factory=list, description="问题的类型分类")
    complexity_level: str = Field(default="", description="问题的复杂度级别")
    theorem_seqs: List[str] = Field(default_factory=list, description="解决问题所需的定理序列")
    theorem_seqs_dag: str = Field(default="{\"START\": []}", description="定理的有向无环图")

# API返回的简化Schema（只包含核心CDL字段）
class CDLSchema(BaseModel):
    construction_cdl: List[str] = Field(default_factory=list)
    text_cdl: List[str] = Field(default_factory=list)
    image_cdl: List[str] = Field(default_factory=list)
    goal_cdl: str = Field(default="")
    problem_answer: str = Field(default="")
# --- 2. 优化后的黄金提示词模板 ---
PROMPT_TEMPLATE = """
你是一位精通几何学、逻辑学和计算机科学的专家。你的任务是精确地将几何问题（包含自然语言描述和图片）转换成特定格式的JSON。
你必须严格按照提供的JSON Schema格式输出结果。

**规则 0: 【谓词合规性 - 最重要!】**
你生成的所有CDL谓词（例如 `Equal`, `Cone`, `LengthOfLine`）**必须**严格从下面提供的官方列表中选择。
绝不允许使用任何未在此列表中出现的谓词。这是一个硬性约束。

--- 官方谓词列表 ---
{valid_predicates_str}
--- 官方谓词列表结束 ---

**核心规则与约束:**
1.  **信息来源区分**: 
    - `text_cdl` 字段【只能】包含从自然语言描述中提取的信息。
    - `image_cdl` 字段【只能】包含从图片中直接观察到的信息（如长度标注、角度符号）。
    - 如果一个信息同时出现在文本和图片中，请在两个字段中都包含它。
2.  **答案格式化**: `problem_answer` 字段必须是纯数字或表达式（例如 "10", "254.47", "36*pi"），绝对不能包含单位（如 'cm'）或文字（如 'Surface Area ='）。
3.  **未知谓词处理**: 在 `construction_cdl` 中，如果遇到不确定的辅助谓词（如 'Shape', 'Cocircular'），请直接忽略它们，返回一个空列表 `[]`。
4.  **核心谓词逻辑**:
    - **长度/高度/母线**: `Equal(LengthOfLine(A,B),5)`, `Equal(HeightOfCone(O,P),12)`, `Equal(BusbarOfCone(O,P),13)`
    - **半径/直径**: `Equal(RadiusOfCircle(O),5)`, `Value(DiameterOfCircle(O))`
    - **关系**: `PerpendicularBetweenLine(A,B,C,D)`, `ParallelBetweenLine(A,B,C,D)`
    - **目标**: 问句中要求解的值必须用 `Value(...)` 包裹。

请仔细分析文本和图片中的所有信息，确保所有几何实体、关系和目标都被准确无误地转换。

**重要提示**: 请直接输出JSON格式，不要添加任何额外的解释或标记。
"""

def load_few_shot_examples(example_dir):
    """从文件夹加载few-shot范例"""
    examples_text = "\n--- 以下是几个高质量的范例，请严格遵循它们的格式和逻辑 ---\n"
    try:
        example_files = sorted([f for f in os.listdir(example_dir) if f.endswith('.json')])
        for filename in example_files:
            problem_id = filename.split('.')[0]
            json_path = os.path.join(example_dir, filename)
            
            text_path = os.path.join(example_dir, f"{problem_id}.txt")
            image_path_png = os.path.join(example_dir, f"{problem_id}.png")
            image_path_jpg = os.path.join(example_dir, f"{problem_id}.jpg")

            if not os.path.exists(text_path): continue

            with open(text_path, 'r', encoding='utf-8') as f:
                problem_text = f.read().strip()
            with open(json_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)

            examples_text += f"\n### 范例 {problem_id}: 输入\n"
            examples_text += f"自然语言描述: \"{problem_text}\"\n"
            examples_text += f"[图片: {os.path.basename(image_path_png if os.path.exists(image_path_png) else image_path_jpg)}]\n"
            examples_text += f"\n### 范例 {problem_id}: JSON输出\n"
            examples_text += f"```json\n{json.dumps(json_content, indent=2, ensure_ascii=False)}\n```\n"
            
    except Exception as e:
        print(f"加载范例时出错: {e}")
        return ""
        
    return examples_text

def load_valid_predicates(gdl_path):
    """从 predicate_GDL.json 文件中加载所有合法的谓词名称。"""
    try:
        with open(gdl_path, 'r', encoding='utf-8') as f:
            gdl_data = json.load(f)
        
        predicate_names = set()
        
        # 提取 "Entity", "Relation", "Attribution" 中的所有谓词
        for category in ["Entity", "Relation", "Attribution"]:
            if category in gdl_data:
                for key in gdl_data[category].keys():
                    predicate_name = key.split('(')[0]
                    predicate_names.add(predicate_name)
                    
        # 也添加一些可能的基础实体谓词
        for preset_key in ["BasicEntity", "Construction"]:
            if preset_key in gdl_data.get("Preset", {}):
                for name in gdl_data["Preset"][preset_key]:
                    predicate_names.add(name)
        
        # 添加 Equal 谓词
        predicate_names.add("Equal")
        predicate_names.add("Value")

        return sorted(list(predicate_names))
    except Exception as e:
        print(f"错误: 无法加载或解析谓词库 '{gdl_path}': {e}")
        return None

def image_to_base64(image_path):
    """将图片转换为base64编码"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # 检测图片格式
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'
            return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"图片编码错误 {image_path}: {e}")
        return None

def generate_geometry_json(problem_text, image_path, golden_prompt, problem_id, retries=3, delay=5):
    """
    调用DeepSeek API（实际是gpt-4o-mini）生成单个几何问题的JSON。
    """
    # 准备图片
    image_base64 = image_to_base64(image_path)
    if not image_base64:
        return {"status": "error", "message": f"无法读取图片文件 {image_path}", "problem_text": problem_text}

    # 构建消息 - 简化提示词，只要求核心CDL字段
    messages = [
        {
            "role": "system",
            "content": golden_prompt + "\n\n重要提示：你的JSON输出应该只包含这些字段：construction_cdl, text_cdl, image_cdl, goal_cdl, problem_answer"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"自然语言描述: \"{problem_text}\"\n\n请分析图片和文本，然后只生成CDL字段的JSON格式。"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    }
                }
            ]
        }
    ]

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4096
            )
            
            # 解析响应
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                # 移除可能的markdown代码块标记
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                parsed_data = json.loads(content)
                
                # 修复goal_cdl格式：如果是列表，取第一个元素
                if isinstance(parsed_data.get('goal_cdl'), list):
                    if parsed_data['goal_cdl']:  # 非空列表
                        parsed_data['goal_cdl'] = parsed_data['goal_cdl'][0]
                    else:  # 空列表
                        parsed_data['goal_cdl'] = ""
                
                # 使用简化的CDLSchema验证
                cdl_data = CDLSchema(**parsed_data)
                
                # 补全完整的ProblemSchema字段
                full_data = ProblemSchema(
                    problem_id=problem_id,
                    annotation="",
                    source="SolidGeo",
                    problem_text_en=problem_text,
                    construction_cdl=cdl_data.construction_cdl,
                    text_cdl=cdl_data.text_cdl,
                    image_cdl=cdl_data.image_cdl,
                    goal_cdl=cdl_data.goal_cdl,
                    problem_answer=cdl_data.problem_answer,
                    problem_type=[],
                    complexity_level="",
                    theorem_seqs=[],
                    theorem_seqs_dag="{\"START\": []}"
                )
                
                return {"status": "success", "data": full_data.dict(), "problem_text": problem_text}
            else:
                raise ValueError("API返回内容为空。")

        except Exception as e:
            error_message = f"API调用或解析失败 (尝试 {attempt + 1}/{retries}): {e}"
            print(f"错误/警告: {error_message}")
            
            if attempt == retries - 1:
                return {"status": "error", "message": error_message, "problem_text": problem_text}
        
        time.sleep(delay)

    return {"status": "error", "message": "已达到最大重试次数", "problem_text": problem_text}


def batch_process_problems(input_dir, output_dir, example_dir, gdl_path):
    """
    批量处理文件夹中的所有问题。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 从GDL文件加载合法的谓词
    valid_predicates = load_valid_predicates(gdl_path)
    if not valid_predicates:
        print("由于无法加载谓词库，处理中止。")
        return
    
    # 将谓词列表格式化为字符串
    valid_predicates_str = ", ".join(valid_predicates)

    few_shot_examples = load_few_shot_examples(example_dir)
    if not few_shot_examples:
        print("警告: 未能加载 few-shot 范例，将继续使用无范例的提示词。")
    
    # 动态构建黄金提示词
    golden_prompt = PROMPT_TEMPLATE.format(valid_predicates_str=valid_predicates_str) + few_shot_examples
    
    # 查找输入文件
    problem_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    log_data = []

    print(f"找到 {len(problem_files)} 个问题待处理。")
    
    for json_filename in tqdm(problem_files, desc="DeepSeek处理进度"):
        problem_id_str = json_filename.split('.')[0]
        json_path = os.path.join(input_dir, json_filename)
        log_entry = {"problem_id": problem_id_str}

        try:
            # 从JSON中读取 problem_text 和 image_path
            with open(json_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            problem_text = input_data.get("problem_text_en")
            if not problem_text:
                print(f"警告: JSON文件 '{json_filename}' 中的 'problem_text_en' 为空，已跳过。")
                log_entry.update({"status": "skipped", "reason": "Empty 'problem_text_en' in source JSON"})
                log_data.append(log_entry)
                continue

            img_path_info = input_data.get("problem_img")
            if isinstance(img_path_info, list) and img_path_info:
                image_relative_path = img_path_info[0]
            elif isinstance(img_path_info, str) and img_path_info:
                image_relative_path = img_path_info
            else:
                print(f"警告: JSON文件 '{json_filename}' 中 'problem_img' 格式不正确或为空，已跳过。")
                log_entry.update({"status": "skipped", "reason": "Invalid 'problem_img' in source JSON"})
                log_data.append(log_entry)
                continue
            
            # 构建完整的图片路径
            normalized_img_path = image_relative_path.replace('\\', '/')
            image_path = os.path.join("gemini", normalized_img_path)

            if not os.path.exists(image_path):
                print(f"警告: 找不到图片 '{image_path}' (在 {json_filename} 中定义)，已跳过。")
                log_entry.update({"status": "skipped", "reason": f"Image file not found at {image_path}"})
                log_data.append(log_entry)
                continue

        except (json.JSONDecodeError, KeyError) as e:
            print(f"警告: 解析JSON文件 '{json_filename}' 时出错: {e}，已跳过。")
            log_entry.update({"status": "skipped", "reason": f"Error reading source JSON: {e}"})
            log_data.append(log_entry)
            continue
        
        # 调用API生成（传入problem_id）
        try:
            problem_id = int(problem_id_str)
        except ValueError:
            problem_id = 0
        
        result = generate_geometry_json(problem_text, image_path, golden_prompt, problem_id)
        
        # 保存和日志记录
        if result["status"] == "success":
            output_json_path = os.path.join(output_dir, f"{problem_id_str}.json")
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(result["data"], f, indent=2, ensure_ascii=False)
            log_entry["status"] = "success"
            log_entry["output_file"] = output_json_path
        else:
            log_entry["status"] = "error"
            log_entry["reason"] = result["message"]
        
        log_data.append(log_entry)

    log_file_path = os.path.join(output_dir, "_generation_log_deepseek.json")
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n批量处理完成！结果已保存在 '{output_dir}' 目录。")
    print(f"详细日志请见: '{log_file_path}'")


if __name__ == '__main__':
    # --- 请在这里配置您的文件夹路径 ---
    INPUT_PROBLEM_DIR = "gemini/data/new_problems" 
    FEW_SHOT_EXAMPLE_DIR = "gemini/data/examples"
    OUTPUT_DIR = "gemini/data/deepseek_output"
    PREDICATE_GDL_PATH = "gemini/predicate_GDL.json"

    if not os.path.exists(INPUT_PROBLEM_DIR): os.makedirs(INPUT_PROBLEM_DIR)
    if not os.path.exists(FEW_SHOT_EXAMPLE_DIR): os.makedirs(FEW_SHOT_EXAMPLE_DIR)
    
    # 运行批量处理
    batch_process_problems(
        input_dir=INPUT_PROBLEM_DIR, 
        output_dir=OUTPUT_DIR, 
        example_dir=FEW_SHOT_EXAMPLE_DIR,
        gdl_path=PREDICATE_GDL_PATH
    )

