#!/usr/bin/env python3
"""
测试API连接和配置
快速验证各个模型的API是否可用
"""

import os
import sys
import json
import base64
from pathlib import Path

def test_chatgpt_api():
    """测试ChatGPT API连接"""
    print("\n" + "="*60)
    print("测试 ChatGPT API")
    print("="*60)
    
    try:
        from openai import OpenAI
        
        OPENAI_API_KEY = "sk-zjNMg4BgRLaUy2LqaGGlggpvNcnSWzo3ejIosJGrZE92eNdX"
        OPENAI_API_BASE = "https://aicanapi.com/v1"
        
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )
        
        # 简单的文本测试
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "请用一句话回答：1+1等于几？"}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print("[OK] ChatGPT API 连接成功!")
        print(f"测试响应: {result}")
        return True
        
    except Exception as e:
        print(f"[X] ChatGPT API 连接失败: {e}")
        return False

def test_deepseek_api():
    """测试DeepSeek API连接"""
    print("\n" + "="*60)
    print("测试 DeepSeek API")
    print("="*60)
    
    try:
        from openai import OpenAI
        
        DEEPSEEK_API_KEY = "sk-zjNMg4BgRLaUy2LqaGGlggpvNcnSWzo3ejIosJGrZE92eNdX"
        DEEPSEEK_API_BASE = "https://aicanapi.com/v1"
        DEEPSEEK_MODEL = "gpt-4o-mini"  # 使用GPT-4o-mini
        
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_BASE
        )
        
        # 简单的文本测试
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "user", "content": "请用一句话回答：2+2等于几？"}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print("[OK] DeepSeek API 连接成功! (使用Qwen2-VL模型)")
        print(f"测试响应: {result}")
        return True
        
    except Exception as e:
        print(f"[X] DeepSeek API 连接失败: {e}")
        return False

def test_gemini_api():
    """测试Gemini API连接"""
    print("\n" + "="*60)
    print("测试 Gemini API")
    print("="*60)
    
    try:
        import google.generativeai as genai
        
        GOOGLE_API_KEY = "AIzaSyBdORqV1tT5hbe5gii8KwPis-ac2IFt73Y"
        genai.configure(api_key=GOOGLE_API_KEY)
        
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # 简单的文本测试
        response = model.generate_content("请用一句话回答：3+3等于几？")
        
        result = response.text
        print("[OK] Gemini API 连接成功!")
        print(f"测试响应: {result}")
        return True
        
    except Exception as e:
        print(f"[X] Gemini API 连接失败: {e}")
        return False

def test_file_structure():
    """测试文件结构是否完整"""
    print("\n" + "="*60)
    print("检查文件结构")
    print("="*60)
    
    required_paths = [
        "gemini/data/new_problems",
        "gemini/data/examples",
        "gemini/predicate_GDL.json",
        "gemini/images"
    ]
    
    all_ok = True
    for path in required_paths:
        if os.path.exists(path):
            print(f"[OK] {path} - 存在")
        else:
            print(f"[X] {path} - 不存在")
            all_ok = False
    
    return all_ok

def test_json_format():
    """测试JSON输出格式"""
    print("\n" + "="*60)
    print("测试JSON格式解析")
    print("="*60)
    
    try:
        from pydantic import BaseModel, Field
        from typing import List
        
        class ProblemSchema(BaseModel):
            problem_id: int = Field(description="问题ID")
            construction_cdl: List[str] = Field(description="构造CDL")
            text_cdl: List[str] = Field(description="文本CDL")
            image_cdl: List[str] = Field(description="图片CDL")
            goal_cdl: str = Field(description="目标CDL")
            problem_answer: str = Field(description="答案")
        
        # 测试数据
        test_data = {
            "problem_id": 1,
            "construction_cdl": [],
            "text_cdl": ["Equal(RadiusOfSphere(O),5)"],
            "image_cdl": ["Equal(LengthOfLine(A,B),10)"],
            "goal_cdl": "Value(VolumeOfSphere(O))",
            "problem_answer": "523.6"
        }
        
        validated = ProblemSchema(**test_data)
        print("[OK] JSON格式验证成功!")
        print(f"示例: {validated.dict()}")
        return True
        
    except Exception as e:
        print(f"[X] JSON格式验证失败: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("API连接和配置测试工具")
    print("="*60)
    
    results = {}
    
    # 测试文件结构
    results['file_structure'] = test_file_structure()
    
    # 测试JSON格式
    results['json_format'] = test_json_format()
    
    # 测试各个API
    results['chatgpt'] = test_chatgpt_api()
    results['deepseek'] = test_deepseek_api()
    results['gemini'] = test_gemini_api()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[OK] 通过" if result else "[X] 失败"
        print(f"{test_name:<20}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] 所有测试通过! 可以开始运行模型。")
        print("\n下一步:")
        print("  1. 准备输入数据到 gemini/data/new_problems/")
        print("  2. 运行单个模型: python gemini/chatgpt_pro.py")
        print("  3. 或运行所有模型: python gemini/run_all_models.py --models all")
    else:
        print("[X] 部分测试失败，请检查配置。")
        print("\n常见问题:")
        print("  - API密钥是否正确？")
        print("  - 网络连接是否正常？")
        print("  - 依赖包是否已安装？")
        print("    pip install openai google-generativeai pillow tqdm pydantic")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

