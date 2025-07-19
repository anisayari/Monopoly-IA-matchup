#!/usr/bin/env python3
"""Test GPU availability in OmniParser environment"""
import torch
import sys

print("=== GPU Test for OmniParser ===")
print(f"Python version: {sys.version}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"cuDNN version: {torch.backends.cudnn.version()}")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    print(f"Current GPU: {torch.cuda.current_device()}")
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("❌ CUDA not available - will use CPU (slower)")
    
# Test a simple operation
print("\n=== Testing GPU computation ===")
try:
    if torch.cuda.is_available():
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.matmul(x, y)
        print("✅ GPU computation successful!")
    else:
        print("⚠️ Running on CPU")
except Exception as e:
    print(f"❌ GPU computation failed: {e}")