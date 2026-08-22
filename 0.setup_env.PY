import os
import subprocess
import sys
import shutil
import urllib.request
import zipfile

def ensure_python_environment():
    """Multi-tier Python availability checker and auto-installer."""
    python_cmd = shutil.which("python") or shutil.which("py")
    
    if python_cmd:
        print(f"[INFO] Active Python environment detected at: {python_cmd}")
        return python_cmd

    print("\n" + "="*70)
    print(" ⚠️  WARNING: Python not found on system PATH! Initiating auto-recovery... ")
    print("="*70)

    # Method 1: Try Winget (Windows Package Manager)
    print("\n[1/2] Attempting automatic installation via Windows Package Manager (Winget)...")
    winget_check = subprocess.run("winget --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if winget_check.returncode == 0:
        print("-> Winget detected. Installing Python 3.11 silently...")
        install_res = subprocess.run("winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements", shell=True)
        if install_res.returncode == 0:
            print("[SUCCESS] Python successfully installed via Winget! Please restart your terminal/script.")
            input("Press Enter to exit, then restart the script...")
            sys.exit(0)
    else:
        print("[-] Winget command not available on this system.")

    # Method 2: Fallback to Microsoft Store URI
    print("\n[2/2] Launching Microsoft Store Python package installer...")
    try:
        os.system("start ms-windows-store://p?productid=9NRPTZXMB4ZI")
    except Exception:
        pass

    print("\n" + "!"*70)
    print(" CRITICAL ACTION REQUIRED:")
    print(" 1. Install Python from the Microsoft Store window that opened.")
    print(" 2. Ensure 'Add Python to PATH' is checked if using an installer.")
    print(" 3. Re-open your terminal and rerun this setup script.")
    print("!"*70)
    input("\nPress Enter to exit...")
    sys.exit(1)

def run_cmd(command, python_exe=None):
    if python_exe and not command.startswith(f'"{python_exe}"'):
        command = command.replace(f"{sys.executable}", f'"{python_exe}"')
        command = command.replace("python ", f'"{python_exe}" ')
    print(f"\n[EXEC] {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
        return False
    return True

def download_file(url, output_path):
    print(f"\n[INFO] Downloading from: {url}")
    print("[INFO] This file can be large. Please wait, do not close...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r[DOWNLOAD] {percent}% completed...")
                sys.stdout.flush()
        
        urllib.request.urlretrieve(url, output_path, reporthook)
        print("\n[SUCCESS] Download completed successfully!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False

def bootstrap_local_python():
    local_py_dir = os.path.abspath("local_runtime")
    python_exe = os.path.join(local_py_dir, "python.exe")
    
    if os.path.exists(python_exe):
        print(f"[INFO] Local standalone Python runtime active at: {local_py_dir}")
        return python_exe

    print("="*70)
    print(" 🚀 BOOTSTRAPPING LOCAL PYTHON RUNTIME (Bypassing System Flashes) 🚀")
    print("="*70)
    
    os.makedirs(local_py_dir, exist_ok=True)
    py_zip_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    zip_path = "python_embed.zip"
    
    if not os.path.exists(zip_path):
        if not download_file(py_zip_url, zip_path):
            sys.exit(1)
            
    print("\n[INFO] Extracting portable Python runtime...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(local_py_dir)
        
    print("[INFO] Configuring runtime path flags...")
    for file in os.listdir(local_py_dir):
        if file.endswith("._pth"):
            pth_file = os.path.join(local_py_dir, file)
            with open(pth_file, "r") as f:
                content = f.read()
            if "#import site" in content:
                content = content.replace("#import site", "import site")
            if "Lib\\site-packages" not in content:
                content += "\nLib\\site-packages\n"
            with open(pth_file, "w") as f:
                f.write(content)
            break

    get_pip_path = "get-pip.py"
    if not os.path.exists(get_pip_path):
        download_file("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
        
    print("\n[INFO] Installing pip into local runtime...")
    subprocess.run(f'"{python_exe}" get-pip.py --no-warn-script-location', shell=True)
    print("[SUCCESS] Local runtime bootstrapped!")
    return python_exe

def check_or_fetch_cuda(version_choice):
    cuda_configs = {
        "9": {"ver": "13.0", "url": "https://developer.download.nvidia.com/compute/cuda/13.0.0/local_installers/cuda_13.0.0_windows.exe", "file": "cuda_13.0_installer.exe"},
        "10": {"ver": "12.8", "url": "https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_windows.exe", "file": "cuda_12.8_installer.exe"},
        "11": {"ver": "12.4", "url": "https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda_12.4.0_windows.exe", "file": "cuda_12.4_installer.exe"},
        "12": {"ver": "12.0", "url": "https://developer.download.nvidia.com/compute/cuda/12.0.0/local_installers/cuda_12.0.0_windows.exe", "file": "cuda_12.0_installer.exe"}
    }
    
    cfg = cuda_configs.get(version_choice)
    if not cfg:
        return False

    print(f"\n[WARNING] CUSTOM CUDA {cfg['ver']} SOURCE BUILD SELECTED:")
    print("------------------------------------------------------------------")
    print("⚠️  STORAGE WARNING: The official CUDA Toolkit installer is large (~3GB to 5GB+).")
    print("⚠️  TIME WARNING: Compiling C++ binaries locally via CMake takes 5-15+ minutes.")
    print("------------------------------------------------------------------")
    
    proceed = input("Do you wish to download the CUDA toolkit and proceed? (y/n) [Default: n]: ").strip().lower()
    if proceed != 'y':
        print("[INFO] Custom CUDA download cancelled by user. Falling back to CPU wheel...")
        return False

    local_installer = cfg['file']
    if not os.path.exists(local_installer):
        success = download_file(cfg['url'], local_installer)
        if not success:
            return False
    else:
        print(f"\n[INFO] Found existing local installer package: {local_installer}")

    print(f"\n[INFO] Launching extraction for CUDA {cfg['ver']}...")
    subprocess.run(f"{local_installer} -s", shell=True)
    return True

def create_smart_batch_file():
    """Generates 3.ocr-AIO.bat with parent-directory fallback support."""
    batch_content = """@echo off
:: 1. Move to the directory where this batch file lives
cd /d "%~dp0"

:: 2. Intelligently look for the 'quizenv' virtual environment one step back (parent dir) or locally
if exist "..\\quizenv\\Scripts\\activate.bat" (
    call "..\\quizenv\\Scripts\\activate.bat"
    echo 📂 [INFO]: Found 'quizenv' in parent directory.
) else if exist "quizenv\\Scripts\\activate.bat" (
    call "quizenv\\Scripts\\activate.bat"
    echo 📂 [INFO]: Found 'quizenv' in current directory.
) else (
    echo ❌ [ERROR]: Could not find 'quizenv' virtual environment!
    echo Please make sure 0.setup_env.py has been run in the root folder.
    pause
    exit /b
)

:: 3. Run target Python script seamlessly
echo 🚀 Running OCR Application via isolated environment...
python 4.ocr-AIO.py

pause
"""
    with open("4.ocr-AIO.bat", "w", encoding="utf-8") as f:
        f.write(batch_content.strip())
    print("\n[INFO] Successfully generated smart launcher: 4.ocr-AIO.bat")

def main():
    # 0. Ensure system Python is present or auto-install via Winget/Store
    ensure_python_environment()

    # Bootstrap local runtime for dependency compilation if needed
    bootstrap_local_python()

    print("="*70)
    print(" 🚀 INCEPTION QUIZ: MASTER WORKSPACE & ENGINE SETUP 🚀")
    print("="*70)

    venv_dir = "quizenv"
    print(f"\n[1/4] Creating isolated virtual environment ({venv_dir}) via system Python...")
    
    success = run_cmd(f'"{sys.executable}" -m venv {venv_dir}')
    if not success:
        print("[ERROR] Failed to create virtual environment using system Python.")
        sys.exit(1)

    venv_python = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(venv_dir, "bin", "python")

    print("\n[2/4] Upgrading pip and installing core project requirements...")
    run_cmd(f'"{venv_python}" -m pip install --upgrade pip')
    if os.path.exists("requirements.txt"):
        run_cmd(f'"{venv_python}" -m pip install --no-cache-dir -r requirements.txt')
    else:
        run_cmd(f'"{venv_python}" -m pip install --no-cache-dir pillow numpy diskcache jinja2')

    print("\n" + "="*70)
    print(" CHOOSE YOUR INFERENCE ACCELERATION BACKEND:")
    print("------------------------------------------------------------------")
    print(" --- PREBUILT BINARY WHEELS (Instant Setup, No Compiler Needed) ---")
    print(" [1] Prebuilt CUDA 13.0 Wheel (NVIDIA GPU)")
    print(" [2] Prebuilt CUDA 12.5 Wheel (NVIDIA GPU)")
    print(" [3] Prebuilt CUDA 12.4 Wheel (NVIDIA GPU - Recommended)")
    print(" [4] Prebuilt CUDA 12.3 Wheel (NVIDIA GPU)")
    print(" [5] Prebuilt CUDA 12.2 Wheel (NVIDIA GPU)")
    print(" [6] Prebuilt CUDA 12.1 Wheel (NVIDIA GPU)")
    print(" [7] Prebuilt CUDA 11.8 Wheel (NVIDIA GPU)")
    print(" [8] Prebuilt Metal Wheel (Apple Silicon macOS)")
    print("------------------------------------------------------------------")
    print(" --- CUSTOM SOURCE BUILDS (Downloads SDK Toolkit & Compiles) ---")
    print(" [9]  Custom Build: CUDA 13.x Source (High Disk & Time Usage)")
    print(" [10] Custom Build: CUDA 12.8 Source (High Disk & Time Usage)")
    print(" [11] Custom Build: CUDA 12.4 Source (High Disk & Time Usage)")
    print(" [12] Custom Build: CUDA 12.0 Source (High Disk & Time Usage)")
    print(" [13] Custom Build: OpenBLAS CPU Acceleration")
    print(" [14] Custom Build: Metal GPU (macOS)")
    print("------------------------------------------------------------------")
    print(" [15] Standard CPU-Only Prebuilt Wheel (Instant, Lightweight, Default)")
    print("="*70)

    choice = input("Select your backend option (1-15) [Default: 15]: ").strip()
    print("\n[4/4] Configuring Local GGUF Vision OCR Engine...")

    prebuilt_map = {
        "1": "cu130", "2": "cu125", "3": "cu124", "4": "cu123",
        "5": "cu122", "6": "cu121", "7": "cu118", "8": "metal"
    }

    if choice in prebuilt_map:
        tag = prebuilt_map[choice]
        print(f"-> Installing prebuilt wheel for target [{tag}]...")
        success = run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/{tag}')
        if not success:
            print(f"[WARNING] Wheel installation for [{tag}] failed. Falling back to CPU wheel...")
            run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')

    elif choice in ["9", "10", "11", "12"]:
        cuda_ready = check_or_fetch_cuda(choice)
        if cuda_ready:
            print("\n[NOTICE] Initiating Custom Source Build with local CUDA environment...")
            os.environ["CMAKE_ARGS"] = "-DGGML_CUDA=on"
            success = run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --force-reinstall --no-build-isolation')
            if not success:
                run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')
        else:
            run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')

    elif choice == "13":
        print("\n[NOTICE] Initiating Source Build with OpenBLAS...")
        os.environ["CMAKE_ARGS"] = "-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"
        success = run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --force-reinstall --no-build-isolation')
        if not success:
            run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')

    elif choice == "14":
        print("\n[NOTICE] Initiating Source Build with Metal GPU (macOS)...")
        os.environ["CMAKE_ARGS"] = "-DGGML_METAL=on"
        success = run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --force-reinstall --no-build-isolation')
        if not success:
            run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')

    else:
        print("-> Selecting standard CPU-only prebuilt wheel (Instant setup)...")
        run_cmd(f'"{venv_python}" -m pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu')

    # Automatically generate the smart batch runner
    create_smart_batch_file()

    print("\n" + "="*70)
    print(" ✅ SETUP COMPLETED SUCCESSFULLY! WORKSPACE IS READY FOR LAUNCH.")
    print("="*70)
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()