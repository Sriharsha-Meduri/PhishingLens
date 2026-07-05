#!/usr/bin/env python3
"""
Export trained text classification model to ONNX format.
Converts the fine-tuned DistilBERT model to ONNX for optimized inference.
"""

import torch
import torch.onnx
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from pathlib import Path
import onnx
import onnxruntime as ort
import numpy as np
import os

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = PROJECT_ROOT / 'models' / 'text'
ONNX_MODEL_PATH = MODELS_DIR / 'distilbert.onnx'

def export_model_to_onnx():
    """Export the trained model to ONNX format."""
    print("🚀 Exporting text classification model to ONNX...")
    
    try:
        # Load the trained model and tokenizer
        if not MODELS_DIR.exists():
            print(f"❌ Model directory not found: {MODELS_DIR}")
            print("Please run the training script first.")
            return False
        
        print(f"Loading model from {MODELS_DIR}")
        model = DistilBertForSequenceClassification.from_pretrained(MODELS_DIR)
        tokenizer = DistilBertTokenizer.from_pretrained(MODELS_DIR)
        
        # Set model to evaluation mode
        model.eval()
        
        # Create dummy input for ONNX export
        dummy_text = "This is a test message for ONNX export"
        dummy_inputs = tokenizer(
            dummy_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256
        )
        
        print("Exporting to ONNX format...")
        
        # Export to ONNX
        torch.onnx.export(
            model,
            (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
            ONNX_MODEL_PATH,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size"},
                "attention_mask": {0: "batch_size"},
                "logits": {0: "batch_size"}
            },
            verbose=False
        )
        
        print(f"✅ ONNX model exported to: {ONNX_MODEL_PATH}")
        
        # Verify the ONNX model
        verify_onnx_model()
        
        return True
        
    except Exception as e:
        print(f"❌ Error exporting to ONNX: {e}")
        return False

def verify_onnx_model():
    """Verify the exported ONNX model works correctly."""
    print("🔍 Verifying ONNX model...")
    
    try:
        # Load ONNX model
        onnx_model = onnx.load(ONNX_MODEL_PATH)
        onnx.checker.check_model(onnx_model)
        print("✅ ONNX model structure is valid")
        
        # Test inference with ONNX Runtime
        session = ort.InferenceSession(ONNX_MODEL_PATH)
        
        # Create test input
        tokenizer = DistilBertTokenizer.from_pretrained(MODELS_DIR)
        test_text = "Urgent: Verify your account immediately"
        inputs = tokenizer(
            test_text,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=256
        )
        
        # Run inference
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }
        
        outputs = session.run(None, onnx_inputs)
        logits = outputs[0]
        
        # Convert to probabilities
        probabilities = torch.softmax(torch.tensor(logits), dim=-1)
        prediction = torch.argmax(probabilities, dim=-1)
        
        print(f"✅ ONNX inference test successful")
        print(f"   Input: '{test_text}'")
        print(f"   Prediction: {'Phishing' if prediction.item() == 1 else 'Legitimate'}")
        print(f"   Confidence: {probabilities.max().item():.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ ONNX model verification failed: {e}")
        return False

def optimize_onnx_model():
    """Optimize the ONNX model for better performance."""
    print("⚡ Optimizing ONNX model...")
    
    try:
        # Load the model
        model = onnx.load(ONNX_MODEL_PATH)
        
        # Basic optimizations
        from onnx import optimizer
        
        # Get available optimizations
        passes = optimizer.get_available_passes()
        print(f"Available optimization passes: {len(passes)}")
        
        # Apply optimizations
        optimized_model = optimizer.optimize(model, passes)
        
        # Save optimized model
        optimized_path = MODELS_DIR / 'distilbert_optimized.onnx'
        onnx.save(optimized_model, optimized_path)
        
        print(f"✅ Optimized model saved to: {optimized_path}")
        
        # Compare model sizes
        original_size = ONNX_MODEL_PATH.stat().st_size / (1024 * 1024)  # MB
        optimized_size = optimized_path.stat().st_size / (1024 * 1024)  # MB
        
        print(f"📊 Model size comparison:")
        print(f"   Original: {original_size:.2f} MB")
        print(f"   Optimized: {optimized_size:.2f} MB")
        print(f"   Reduction: {((original_size - optimized_size) / original_size * 100):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Model optimization failed: {e}")
        return False

def create_model_metadata():
    """Create metadata file for the ONNX model."""
    print("📝 Creating model metadata...")
    
    try:
        metadata = {
            "model_name": "distilbert-phishing-detection",
            "version": "1.0.0",
            "format": "onnx",
            "opset_version": 11,
            "input_shape": {
                "input_ids": [1, 256],
                "attention_mask": [1, 256]
            },
            "output_shape": {
                "logits": [1, 2]
            },
            "classes": ["legitimate", "phishing"],
            "max_sequence_length": 256,
            "exported_at": torch.utils.data.get_worker_info() or "unknown",
            "framework": "pytorch",
            "optimized": True
        }
        
        import json
        from datetime import datetime
        metadata["exported_at"] = datetime.now().isoformat()
        
        metadata_path = MODELS_DIR / 'model_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Metadata saved to: {metadata_path}")
        return True
        
    except Exception as e:
        print(f"❌ Metadata creation failed: {e}")
        return False

def main():
    """Main export function."""
    print("🚀 Starting ONNX export for text classification model...")
    print("=" * 60)
    
    try:
        # Export model
        if not export_model_to_onnx():
            print("❌ ONNX export failed")
            return False
        
        # Verify model
        if not verify_onnx_model():
            print("❌ ONNX verification failed")
            return False
        
        # Optimize model
        optimize_onnx_model()
        
        # Create metadata
        create_model_metadata()
        
        print("\n" + "=" * 60)
        print("✅ ONNX export complete!")
        print(f"📁 Model location: {ONNX_MODEL_PATH}")
        print("🎯 Ready for production deployment!")
        
        return True
        
    except Exception as e:
        print(f"❌ Export process failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
