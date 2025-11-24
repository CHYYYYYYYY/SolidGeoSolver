#!/usr/bin/env python3
"""
Quick test script for Gemini CDL evaluation

This script helps test the evaluation functionality with the actual data directories.
"""

import os
import sys
from pathlib import Path

def test_evaluation():
    """Test the evaluation script with default paths."""
    
    # Get the script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Default paths
    gt_dir = project_root / "src" / "fgps" / "formalgeo7k_v2" / "problems"
    pred_dir = script_dir / "data" / "generated_output"
    
    print("="*80)
    print("Gemini CDL Evaluation Test")
    print("="*80)
    print(f"\nGround Truth Directory: {gt_dir}")
    print(f"Prediction Directory: {pred_dir}")
    
    # Check if directories exist
    if not gt_dir.exists():
        print(f"\n❌ Error: Ground truth directory not found: {gt_dir}")
        print("Please ensure the path is correct.")
        return False
    
    if not pred_dir.exists():
        print(f"\n❌ Error: Prediction directory not found: {pred_dir}")
        print("Please ensure Gemini has generated some output files.")
        return False
    
    # Count files
    gt_files = list(gt_dir.glob("*.json"))
    pred_files = [f for f in pred_dir.glob("*.json") if not f.name.startswith("_")]
    
    print(f"\nFound {len(gt_files)} ground truth files")
    print(f"Found {len(pred_files)} prediction files")
    
    if len(pred_files) == 0:
        print("\n⚠️  Warning: No prediction files found in the output directory.")
        print("Please run Gemini generation first.")
        return False
    
    # Import and run evaluation
    print("\n" + "="*80)
    print("Running evaluation...")
    print("="*80 + "\n")
    
    original_dir = os.getcwd()
    try:
        # Change to script directory to import the module
        os.chdir(script_dir)
        sys.path.insert(0, str(script_dir))
        
        # Try importing using importlib to avoid cache issues
        import importlib.util
        spec = importlib.util.spec_from_file_location("evaluate_cdl", script_dir / "evaluate_cdl.py")
        evaluate_cdl_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluate_cdl_module)
        
        evaluator_class = evaluate_cdl_module.GeminiCDLEvaluator
        
        evaluator = evaluator_class()
        metrics = evaluator.evaluate_dataset(str(gt_dir), str(pred_dir))
        
        if metrics:
            evaluator.print_results(metrics)
            
            # Save results
            output_file = script_dir / "evaluation_results.json"
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2)
            print(f"\n✅ Results saved to: {output_file}")
            
            return True
        else:
            print("\n❌ Evaluation failed. Please check the error messages above.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original directory
        try:
            os.chdir(original_dir)
        except Exception:
            pass


if __name__ == "__main__":
    success = test_evaluation()
    sys.exit(0 if success else 1)

