# 🌌 Inception Quiz Builder Framework 🚀

Welcome to the **Inception Quiz Builder Framework**—an advanced, multi-modal vision OCR and web-based interactive assessment platform[cite: 11]. It utilizes a structured, two-tier architecture powered by local GGUF vision models, separating your master setup environment from your working assessment directory[cite: 1, 7, 9].

---

## 🎛️ Phase 1: Root Base Folder Setup (Control Center)

When you first clone or extract the repository, the root directory acts as your central configuration and bootstrapping control center[cite: 7, 8, 9]. Follow the numbered file sequence below:

### 🔹 Step 0: Environment Bootstrapping (`0.setup_env.PY`) 🐍
* Automatically boots up a local standalone Python runtime to isolate your environment and avoid host system flashing bugs[cite: 9].
* Creates an isolated virtual environment directory named `quizenv` and upgrades pip[cite: 9].
* Automatically installs core project dependencies including `pillow`, `numpy`, `diskcache`, and `jinja2`[cite: 1, 9].
* Presents an interactive hardware acceleration choice menu for the local GGUF vision engine (`llama-cpp-python`), letting you pick prebuilt CUDA/Metal binary wheels, custom source builds, or standard CPU-only wheels[cite: 9].

### 🔹 Step 1: Framework Generation (`2.inception_builder.py` / Step 1) 🏗️
* Serves as the master engine builder script that prompts you interactively for custom parameters like grades, subjects, years, and exam types/levels[cite: 11].
* Creates a dedicated standalone working directory named `inceptionquiz/`[cite: 11].
* Dynamically rewrites and patches the Python creator script (`yourquizjsoncreator.py`), the HTML web layout (`spawn.html`), and the JavaScript routing (`quizlogic.js`) to match your customized user settings[cite: 11].

> **📂 Transition Note (`2a.NOW go to inceptionquiz folder and run steps 3,4,5,6`)**: Navigate into your newly generated `inceptionquiz/` workspace to continue authoring content and managing assessments[cite: 9, 11].

---

## 📂 Phase 2: Working Directory & Content Authoring (`inceptionquiz/`)

Inside your working folder, use the following numbered tools to create, organize, and process your question banks:

### 🔹 Step 3: OCR Creator Launcher (`3.ocr-AIO.bat`) 🚀
* A smart Windows batch wrapper that automatically steps back to locate the root `quizenv` virtual environment and launches the multimodal OCR application cleanly.

### 🔹 Step 4: Vision Model Configuration (`4.model_manager.py`) 👁️
* Opens a graphical Vision Model Manager interface window.
* Allows you to browse and select your local **GGUF Model** file and **MMPROJ File** paths[cite: 10, 19].
* Saves these file paths directly into a `model_config.json` configuration file so that the OCR vision engine can read them globally[cite: 1, 10].

### 🔹 Step 5: Serial-Numbered Chapter Generation (`5.Setup-multiple-JSON.PY`) 📦
* Collects multi-line chapter names, strips punctuation/parentheses via slugification, and generates clean, serial-numbered JSON question bank files pre-loaded with empty arrays[cite: 4, 7].

### 🔹 Step 6: Topic Index Refresh & Cleanup (`6.RefreshYourTopicsJSON.py`) 🔄
* Scans the current directory for JSON files, converts snake-case or kebab-case filenames into readable Title Case chapter names[cite: 3, 16].
* Features an automated post-build cleanup filter that strips out system configuration files like `model_config.json`, keeping your dropdown UI pristine[cite: 14, 16].
* Sorts chapters alphabetically and builds the `topics.json` index file[cite: 3, 16].

### 🧠 The OCR & Authoring Core (`ocr-AIO.py`)
* **Desktop GUI App**: Launches an interface to create, edit, and save assessment questions[cite: 1].
* **Target Database Manager 🗄️**: Select, refresh, switch, or create new target JSON database files directly inside the application[cite: 1].
* **Built-in Screen Sniper (`ScreenSniper`) ✂️**: Takes full-screen snapshots and lets you crop custom regions to pass raw images directly into the multimodal vision engine[cite: 1].
* **Advanced OCR Capabilities 🧠**: Supports targeted single-widget OCR extraction, automated batch MCQ options analysis with JSON extraction, 10-line explanation line-splitting, and unconstrained step-by-step math proof generation[cite: 1].
* **Graphic Resource Management 🖼️**: Captures optional question or explanation graphics, converts them to high-quality JPEGs, saves them into an `images/` folder using unique UUID tokens, and stores relative file paths in the JSON record[cite: 1].
* **Comprehensive Data Schema Support 📊**: Handles Multiple Choice Questions (MCQ), Matrix Matching, Numerical/Integer evaluation answers, and Subjective derivations[cite: 1].

---

## 🌐 Phase 3: Launching the Web Assessment Arena (`spawn.html`)

### ⚠️ Local Hosting Requirement
Because the web framework fetches JSON data dynamically (`topics.json` and chapter banks), opening `spawn.html` directly by double-clicking (`file://`) triggers browser CORS security restrictions. You **must** host it locally using one of the options below:

* **Option A (Quick CLI Command) 💻**: Open your terminal inside the folder and run Python's built-in server:
  ```bash
  python -m http.server 8000