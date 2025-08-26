import sys
import subprocess

print("=== System Info ===")
print(f"Python: {sys.version}")
print(f"Python Path: {sys.executable}")

# Check nvidia-smi
print("\n=== NVIDIA SMI ===")
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    print("NVIDIA Driver Found")
except:
    print("NVIDIA Driver NOT Found")

# Check PyTorch
print("\n=== PyTorch Info ===")
try:
    import torch
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"cuDNN Version: {torch.backends.cudnn.version()}")
        print(f"GPU Count: {torch.cuda.device_count()}")
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA is NOT available in PyTorch")
        print("This is likely a CPU-only build")
        
        # Check if CUDA runtime is available
        print("\nChecking CUDA runtime...")
        try:
            import ctypes
            cuda = ctypes.CDLL("cudart64_110.dll")
            print("CUDA runtime DLL found")
        except:
            print("CUDA runtime DLL NOT found")
            
except ImportError as e:
    print(f"PyTorch import error: {e}")

# Show installed packages
print("\n=== Installed PyTorch Packages ===")
result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'torch'], capture_output=True, text=True)
print(result.stdout)