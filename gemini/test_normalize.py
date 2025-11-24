#!/usr/bin/env python3
"""Test the normalization function"""
import re

def normalize_cdl_element(element: str) -> str:
    """
    Normalize CDL elements for comparison with lenient matching.
    - Removes all spaces
    - Replaces all variables (but keeps numbers)
    - Standardizes to ignore variable naming and parameter count differences
    """
    # Remove all spaces
    normalized = element.strip().replace(' ', '')
    
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

# Test cases from the actual data
test_cases = [
    ("Equal(HeightOfCone(C1), 12)", "Equal(HeightOfCone(O,P),12)"),
    ("Equal(BusbarOfCone(C1), 13)", "Equal(BusbarOfCone(O,P),13)"),
    ("Value(DiameterOfCircle(O1))", "Value(DiameterOfCircle(O))"),
    ("Cone(C1)", "Cone(O,P)"),
    ("Circle(O1)", "IsCentreOfCircle(O,O)"),
]

print("="*80)
print("CDL Normalization Test")
print("="*80)

# Debug: trace through Equal(HeightOfCone(C1), 12)
print("\nDetailed trace for Test Case 1:")
test1_pred = "Equal(HeightOfCone(C1), 12)"
test1_gt = "Equal(HeightOfCone(O,P),12)"
print(f"Input 1: {test1_pred}")
print(f"  After space removal: {test1_pred.replace(' ', '')}")

# Manually trace
print("\nStep-by-step processing:")
print("  1. Innermost: HeightOfCone(C1) -> should become HeightOfCone(_V_)")
print("  2. Innermost: HeightOfCone(O,P) -> should become HeightOfCone(_V_)")  
print("  3. Outer: Equal(HeightOfCone(_V_), 12) and Equal(HeightOfCone(_V_),12) should match!")

for i, (pred, gt) in enumerate(test_cases, 1):
    norm_pred = normalize_cdl_element(pred)
    norm_gt = normalize_cdl_element(gt)
    match = norm_pred == norm_gt
    
    print(f"\nTest Case {i}:")
    print(f"  Predicted: {pred}")
    print(f"    -> Normalized: {norm_pred}")
    print(f"  Ground Truth: {gt}")
    print(f"    -> Normalized: {norm_gt}")
    print(f"  Match: {'YES' if match else 'NO'}")

print("\n" + "="*80)
