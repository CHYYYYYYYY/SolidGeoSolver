# -*- coding: utf-8 -*-
import openai
import PIL.Image
import os
import json
import time
import socket
import socket
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import base64
from io import BytesIO
import sys

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# --- API configuration (Google Generative AI) ---
# Provide Google API keys via environment variable:
#   set GOOGLE_API_KEYS="KEY1,KEY2,KEY3" (or setx on Windows), or set GOOGLE_API_KEY (single)
GEMINI_API_BASE = "http://aicanapi.com/v1"
GEMINI_MODEL = "gemini-2.5-pro"
API_KEYS: List[str] = [
    "sk-8XbeoWmUgJy7muDhf4IswkRPrBjMmXBImOHCIP55NE0eh7le",
    "sk-cJIqFNxykfIFec19QUbIuwmQn6NoHLAyMD3lADfkLotYVOcI"
]
if not API_KEYS:
    print("⚠️  No Google API keys found. Set env var 'GOOGLE_API_KEYS' (comma-separated) or 'GOOGLE_API_KEY' before running.")


# API Key 轮询索引和状态追踪
current_key_index = 0
exhausted_keys = set()  # 记录已耗尽配额的 keys

def get_next_api_key():
    """轮询获取下一个可用的 API Key"""
    global current_key_index
    if not API_KEYS:
        raise RuntimeError("No API keys configured. Please set env var AICAN_API_KEYS (comma-separated) or AICAN_API_KEY/GOOGLE_API_KEY.")
    attempts = 0
    # Round-robin through available keys; skip those marked exhausted
    while attempts < len(API_KEYS):
        idx = current_key_index % len(API_KEYS)
        key = API_KEYS[idx]
        # advance pointer for next call
        current_key_index = (idx + 1) % len(API_KEYS)
        if key not in exhausted_keys:
            return key
        attempts += 1
    # All keys exhausted
    raise RuntimeError("All configured API keys are exhausted. Please wait for quota reset or update keys.")

def mark_key_exhausted(api_key):
    """标记某个 API key 配额已耗尽"""
    global exhausted_keys
    exhausted_keys.add(api_key)
    remaining = len(API_KEYS) - len(exhausted_keys)
    if remaining > 0:
        print(f"  ⚠️  API Key 配额耗尽，剩余可用 keys: {remaining}/{len(API_KEYS)}")
    else:
        print("  ⚠️  所有 API Keys 配额已耗尽！建议等待配额重置或使用新的 keys")


# --- 1. 使用Pydantic定义严格的JSON输出结构 (Schema) ---
# 修复：移除所有 'default' 参数，因为Gemini API的后端schema解析器不兼容它。
class ProblemSchema(BaseModel):
    problem_id: int = Field(description="问题的唯一标识符，例如 150")
    annotation: str = Field(description="标注信息。如果没有，则为空字符串。")
    source: str = Field(description="问题的来源，通常为 'SolidGeo'。")
    problem_text_en: str = Field(description="问题的完整英文自然语言描述。")
    construction_cdl: List[str] = Field(description="定义几何实体构造的辅助谓词，包括Shape、Collinear、Cocircular、Coplanar、Cospherical等。用于定义形状的边、线段和点的几何关系。")
    text_cdl: List[str] = Field(description="仅从【文本描述】中提取的几何关系和条件。")
    image_cdl: List[str] = Field(description="仅从【图片】中提取的几何关系和条件（例如直角符号、标注的长度等）。")
    goal_cdl: str = Field(description="从问题的问句中提炼出的求解目标，必须以 'Value(...)' 的形式表示。")
    problem_answer: str = Field(description="问题的标准答案，必须是纯数字或数学表达式，不含任何单位或文字。")
    problem_type: List[str] = Field(description="问题的类型分类。")
    complexity_level: str = Field(description="问题的复杂度级别。")
    # 修复：将 List[Any] 改为 List[str]，将 Dict[str, Any] 改为 str，以满足API对Schema的严格要求
    theorem_seqs: List[str] = Field(description="解决问题所需的定理序列（字符串列表），通常为空列表。")
    theorem_seqs_dag: str = Field(description="一个JSON字符串，表示解决问题所需定理的有向无环图。例如：'{\"START\": []}'")

# --- 2. 优化后的黄金提示词模板 ---
# 将其更改为模板，以便动态插入谓词列表
PROMPT_TEMPLATE = """
You are an expert in geometry, logic, and computer science. Your task is to precisely convert a geometry problem (with natural language and an image) into a JSON object following the provided JSON Schema.
You must strictly follow the schema and output a complete JSON object.

Rule 0: Predicate Compliance (MOST IMPORTANT)
- All CDL predicates you generate (e.g., `Equal`, `Cone`, `LengthOfLine`) MUST be strictly chosen from the official list below.
- Using any predicate that does not appear in this list is strictly forbidden.

--- Official Predicate List ---
{valid_predicates_str}
--- End of Official Predicate List ---

Core Rules and Constraints:

1) Information Source Separation:
   - `text_cdl` MUST include only facts extracted from the natural language description.
   - `image_cdl` MUST include only facts directly observable from the image (e.g., length labels, right-angle marks, shape recognition).
   - If a fact appears in both text and image, include it in both fields.

2) construction_cdl - Geometric construction predicates (IMPORTANT):
   `construction_cdl` defines basic construction for entities, and MUST include the following types where applicable:
   - Shape predicates: define edges/segments of shapes
     * For segments/edges: `Shape(AB,BC,CD,DA)` or `Shape(OP,PO)` or `Shape(PQ,QP)`
     * For points (spheres etc.): `Shape(O)` or `Shape(P)`
     * Example: rectangles require `Shape(AB,BC,CD,DA)`; cylinders require `Shape(PQ,QP)`
   - Collinearity/Cocircular/Coplanar/Cospherical:
     * `Collinear(PABQ)` - P, A, B, Q are collinear
     * `Cocircular(O)` - O is on a circle (for cone/cylinder base center)
     * `Cocircular(P)`, `Cocircular(Q)` - P and Q on their respective circles
     * `Coplanar(U,ABCD)` - U coplanar with ABCD
     * `Cospherical(O)` - O is on a sphere (for spheres)
   Important:
   - Carefully analyze the image to identify all necessary edges/segments/relations
   - Only return `[]` when no construction info is truly needed
   - Most problems require at least one `Shape(...)`
   - Cones/cylinders often need `Shape(...)` and `Cocircular(...)`
   - Spheres often need `Shape(O)` and `Cospherical(O)`
   - Cubes/prisms often need multiple `Shape(...)` with `Coplanar(...)`

3) Answer formatting:
   - `problem_answer` MUST be a pure number or expression (e.g., "10", "254.47", "36*pi"), and MUST NOT contain units or extra text.

4) Core predicate logic:
   - Length/Height/Generator: `Equal(LengthOfLine(A,B),5)`, `Equal(HeightOfCone(O,P),12)`, `Equal(BusbarOfCone(O,P),13)`
   - Radius/Diameter: `Equal(RadiusOfCircle(O),5)`, `Value(DiameterOfCircle(O))`
   - Relations: `PerpendicularBetweenLine(A,B,C,D)`, `ParallelBetweenLine(A,B,C,D)`
   - Goal: the requested quantity MUST be wrapped by `Value(...)`.

5) Predicate and Operator Legality (CRITICAL):
   - Only reuse names from the official predicate list; DO NOT invent new construction predicates (e.g., `Triangle`, `Line`, `Angle` are FORBIDDEN).
   - Quantities allowed in CDL expressions (including `goal_cdl`) are LIMITED to:
     `VolumeOfCone`, `VolumeOfCylinder`, `VolumeOfSphere`, `VolumeOfCuboid`, `VolumeOfQuadrangularPyramid`,
     `SurfaceAreaOfCylinder`, `SurfaceAreaOfCuboid`, `SurfaceAreaOfQuadrangularPrism`, `SurfaceAreaOfQuadrangularPyramid`,
     `LateralareaOfCone`, `LateralareaOfCylinder`, `AreaOfCircle`, `AreaOfSphere`, `AreaOfCuboid`, `AreaOfQuadrilateral`,
     `PerimeterOfQuadrilateral`, `DiameterOfCircle`, `RadiusOfCircle`, `LengthOfLine`, `HeightOfCone`, `HeightOfCylinder`, `BusbarOfCone`.
     If a problem mentions other quantities, rewrite them using these standard quantities or include supporting info in `text_cdl/image_cdl` and then use the standard quantities.
   - Only the following algebraic operators are allowed: `Value`, `Add`, `Sub`, `Mul`, `Div`. For "1/2 × X", write `Mul(1/2,X)`.
   - Formatting: NO extra spaces inside any predicate/operator. Use `Add(A,B,C)` and `Equal(HeightOfCylinder(P,Q),2)`, NOT `Add(A, B)` or `Equal(..., 2)`. Also avoid leading/trailing spaces in names (e.g., never `" VolumeOfCylinder"`).

6) Completeness Checks:
   - Ensure every entity used by `text_cdl`/`image_cdl` exists in `construction_cdl`
   - Ensure the target entity in `goal_cdl` exists in the construction as well
   - Self-check after generation: verify all predicates/operators are allowed, no extra spaces, and no undeclared entities are referenced.

Important: Output Requirements
1. You MUST output a complete JSON object with all required fields
2. All CDL fields MUST be arrays of strings (e.g., `["Cylinder(O,P)", "Equal(HeightOfCylinder(O,P),12)"]`)
3. `goal_cdl` MUST be a string (e.g., `"Value(VolumeOfCone(O,P))"`)
4. Required fields:
   - `problem_id`: integer
   - `annotation`: string (can be empty)
   - `source`: string (usually "SolidGeo")
   - `problem_text_en`: string
   - `construction_cdl`: array of strings
   - `text_cdl`: array of strings
   - `image_cdl`: array of strings
   - `goal_cdl`: string
   - `problem_answer`: string
   - `problem_type`: array of strings
   - `complexity_level`: string
   - `theorem_seqs`: array of strings (can be empty)
   - `theorem_seqs_dag`: JSON string (e.g., '{{"START": []}}')

Output Example:
Please follow the JSON example below (ALL fields are required):

JSON_EXAMPLE_PLACEHOLDER

Ensure the JSON is complete and properly formatted. Do NOT truncate or omit any fields.
"""

# JSON示例（单独定义，避免format()解析问题）
JSON_EXAMPLE = """```json
{
  "problem_id": 1,
  "annotation": "",
  "source": "SolidGeo",
  "problem_text_en": "Find the volume of the cone.",
  "construction_cdl": ["Shape(OP,PO)", "Cocircular(O)"],
  "text_cdl": ["Equal(HeightOfCone(O,P),12)"],
  "image_cdl": ["Cone(O,P)", "Equal(BusbarOfCone(O,P),13)"],
  "goal_cdl": "Value(VolumeOfCone(O,P))",
  "problem_answer": "10",
  "problem_type": ["Solid Geometry"],
  "complexity_level": "Level 1",
  "theorem_seqs": [],
  "theorem_seqs_dag": "{\"START\": []}"
}
```"""

def load_few_shot_examples(train_dir, images_dir, max_examples=40):
    """
    从训练集目录加载few-shot范例，并加载对应的图片
    
    Args:
        train_dir: 训练范例目录
        images_dir: 图片目录
        max_examples: 最大范例数量（默认40个）
    
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
        
        # 添加 Equal 和 Value 谓词
        predicate_names.add("Equal")
        predicate_names.add("Value")

        return sorted(predicate_names)
    except Exception as e:
        print(f"错误: 无法加载或解析谓词库 '{gdl_path}': {e}")
        return None

def fix_incomplete_json(json_str):
    """尝试修复不完整的JSON字符串"""
    try:
        # 尝试直接解析
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # 尝试修复常见的JSON截断问题
    fixed_str = json_str.strip()
    
    # 如果以 { 开头但没有 }，尝试添加
    if fixed_str.startswith('{') and not fixed_str.rstrip().endswith('}'):
        # 找到最后一个完整的键值对
        last_comma = fixed_str.rfind(',')
        if last_comma > 0:
            # 移除最后一个不完整的键值对
            fixed_str = fixed_str[:last_comma] + '}'
        else:
            fixed_str = fixed_str + '}'
    
    # 尝试解析修复后的字符串
    try:
        return json.loads(fixed_str)
    except json.JSONDecodeError:
        return None

def normalize_api_response(data, problem_id, problem_text_en):
    """规范化API返回的数据，填充缺失字段并修正格式"""
    normalized = {}
    
    # 必需字段的默认值
    normalized['problem_id'] = data.get('problem_id') or problem_id
    normalized['annotation'] = data.get('annotation') or ''
    normalized['source'] = data.get('source') or 'SolidGeo'
    normalized['problem_text_en'] = data.get('problem_text_en') or data.get('problem_text') or problem_text_en
    normalized['problem_answer'] = data.get('problem_answer') or ''
    normalized['problem_type'] = data.get('problem_type') or []
    normalized['complexity_level'] = data.get('complexity_level') or ''
    normalized['theorem_seqs'] = data.get('theorem_seqs') or []
    normalized['theorem_seqs_dag'] = data.get('theorem_seqs_dag') or '{"START": []}'
    
    # 处理CDL字段 - 确保它们是字符串列表
    def normalize_cdl_list(cdl_data):
        if cdl_data is None:
            return []
        if isinstance(cdl_data, list):
            result = []
            for item in cdl_data:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # 尝试从字典中提取谓词字符串
                    # 例如: {"predicate": "Cylinder", "params": ["O", "P"]} -> "Cylinder(O,P)"
                    predicate = item.get('predicate') or list(item.keys())[0] if item else None
                    if predicate:
                        params = item.get('params') or item.get(predicate) or []
                        if isinstance(params, list):
                            params_str = ','.join(str(p) for p in params)
                            result.append(f"{predicate}({params_str})")
                        else:
                            result.append(str(predicate))
            return result
        return []
    
    normalized['construction_cdl'] = normalize_cdl_list(
        data.get('construction_cdl')
    )
    normalized['text_cdl'] = normalize_cdl_list(
        data.get('text_cdl')
    )
    normalized['image_cdl'] = normalize_cdl_list(
        data.get('image_cdl')
    )
    
    # 处理goal_cdl - 确保它是字符串
    goal_cdl = data.get('goal_cdl')
    if isinstance(goal_cdl, list) and goal_cdl:
        normalized['goal_cdl'] = goal_cdl[0] if isinstance(goal_cdl[0], str) else str(goal_cdl[0])
    elif isinstance(goal_cdl, str):
        normalized['goal_cdl'] = goal_cdl
    else:
        normalized['goal_cdl'] = ''
    
    # 处理嵌套的cdl结构（如 {"cdl": {"construction_cdl": [...]}}）
    if 'cdl' in data and isinstance(data['cdl'], dict):
        cdl_data = data['cdl']
        if 'construction_cdl' in cdl_data:
            normalized['construction_cdl'] = normalize_cdl_list(cdl_data['construction_cdl'])
        if 'text_cdl' in cdl_data:
            normalized['text_cdl'] = normalize_cdl_list(cdl_data['text_cdl'])
        if 'image_cdl' in cdl_data:
            normalized['image_cdl'] = normalize_cdl_list(cdl_data['image_cdl'])
        if 'goal_cdl' in cdl_data:
            goal = cdl_data['goal_cdl']
            if isinstance(goal, list) and goal:
                normalized['goal_cdl'] = goal[0] if isinstance(goal[0], str) else str(goal[0])
            elif isinstance(goal, str):
                normalized['goal_cdl'] = goal
    
    return normalized

def image_to_base64(image_path):
    """将图片转换为base64编码（参考 test_gemini_problems.py）"""
    try:
        with PIL.Image.open(image_path) as img:
            # 如果图片太大，调整大小以节省API成本
            max_size = (1024, 1024)
            img.thumbnail(max_size, PIL.Image.Resampling.LANCZOS)
            
            # 转换为RGB（如果是RGBA或其他格式）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存到内存缓冲区
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            
            # 编码为base64
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
    except Exception as e:
        print(f"  ⚠️  图片转换失败: {e}")
        return None

def generate_geometry_json(problem_text, image_path, golden_prompt, problem_id, few_shot_examples_data=None, retries=5, delay=3):
    """
    通过 aicanapi.com 调用 Gemini API 生成单个几何问题的JSON，使用JSON Schema强制结构化输出。
    
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
        print(f"    🖼️  正在处理图片: {os.path.basename(image_path)}")
        image_base64 = image_to_base64(image_path)
        if not image_base64:
            print(f"    ⚠️  警告: 无法加载图片 {image_path}，将仅使用文本处理。")
        else:
            print("    ✅ 图片处理完成")
    else:
        print("    ℹ️  未提供图片，将仅使用文本处理。")
    
    # 构建消息 - 包含few-shot范例
    messages = []
    
    # System message包含基础提示词
    messages.append({
        "role": "system",
        "content": golden_prompt + "\n\nIMPORTANT: Your JSON output must include all required fields and strictly follow the format above."
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
            "text": f"Now process this problem (ID: {problem_id}):\nNatural Language Description: \"{problem_text if problem_text else '(No text description, analyze the image only)'}\"\n\nPlease analyze the image and text, then generate a complete JSON output including all required fields."
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
    
    # 如果没有图片也没有文本，返回错误
    if not image_base64 and not problem_text:
        return {"status": "error", "message": "问题既没有图片也没有文本，无法处理", "problem_text": problem_text}
    
    consecutive_quota_errors = 0
    
    for attempt in range(retries):
        try:
            # 获取下一个 API key
            api_key = get_next_api_key()
            
            if attempt > 0:
                print(f"    🔄 重试第 {attempt + 1} 次...")
            
            # 创建 OpenAI 兼容客户端（通过 aicanapi.com）
            client = openai.OpenAI(
                api_key=api_key,
                base_url=GEMINI_API_BASE
            )
            
            # 调用 API（使用 Gemini 模型名称）
            # 注意：OpenAI 兼容 API 可能不支持 response_format，我们需要在提示词中强调 JSON 格式
            print(f"    ⏳ 发送API请求到 {GEMINI_MODEL}...")
            print(f"    ℹ️  请求包含 {len(messages)} 条消息，其中 {len(few_shot_examples_data) if few_shot_examples_data else 0} 个 few-shot 范例")
            
            # 设置socket超时（120秒）
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(120)
            
            try:
                response = client.chat.completions.create(
                    model=GEMINI_MODEL,
                    messages=messages,
                    max_tokens=16
                    000,  # 增加 token 限制以支持完整的 JSON 输出（API最大支持65536）
                    temperature=0.1,
                    timeout=120.0  # 120秒超时
                )
                print("    📥 收到API响应")
            except Exception as api_error:
                error_msg = f"API调用失败: {str(api_error)}"
                print(f"    ❌ {error_msg}")
                # 恢复原来的超时设置
                socket.setdefaulttimeout(old_timeout)
                if attempt == retries - 1:
                    return {"status": "error", "message": error_msg, "problem_text": problem_text}
                continue
            finally:
                # 恢复原来的超时设置
                socket.setdefaulttimeout(old_timeout)
            
            response_text = ""
            if isinstance(response, str):
                response_text = response.strip()
            elif hasattr(response, 'choices') and response.choices and response.choices[0].message.content:
                response_text = response.choices[0].message.content.strip()

            if response_text:
                # Debug: 显示响应的前500字符以便监控
                print(f"    💬 API响应预览: {response_text[:200]}...")
                
                # 尝试提取 JSON（可能包含 markdown 代码块）
                # 移除可能的 markdown 代码块标记
                if response_text.startswith("```json"):
                    response_text = response_text[7:]  # 移除 ```json
                if response_text.startswith("```"):
                    response_text = response_text[3:]  # 移除 ```
                if response_text.endswith("```"):
                    response_text = response_text[:-3]  # 移除结尾的 ```
                response_text = response_text.strip()
                
                try:
                    # 尝试解析JSON（可能不完整）
                    parsed_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # 尝试修复不完整的JSON
                    print("    🔧 尝试修复不完整的JSON...")
                    parsed_data = fix_incomplete_json(response_text)
                    if parsed_data is None:
                        error_message = f"JSON解析失败且无法修复 (尝试 {attempt + 1}/{retries})\n原始响应: {response_text[:500]}"
                        print(f"错误/警告: {error_message}")
                        if attempt == retries - 1:
                            return {"status": "error", "message": error_message, "raw_output": response_text, "problem_text": problem_text}
                        continue
                
                # 规范化数据格式
                print("    🔄 规范化数据格式...")
                # 尝试从解析的数据中获取problem_id
                api_problem_id = parsed_data.get('problem_id')
                if api_problem_id:
                    try:
                        api_problem_id = int(api_problem_id)
                    except (ValueError, TypeError):
                        api_problem_id = None
                normalized_data = normalize_api_response(parsed_data, api_problem_id, problem_text)
                
                try:
                    # 使用Pydantic模型验证数据
                    validated_data = ProblemSchema(**normalized_data)
                    # 将验证后的Pydantic模型转换为字典以便保存
                    return {"status": "success", "data": validated_data.dict(), "problem_text": problem_text}
                except Exception as e:
                    error_message = f"数据验证失败 (尝试 {attempt + 1}/{retries}): {e}\n规范化后的数据: {json.dumps(normalized_data, ensure_ascii=False)[:500]}"
                    print(f"错误/警告: {error_message}")
                    if attempt == retries - 1:
                        return {"status": "error", "message": error_message, "raw_output": response_text, "normalized_data": normalized_data, "problem_text": problem_text}
            else:
                raise ValueError("API返回内容为空。")

        except Exception as e:
            error_str = str(e)
            
            # 检查是否是配额耗尽错误
            if "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                mark_key_exhausted(api_key)
                consecutive_quota_errors += 1
                
                # 如果连续多次配额错误，增加等待时间
                if consecutive_quota_errors >= 3:
                    wait_time = 30  # 等待30秒
                    print(f"  ⏳ 配额受限，等待 {wait_time} 秒后继续...")
                    time.sleep(wait_time)
                    consecutive_quota_errors = 0
                else:
                    time.sleep(delay)
            else:
                # 其他类型的错误
                error_message = f"API调用失败 (尝试 {attempt + 1}/{retries}): {e}"
                print(f"  ⚠️  {error_message}")
                time.sleep(delay)
            
            if attempt == retries - 1:
                return {"status": "error", "message": f"已达到最大重试次数: {error_str}", "problem_text": problem_text}
        
        time.sleep(delay)

    return {"status": "error", "message": "已达到最大重试次数", "problem_text": problem_text}


def batch_process_problems(input_dir, output_dir, example_dir, gdl_path, start_id=1, end_id=None, force_regenerate=False):
    """
    批量处理文件夹中的所有问题。
    新流程：输入文件夹包含部分填充的 .json 文件。
    
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
    
    # 将谓词列表格式化为字符串，以便注入提示
    valid_predicates_str = ", ".join(valid_predicates)

    # 从训练集加载few-shot范例（包含图片）
    train_dir = example_dir  # example_dir现在指向训练集目录
    images_dir = "src/fgps/formalgeo7k_v2/images"  # 图片目录
    # 使用10个few-shot样本（减少以节省输入token空间）
    few_shot_examples_data, example_count = load_few_shot_examples(train_dir, images_dir, max_examples=10)
    
    if example_count == 0:
        print("警告: 未能加载 few-shot 范例，将继续使用无范例的提示词。")
    
    # 构建范例文本（用于提示词，英文）
    examples_text = ""
    for i, example in enumerate(few_shot_examples_data, 1):
        img_note = f"Image: {example['problem_id']}.png" if example['image_base64'] else "No image"
        examples_text += f"""
#### Example {i} (ID: {example['problem_id']})
- problem_text: {example['problem_text']}
- {img_note}
- text_cdl: {example['text_cdl']}
- image_cdl: {example['image_cdl']}
- construction_cdl: {example['construction_cdl']}
- goal_cdl: {example['goal_cdl']}
- problem_answer: {example['problem_answer']}
"""
    
    # 动态构建黄金提示词
    golden_prompt = PROMPT_TEMPLATE.format(valid_predicates_str=valid_predicates_str)
    # 替换JSON示例占位符
    golden_prompt = golden_prompt.replace("JSON_EXAMPLE_PLACEHOLDER", JSON_EXAMPLE)
    if examples_text:
        golden_prompt += "\n--- Here are several high-quality examples. STRICTLY follow their format and logic. ---\n"
        golden_prompt += examples_text
    
    # 1. 修改：查找 .json 文件而不是 .txt 文件
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
    log_file_path = os.path.join(output_dir, "_generation_log.json")
    processed_problems = set()  # 已成功处理的问题ID集合
    log_data = []  # 日志数据
    
    # 如果强制重新生成，跳过加载已处理的问题
    if force_regenerate:
        print("🔄 强制重新生成模式：将重新生成所有问题，忽略已存在的输出。")
        # 可以选择备份旧的日志文件
        if os.path.exists(log_file_path):
            backup_path = log_file_path + ".backup"
            try:
                import shutil
                shutil.copy2(log_file_path, backup_path)
                print(f"📦 已备份现有日志到: {backup_path}")
            except Exception as e:
                print(f"⚠️  警告: 备份日志文件失败: {e}")
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
                print(f"📋 加载已有日志: 找到 {len(processed_problems)} 个已成功处理的问题，将从断点继续...")
            except Exception as e:
                print(f"⚠️  警告: 无法加载已有日志文件 '{log_file_path}': {e}，将从头开始处理。")
        
        # 检查输出目录中已存在的文件（即使日志中没有记录）
        if os.path.exists(output_dir):
            existing_output_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and f != '_generation_log.json']
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
    
    print(f"找到 {len(problem_files)} 个问题文件，过滤后 {len(filtered_files)} 个问题在范围内，其中 {len(processed_problems)} 个已处理，剩余 {len(remaining_files)} 个待处理。")
    
    if len(remaining_files) == 0:
        print("✅ 所有问题都已处理完成！")
        return
    
    # 2. 修改：循环并解析 .json 文件
    for idx, json_filename in enumerate(tqdm(remaining_files, desc="处理进度"), 1):
        problem_id_str = json_filename.split('.')[0]
        json_path = os.path.join(input_dir, json_filename)
        log_entry = {"problem_id": problem_id_str}
        
        # 显示当前处理进度
        if idx % 10 == 1 or idx == len(remaining_files):
            print(f"\n[{idx}/{len(remaining_files)}] 正在处理问题 {problem_id_str}...")

        try:
            # 3. 从JSON中读取 problem_text 和 image_path
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
                    print(f"警告: 无法从文件名 '{json_filename}' 中提取问题ID，已跳过。")
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
                    print(f"警告: 问题 {problem_id} 既没有图片也没有文本，已跳过。")
                    log_entry.update({"status": "skipped", "reason": f"No image and no text for problem_id {problem_id}"})
                    log_data.append(log_entry)
                    continue
                else:
                    # 只有文本没有图片，仍然可以处理（但会提示）
                    print(f"警告: 问题 {problem_id} 没有图片文件，将仅使用文本处理。")
                    image_path = None  # 设置为 None，后续会处理

        except (json.JSONDecodeError, KeyError) as e:
            print(f"警告: 解析JSON文件 '{json_filename}' 时出错: {e}，已跳过。")
            log_entry.update({"status": "skipped", "reason": f"Error reading source JSON: {e}"})
            log_data.append(log_entry)
            continue
        
        # 调用API生成（传入few-shot范例数据）
        print(f"  📤 调用API处理问题 {problem_id_str}...")
        # 如果 image_path 为 None，传递 None 而不是字符串
        result = generate_geometry_json(problem_text, image_path if image_path else None, golden_prompt, problem_id, few_shot_examples_data)
        
        # 显示处理结果
        if result["status"] == "success":
            print(f"  ✅ 问题 {problem_id_str} 处理成功")
        else:
            print(f"  ❌ 问题 {problem_id_str} 处理失败: {result.get('message', '未知错误')[:100]}")
        
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
            print(f"⚠️  警告: 保存日志文件失败: {e}")

    # 最终保存日志（确保所有数据都已保存）
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n批量处理完成！结果已保存在 '{output_dir}' 目录。")
    print(f"详细日志请见: '{log_file_path}'")


if __name__ == '__main__':
    # --- 请在这里配置您的文件夹路径 ---
    # 存放新问题（.json文件）的文件夹 - 直接从原始问题目录读取
    INPUT_PROBLEM_DIR = "src/fgps/formalgeo7k_v2/problems" 
    # 存放训练集（manual_train_set）的文件夹
    FEW_SHOT_EXAMPLE_DIR = "gemini/data/manual_train_set"
    # 存放AI生成结果的文件夹
    OUTPUT_DIR = "gemini/data/generated_output"
    # 谓词定义文件
    PREDICATE_GDL_PATH = "gemini/predicate_GDL.json"
    # 处理范围：1-700题目
    START_ID = 1
    END_ID = 700

    if not os.path.exists(INPUT_PROBLEM_DIR):
        print(f"错误: 输入目录不存在: {INPUT_PROBLEM_DIR}")
        exit(1)
    if not os.path.exists(FEW_SHOT_EXAMPLE_DIR):
        print(f"警告: 范例目录不存在: {FEW_SHOT_EXAMPLE_DIR}，将继续使用无范例的提示词。")
    
    # 是否强制重新生成所有问题（忽略已处理的标记）
    # 设置为 True 将重新生成所有问题，即使之前已经处理过
    FORCE_REGENERATE = False  # 设置为 True 以重新生成所有问题
    
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
