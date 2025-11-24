#!/usr/bin/env python3
"""
ChatGPT CDL Generation Script
基于Gemini实现改造,使用OpenAI API生成几何问题的CDL表示
"""

from openai import OpenAI
import PIL.Image
import os
import json
import time
import base64
import socket
from io import BytesIO
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- 配置 ---
# 使用OpenAI兼容的API
OPENAI_API_KEY = "sk-oMHOiiySXVtKYBHBK2QJNlVWpwNC228JHTJrl824UdcV735S"
OPENAI_API_BASE = "https://aicanapi.com/v1"  # ChatGPT API base URL

if not OPENAI_API_KEY:
    raise ValueError("API密钥不能为空")

# 初始化OpenAI客户端
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE
)

# --- 1. 使用Pydantic定义严格的JSON输出结构 (Schema) ---
# 完整Schema（用于最终输出）
class ProblemSchema(BaseModel):
    problem_id: int = Field(default=0, description="问题的唯一标识符")
    annotation: str = Field(default="", description="标注信息")
    source: str = Field(default="SolidGeo", description="问题的来源")
    problem_text_en: str = Field(default="", description="问题的完整英文自然语言描述")
    construction_cdl: List[str] = Field(default_factory=list, description="定义几何实体构造的辅助谓词，包括Shape、Collinear、Cocircular、Coplanar、Cospherical等。用于定义形状的边、线段和点的几何关系。")
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
# --- 2. 优化后的黄金提示词模板（参考Gemini代码风格） ---
PROMPT_TEMPLATE = """You are an expert in generating CDL for geometry, and must strictly follow the format and rules of the following training examples to generate CDL:

**Rule 0: [Predicate Compliance - MOST IMPORTANT!]**
All CDL predicates you generate (e.g., `Equal`, `Cone`, `LengthOfLine`) **MUST** be strictly selected from the official list provided below.
You are absolutely forbidden from using any predicates not appearing in this list. This is a hard constraint.

--- Official Predicate List ---
{valid_predicates_str}
--- End of Official Predicate List ---

**Core Rules:**

1. **text_cdl**: Extract key geometric information from the problem text (if there is no text, fill in ["no relevant text information"]), and ensure that there are no spaces before or after the comma in any Equal(x,3)

2. **image_cdl**: Extract visual elements from the image (if there is no image, fill in ["no relevant image information"])

3. **construction_cdl**: Generate geometric construction steps (points are represented by single letters A/B/C/D, etc.)
   - **Shape Predicates**: Define edges or line segments of shapes
     * For line segments/edges: `Shape(AB,BC,CD,DA)` or `Shape(OP,PO)` or `Shape(PQ,QP)`
     * For points (spheres, etc.): `Shape(O)` or `Shape(P)`
   - **Collinear/Cocircular/Coplanar/Cospherical Predicates**: Define geometric relationships of points
     * `Collinear(PABQ)` - Points P, A, B, Q are collinear
     * `Cocircular(O)` - Point O is on a circle (used for cone/cylinder base center)
     * `Cocircular(P)`, `Cocircular(Q)` - Points P, Q are on their respective circles
     * `Coplanar(U,ABCD)` - Point U is coplanar with ABCD
     * `Cospherical(O)` - Point O is on a sphere

4. **goal_cdl**: Define the problem objective (when there is no text or image, make reasonable inferences based on the geometric scenario, such as "complete relevant calculations based on geometric shapes")

5. **problem_answer**: Must be a pure number or expression (e.g., "10", "254.47", "36*pi"), absolutely cannot contain units (like 'cm') or text (like 'Surface Area =').

### Training Examples (Total: {total_examples})
{training_examples}

### Test Task
Now please process the following test sample and strictly follow the above example format to generate a JSON-formatted CDL, with fields including:
- construction_cdl (List[str])
- text_cdl (List[str])
- image_cdl (List[str])
- goal_cdl (str)
- problem_answer (str)

Output only JSON, do not include other redundant content.
"""

def load_few_shot_examples(train_dir, images_dir, max_examples=5):
    """
    从manual_train_set目录加载few-shot范例，并加载对应的图片
    
    Args:
        train_dir: 训练范例目录
        images_dir: 图片目录
        max_examples: 最大范例数量（限制数量以避免token过多）
    
    Returns:
        examples_data: List[Dict] 包含范例数据的列表，每个元素包含文本、图片base64和CDL
        valid_count: int 有效范例数量
    """
    examples_data = []
    valid_count = 0
    
    try:
        # 获取所有JSON文件并排序
        train_json_files = [
            f for f in os.listdir(train_dir)
            if f.endswith('.json') and os.path.isfile(os.path.join(train_dir, f))
        ]
        train_json_files.sort(key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 999999)
        
        for json_file in train_json_files:
            if valid_count >= max_examples:
                break
                
            problem_id = json_file.split('.')[0]
            json_path = os.path.join(train_dir, json_file)
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    train_data = json.load(f)
                
                # 检查是否有有效的CDL数据
                has_valid_cdl = False
                cdl_fields = ['construction_cdl', 'text_cdl', 'image_cdl', 'goal_cdl']
                for field in cdl_fields:
                    val = train_data.get(field, [])
                    if (isinstance(val, list) and len(val) > 0) or (isinstance(val, str) and val.strip()):
                        has_valid_cdl = True
                        break
                
                if not has_valid_cdl:
                    continue
                
                # 获取问题文本
                problem_text = train_data.get('problem_text_en', '').strip()
                if not problem_text:
                    # 尝试从txt文件读取
                    txt_path = os.path.join(train_dir, f"{problem_id}.txt")
                    if os.path.exists(txt_path):
                        with open(txt_path, 'r', encoding='utf-8') as f:
                            problem_text = f.read().strip()
                
                # 获取图片并编码为base64
                img_base64 = None
                image_extensions = ['.png', '.jpg', '.jpeg']
                for ext in image_extensions:
                    candidate_path = os.path.join(images_dir, f"{problem_id}{ext}")
                    if os.path.exists(candidate_path):
                        img_base64 = image_to_base64(candidate_path)
                        break
                
                # 构建范例数据
                example_data = {
                    "problem_id": problem_id,
                    "problem_text": problem_text if problem_text else "无文本信息",
                    "image_base64": img_base64,
                    "text_cdl": train_data.get('text_cdl', []),
                    "image_cdl": train_data.get('image_cdl', []),
                    "construction_cdl": train_data.get('construction_cdl', []),
                    "goal_cdl": train_data.get('goal_cdl', ''),
                    "problem_answer": train_data.get('problem_answer', '')
                }
                
                examples_data.append(example_data)
                valid_count += 1
                
            except Exception as e:
                print(f"跳过训练样本{problem_id}（加载失败）: {str(e)}")
                continue
        
        print(f"成功加载 {valid_count} 个训练范例（包含图片）")
        
    except Exception as e:
        print(f"加载训练范例时出错: {e}")
        return [], 0
        
    return examples_data, valid_count

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

        return sorted(predicate_names)
    except Exception as e:
        print(f"Error loading predicates from '{gdl_path}': {e}")
        return None

def fix_incomplete_json(json_str):
    """Try to fix incomplete JSON strings"""
    try:
        # Try direct parsing
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # Try to fix common JSON truncation issues
    fixed_str = json_str.strip()
    
    # If starts with { but doesn't end with }, try to add it
    if fixed_str.startswith('{') and not fixed_str.rstrip().endswith('}'):
        # Find the last complete key-value pair
        last_comma = fixed_str.rfind(',')
        if last_comma > 0:
            # Remove the last incomplete key-value pair
            fixed_str = fixed_str[:last_comma] + '}'
        else:
            fixed_str = fixed_str + '}'
    
    # Try to parse the fixed string
    try:
        return json.loads(fixed_str)
    except json.JSONDecodeError:
        return None

def normalize_cdl_data(cdl_data):
    """Normalize CDL data to ensure it's a list of strings"""
    if cdl_data is None:
        return []
    if isinstance(cdl_data, list):
        result = []
        for item in cdl_data:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Try to extract predicate string from dict
                # e.g., {"predicate": "Cylinder", "params": ["O", "P"]} -> "Cylinder(O,P)"
                predicate = item.get('predicate') or (list(item.keys())[0] if item else None)
                if predicate:
                    params = item.get('params') or item.get(predicate) or []
                    if isinstance(params, list):
                        params_str = ','.join(str(p) for p in params)
                        result.append(f"{predicate}({params_str})")
                    else:
                        result.append(str(predicate))
        return result
    return []

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
        print(f"Error encoding image {image_path}: {e}")
        return None

def generate_geometry_json(problem_text, image_path, golden_prompt, problem_id, few_shot_examples_data=None, retries=3, delay=5):
    """
    调用ChatGPT API生成单个几何问题的JSON，使用结构化输出。
    
    Args:
        problem_text: 问题文本（可以为空）
        image_path: 问题图片路径（可以为None，表示没有图片）
        golden_prompt: 基础提示词
        problem_id: 问题ID
        few_shot_examples_data: Few-shot范例数据列表（包含图片）
        retries: 重试次数
        delay: 重试延迟
    """
    # 准备图片（如果提供）
    image_base64 = None
    if image_path:
        print(f"    🖼️  Processing image: {os.path.basename(image_path)}")
        image_base64 = image_to_base64(image_path)
        if not image_base64:
            print(f"    ⚠️  Warning: Failed to load image {image_path}, will process with text only.")
        else:
            print("    ✅ Image processing completed")
    else:
        print("    ℹ️  No image provided, will process with text only.")

    # 构建消息 - 包含few-shot范例
    messages = []
    
    # System message包含基础提示词
    messages.append({
        "role": "system",
        "content": golden_prompt + "\n\nIMPORTANT: Your JSON output should ONLY contain these fields: construction_cdl, text_cdl, image_cdl, goal_cdl, problem_answer"
    })
    
    # 添加few-shot范例（如果提供）
    if few_shot_examples_data:
        for i, example in enumerate(few_shot_examples_data, 1):
            # 范例的user message
            example_content = [
                {
                    "type": "text",
                    "text": f"Example {i} (ID: {example['problem_id']}):\nNatural Language Description: \"{example['problem_text']}\"\n\nPlease analyze the image and text, then generate the CDL fields in JSON format."
                }
            ]
            
            # 如果范例有图片，添加到消息中
            if example.get('image_base64'):
                example_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": example['image_base64']
                    }
                })
            
            messages.append({
                "role": "user",
                "content": example_content
            })
            
            # 范例的assistant回复（包含CDL输出）
            messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "construction_cdl": example['construction_cdl'],
                    "text_cdl": example['text_cdl'],
                    "image_cdl": example['image_cdl'],
                    "goal_cdl": example['goal_cdl'],
                    "problem_answer": example['problem_answer']
                }, ensure_ascii=False)
            })
    
    # 当前问题的user message
    user_content = [
        {
            "type": "text",
            "text": f"Now process this problem (ID: {problem_id}):\nNatural Language Description: \"{problem_text if problem_text else '(No text description, analyze the image only)'}\"\n\nPlease analyze the image and text, then generate ONLY the CDL fields in JSON format."
        }
    ]
    
    # 如果有图片，添加到消息中
    if image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": image_base64
            }
        })
    
    messages.append({
        "role": "user",
        "content": user_content
    })

    for attempt in range(retries):
        try:
            if attempt > 0:
                print(f"    🔄 Retry attempt {attempt + 1}...")
            
            print(f"    ⏳ Sending API request to gpt-4o...")
            print(f"    ℹ️  Request contains {len(messages)} messages with {len(few_shot_examples_data) if few_shot_examples_data else 0} few-shot examples")
            
            # 设置socket超时（120秒）
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(120)
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # 使用支持视觉的模型
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=4096,
                    timeout=120.0  # 120秒超时
                )
                print(f"    📥 Received API response")
            except Exception as api_error:
                error_msg = f"API call failed: {str(api_error)}"
                print(f"    ❌ {error_msg}")
                # 恢复原来的超时设置
                socket.setdefaulttimeout(old_timeout)
                if attempt == retries - 1:
                    return {"status": "error", "message": error_msg, "problem_text": problem_text}
                continue
            finally:
                # 恢复原来的超时设置
                socket.setdefaulttimeout(old_timeout)
            
            # 解析响应
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                
                # Try to parse JSON (may be incomplete)
                try:
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    # Try to fix incomplete JSON
                    print(f"    🔧 Attempting to fix incomplete JSON...")
                    parsed_data = fix_incomplete_json(content)
                    if parsed_data is None:
                        error_message = f"JSON parsing failed and cannot be fixed (attempt {attempt + 1}/{retries})"
                        print(f"Error/Warning: {error_message}")
                        if attempt == retries - 1:
                            return {"status": "error", "message": error_message, "raw_output": content, "problem_text": problem_text}
                        continue
                
                # Normalize CDL data format
                print(f"    🔄 Normalizing data format...")
                parsed_data['construction_cdl'] = normalize_cdl_data(parsed_data.get('construction_cdl'))
                parsed_data['text_cdl'] = normalize_cdl_data(parsed_data.get('text_cdl'))
                parsed_data['image_cdl'] = normalize_cdl_data(parsed_data.get('image_cdl'))
                
                # Fix goal_cdl format: if it's a list, take the first element
                if isinstance(parsed_data.get('goal_cdl'), list):
                    if parsed_data['goal_cdl']:  # Non-empty list
                        parsed_data['goal_cdl'] = parsed_data['goal_cdl'][0]
                    else:  # Empty list
                        parsed_data['goal_cdl'] = ""
                elif not isinstance(parsed_data.get('goal_cdl'), str):
                    parsed_data['goal_cdl'] = str(parsed_data.get('goal_cdl', ''))
                
                # Use simplified CDLSchema for validation
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


def batch_process_problems(input_dir, output_dir, example_dir, gdl_path, start_id=1, end_id=None, force_regenerate=False):
    """
    批量处理文件夹中的所有问题。
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        example_dir: 范例目录
        gdl_path: 谓词定义文件路径
        start_id: 起始问题ID（包含），默认1
        end_id: 结束问题ID（包含），默认None表示不限制
        force_regenerate: 是否强制重新生成所有问题（忽略已处理的标记），默认False
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

    # 从manual_train_set加载few-shot范例（包含图片）
    train_dir = example_dir  # example_dir现在指向manual_train_set
    images_dir = "src/fgps/formalgeo7k_v2/images"  # 图片目录
    # 使用适量的few-shot样本（20个，在效果和性能之间取得平衡）
    # 20个范例包含图片，请求大小适中，既能提供足够的学习样本又不会导致超时
    few_shot_examples_data, example_count = load_few_shot_examples(train_dir, images_dir, max_examples=20)
    
    if example_count == 0:
        print("警告: 未能加载 few-shot 范例，将继续使用无范例的提示词。")
    
    # 构建范例文本（用于提示词）
    examples_text = ""
    for i, example in enumerate(few_shot_examples_data, 1):
        img_note = f"图片路径：{example['problem_id']}.png" if example['image_base64'] else "无对应图片"
        examples_text += f"""
#### 范例{i}（ID：{example['problem_id']}）
- 问题文本：{example['problem_text']}
- {img_note}
- text_cdl：{example['text_cdl']}
- image_cdl：{example['image_cdl']}
- construction_cdl：{example['construction_cdl']}
- goal_cdl：{example['goal_cdl']}
- problem_answer：{example['problem_answer']}
"""
    
    # 动态构建黄金提示词（参考Gemini代码风格）
    golden_prompt = PROMPT_TEMPLATE.format(
        valid_predicates_str=valid_predicates_str,
        total_examples=example_count,
        training_examples=examples_text
    )
    
    # 查找输入文件
    problem_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    # 过滤问题ID范围
    filtered_files = []
    for json_filename in problem_files:
        try:
            problem_id = int(json_filename.split('.')[0])
            if problem_id >= start_id and (end_id is None or problem_id <= end_id):
                filtered_files.append(json_filename)
        except ValueError:
            # 如果无法解析ID，跳过该文件
            continue
    
    filtered_files.sort(key=lambda x: int(x.split('.')[0]))
    
    # 断点续传：加载已有的日志文件，检查已处理的问题
    log_file_path = os.path.join(output_dir, "_generation_log_chatgpt.json")
    processed_problems = set()  # 已成功处理的问题ID集合
    log_data = []  # 日志数据
    
    # 如果强制重新生成，跳过加载已处理的问题
    if force_regenerate:
        print("🔄 Force regenerate mode: Will regenerate all problems regardless of existing outputs.")
        # 可以选择备份旧的日志文件
        if os.path.exists(log_file_path):
            backup_path = log_file_path + ".backup"
            try:
                import shutil
                shutil.copy2(log_file_path, backup_path)
                print(f"📦 Backed up existing log to: {backup_path}")
            except Exception as e:
                print(f"⚠️  Warning: Failed to backup log file: {e}")
    else:
        # 正常模式：加载已处理的问题
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
                # 找出已成功处理的问题
                for log_entry in existing_logs:
                    if log_entry.get("status") == "success":
                        processed_problems.add(str(log_entry.get("problem_id")))
                log_data = existing_logs  # 保留已有日志
                print(f"📋 Loaded existing log: Found {len(processed_problems)} successfully processed problems, will continue from checkpoint...")
            except Exception as e:
                print(f"⚠️  Warning: Unable to load existing log file '{log_file_path}': {e}, will start from beginning.")
        
        # 检查输出目录中已存在的文件（即使日志中没有记录）
        if os.path.exists(output_dir):
            existing_output_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and f != '_generation_log_chatgpt.json']
            for output_file in existing_output_files:
                problem_id_from_file = output_file.split('.')[0]
                # 检查文件是否有效（包含必要字段）
                output_file_path = os.path.join(output_dir, output_file)
                try:
                    with open(output_file_path, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                    # 如果文件包含problem_id字段，认为已处理（需要检查是否是dict）
                    if isinstance(output_data, dict) and output_data.get("problem_id") is not None:
                        processed_problems.add(problem_id_from_file)
                except (json.JSONDecodeError, IOError, OSError):
                    pass  # 如果文件损坏或无法读取，忽略
    
    # 过滤掉已处理的问题
    remaining_files = []
    for json_filename in filtered_files:
        problem_id_str = json_filename.split('.')[0]
        if problem_id_str not in processed_problems:
            remaining_files.append(json_filename)
    
    print(f"Found {len(problem_files)} problem files, filtered to {len(filtered_files)} problems in range, of which {len(processed_problems)} are already processed, {len(remaining_files)} remaining to process.")
    
    if len(remaining_files) == 0:
        print("✅ All problems have been processed!")
        return
    
    for idx, json_filename in enumerate(tqdm(remaining_files, desc="ChatGPT Processing Progress"), 1):
        problem_id_str = json_filename.split('.')[0]
        json_path = os.path.join(input_dir, json_filename)
        log_entry = {"problem_id": problem_id_str}

        try:
            # 从JSON中读取 problem_text 和 image_path
            with open(json_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            # 获取问题文本（允许为空，只要有图片就可以处理）
            problem_text = input_data.get("problem_text_en", "").strip()
            if not problem_text:
                problem_text = input_data.get("problem_text_cn", "").strip()
            if not problem_text:
                problem_text = ""  # 允许为空，只处理图片
            
            # 从文件名或problem_id字段中提取问题ID
            problem_id = input_data.get("problem_id")
            if problem_id is None:
                # 如果JSON中没有problem_id，从文件名中提取
                try:
                    problem_id = int(problem_id_str)
                except ValueError:
                    print(f"Warning: Cannot extract problem_id from filename '{json_filename}', skipping.")
                    log_entry.update({"status": "skipped", "reason": "Cannot extract problem_id from filename"})
                    log_data.append(log_entry)
                    continue
            else:
                problem_id = int(problem_id)
            
            # 优先使用 problem_img 字段中的路径
            image_path = None
            images_base_dir = "src/fgps/formalgeo7k_v2/images"
            image_extensions = ['.png', '.jpg', '.jpeg']
            
            # 方法1: 尝试从 problem_img 字段获取图片路径
            problem_img = input_data.get("problem_img")
            if problem_img:
                if isinstance(problem_img, list) and len(problem_img) > 0:
                    img_path_str = problem_img[0]
                elif isinstance(problem_img, str):
                    img_path_str = problem_img
                else:
                    img_path_str = None
                
                if img_path_str:
                    # 处理路径格式（可能是 Windows 路径格式 images\239.jpg）
                    img_path_str = img_path_str.replace('\\', '/')
                    # 提取文件名
                    img_filename = os.path.basename(img_path_str)
                    # 尝试在 images 目录中查找
                    candidate_path = os.path.join(images_base_dir, img_filename)
                    if os.path.exists(candidate_path):
                        image_path = candidate_path
            
            # 方法2: 如果方法1失败，按 problem_id 查找图片文件
            if not image_path:
                for ext in image_extensions:
                    candidate_path = os.path.join(images_base_dir, f"{problem_id}{ext}")
                    if os.path.exists(candidate_path):
                        image_path = candidate_path
                        break
            
            # 如果仍然找不到图片，检查是否至少有问题文本
            if not image_path:
                if not problem_text:
                    print(f"Warning: Problem {problem_id} has no image and no text, skipping.")
                    log_entry.update({"status": "skipped", "reason": f"No image and no text for problem_id {problem_id}"})
                    log_data.append(log_entry)
                    continue
                else:
                    # 只有文本没有图片，仍然可以处理（但会提示）
                    print(f"Warning: Problem {problem_id} has no image file, will process with text only.")
                    image_path = None  # 设置为 None，后续会处理

        except (json.JSONDecodeError, KeyError) as e:
            print(f"警告: 解析JSON文件 '{json_filename}' 时出错: {e}，已跳过。")
            log_entry.update({"status": "skipped", "reason": f"Error reading source JSON: {e}"})
            log_data.append(log_entry)
            continue
        
        # 显示当前处理进度
        if idx % 10 == 1 or idx == len(remaining_files):
            print(f"\n[{idx}/{len(remaining_files)}] Processing problem {problem_id_str}...")
        
        # 调用API生成（传入few-shot范例数据）
        print(f"  📤 Calling API for problem {problem_id_str}...")
        # 如果 image_path 为 None，传递 None 而不是字符串
        result = generate_geometry_json(problem_text, image_path if image_path else None, golden_prompt, problem_id, few_shot_examples_data)
        
        # 显示处理结果
        if result["status"] == "success":
            print(f"  ✅ Problem {problem_id_str} processed successfully")
        else:
            print(f"  ❌ Problem {problem_id_str} failed: {result.get('message', 'Unknown error')[:100]}")
        
        # 保存和日志记录
        if result["status"] == "success":
            output_json_path = os.path.join(output_dir, f"{problem_id_str}.json")
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(result["data"], f, indent=2, ensure_ascii=False)
            log_entry["status"] = "success"
            log_entry["output_file"] = output_json_path
            processed_problems.add(problem_id_str)  # 标记为已处理
        else:
            log_entry["status"] = "error"
            log_entry["reason"] = result["message"]
            if "raw_output" in result:
                log_entry["raw_output"] = result["raw_output"]
        
        # 更新日志（查找是否已有该问题的日志条目）
        existing_entry_index = None
        for i, entry in enumerate(log_data):
            if entry.get("problem_id") == problem_id_str:
                existing_entry_index = i
                break
        
        if existing_entry_index is not None:
            # 更新已有条目
            log_data[existing_entry_index] = log_entry
        else:
            # 添加新条目
            log_data.append(log_entry)
        
        # 增量保存日志（每处理一个问题就保存一次，实现断点续传）
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Warning: Failed to save log file: {e}")

    # 最终保存日志（确保所有数据都已保存）
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n批量处理完成！结果已保存在 '{output_dir}' 目录。")
    print(f"详细日志请见: '{log_file_path}'")


if __name__ == '__main__':
    # --- 请在这里配置您的文件夹路径 ---
    # 存放新问题（.json文件）的文件夹 - 直接从原始问题目录读取
    INPUT_PROBLEM_DIR = "src/fgps/formalgeo7k_v2/problems" 
    # 存放手动训练集（manual_train_set）的文件夹
    FEW_SHOT_EXAMPLE_DIR = "gemini/data/manual_train_set"
    # 存放AI生成结果的文件夹
    OUTPUT_DIR = "gemini/data/chatgpt_output"
    # 谓词定义文件
    PREDICATE_GDL_PATH = "gemini/predicate_GDL.json"
    # 处理范围：1-700题目
    START_ID = 1
    END_ID = 700

    if not os.path.exists(INPUT_PROBLEM_DIR):
        print(f"Error: Input directory does not exist: {INPUT_PROBLEM_DIR}")
        exit(1)
    if not os.path.exists(FEW_SHOT_EXAMPLE_DIR):
        print(f"Warning: Example directory does not exist: {FEW_SHOT_EXAMPLE_DIR}, will continue without examples.")
    
    # 是否强制重新生成所有问题（忽略已处理的标记）
    # 设置为 True 将重新生成所有问题，即使之前已经处理过
    FORCE_REGENERATE = True  # 设置为 True 以重新生成所有问题
    
    # 运行批量处理
    batch_process_problems(
        input_dir=INPUT_PROBLEM_DIR, 
        output_dir=OUTPUT_DIR, 
        example_dir=FEW_SHOT_EXAMPLE_DIR,
        gdl_path=PREDICATE_GDL_PATH,
        start_id=START_ID,
        end_id=END_ID,
        force_regenerate=FORCE_REGENERATE
    )

