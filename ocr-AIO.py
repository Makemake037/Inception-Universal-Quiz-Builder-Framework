import json
import os
import glob
import re
import io
import base64
import uuid
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import threading
from PIL import Image, ImageTk, ImageGrab
import sys

# --- GGUF VERSION ENGINE IMPORTS ---
try:
    from llama_cpp import Llama
    print("--> llama-cpp-python Engine Loaded Successfully!")
except Exception as ie:
    import traceback
    print(f"\n[CRITICAL IMPORT ERROR DETECTED]:")
    traceback.print_exc()
    print(f"\nOriginal Exception Message: {ie}\n")
    Llama = None


def clean_ocr_question(raw_text):
    # Replace 3 or more consecutive underscores with a clean placeholder
    cleaned_text = re.sub(r'_{3,}', '[BLANK]', raw_text)
    return cleaned_text

# --- MERGED MULTIMODAL OCR ENGINE ---


class UnifiedVisionOCR:
    def __init__(self):
        self.model_path = ""
        self.mmproj_path = ""
        self.model = None

        # Silently load paths configured by model_manager.py
        try:
            with open("model_config.json", "r") as f:
                config = json.load(f)
                # Ensure Windows handles long paths automatically
                self.model_path = config.get("gguf", "")
                self.mmproj_path = config.get("mmproj", "")

                # Auto-inject long path prefix if needed for Windows
                if len(self.model_path) > 250 and not self.model_path.startswith("\\\\?\\"):
                    self.model_path = "\\\\?\\" + self.model_path
                if len(self.mmproj_path) > 250 and not self.mmproj_path.startswith("\\\\?\\"):
                    self.mmproj_path = "\\\\?\\" + self.mmproj_path

        except Exception as e:
            print(f"[WARNING] Could not read model_config.json. Did you run model_manager.py first? Error: {e}")

    # PROPERLY ALIGNED AT THE CLASS LEVEL (4 spaces)
    def _clean_output(self, text):
        """Helper method to filter out leaked chat control sequences globally."""
        if not isinstance(text, str):
            return text
        cleaned = re.sub(r'<\|im_end\|>|<\|im_start\|>(?:assistant|user)?', '', text)
        return cleaned.strip()

    def load_model(self):
        if self.model is not None:
            return
        if Llama is None:
            print("Error: llama-cpp-python library missing in this environment.")
            return

        print(f"Loading Vision Engine from {self.model_path}...")

        try:
            # Dynamic template selector to find the exact correct chat layout
            # safely
            chat_handler = None
            try:
                from llama_cpp.llama_chat_format import Gemma4ChatHandler  # type: ignore
                chat_handler = Gemma4ChatHandler(
                    clip_model_path=self.mmproj_path)
            except (ImportError, AttributeError):
                try:
                    from llama_cpp.llama_chat_format import Gemma3ChatHandler  # type: ignore
                    chat_handler = Gemma3ChatHandler(
                        clip_model_path=self.mmproj_path)
                except (ImportError, AttributeError):
                    try:
                        from llama_cpp.llama_chat_format import Llava15ChatHandler  # type: ignore
                        chat_handler = Llava15ChatHandler(
                            clip_model_path=self.mmproj_path)
                    except (ImportError, AttributeError):
                        try:
                            from llama_cpp.llama_chat_format import Qwen25VLChatHandler  # type: ignore
                            chat_handler = Qwen25VLChatHandler(
                                clip_model_path=self.mmproj_path)
                        except (ImportError, AttributeError):
                            print(
                                "Critical Error: No multimodal chat handlers found.")
                            return

            # Context size set to 8192 to avoid clipping large math text
            # responses
            self.model = Llama(
                model_path=self.model_path,
                chat_handler=chat_handler,
                n_ctx=8192,
                n_gpu_layers=-1,
                flash_attn=True,
                verbose=False,
                model_kwargs={"no_kv_offload": True, "use_gpu_graphs": False}
            )
            print("Engine successfully claimed Dedicated VRAM!")

        except Exception as e:
            print(f"[CRITICAL INITIALIZATION FAILURE]: {e}")
            self.model = None

    def _preprocess_image(self, image):
        """Compression stripped away. Passes raw, full-resolution image to the engine.[cite: 11]"""
        if image is None:
            return image
        return image

    def _image_to_base64_uri(self, image):
        """Converts PIL Image data to a base64 Data URI."""
        buffered = io.BytesIO()
        image.convert("RGB").save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    def run_ocr(self, image):
        image = self._preprocess_image(image)
        self.load_model()
        if self.model is None:
            return "Error: Engine Not Loaded."

        base64_uri = self._image_to_base64_uri(image)
        prompt_text = "Extract all text including formulas from this image exactly as they appear cleanly using standard LaTeX notation ($...$). Pay close attention to mathematical arrows or implication signs. Do not append extra commentary or explanations."

        try:
            response = self.model.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": base64_uri}}
                        ]
                    }
                ],
                max_tokens=2048,
                temperature=0.1
            )
            content = response["choices"][0]["message"]["content"]
            return self._clean_output(content)
        except Exception as e:
            return f"Engine Inference Error: {e}"

    def analyze_4_options_and_answer(self, image):
        """Batch analyze options and extract answer[cite: 10]"""
        image = self._preprocess_image(image)
        self.load_model()
        if self.model is None:
            return None

        base64_uri = self._image_to_base64_uri(image)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this multiple choice options block image. Perform two tasks:\n"
                            "1. Extract the exact text for each of the 4 options sequentially.\n"
                            "2. Detect which option circle has a green or blue color border, green or blue dot, or is active/selected.\n"
                            "Return the response strictly as a valid JSON object containing exactly two keys: "
                            "\"options\" (a list of 4 strings) and \"answer\" (a single lowercase letter string: \"a\", \"b\", \"c\", or \"d\"). "
                            "Do not include markdown tags or wrap with extra code strings."
                        )
                    },
                    {"type": "image_url", "image_url": {"url": base64_uri}}
                ]
            }
        ]

        try:
            response = self.model.create_chat_completion(
                messages=messages,
                max_tokens=2048,
                # Enforce absolute determinism to minimize JSON structure
                # variations[cite: 10]
                temperature=0.0
            )
            content = response["choices"][0]["message"]["content"]
            content = self._clean_output(content)

            print("\n--- DEBUG OPTION OCR RAW OUTPUT ---")
            print(content)
            print("-----------------------------------\n")

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                content = re.sub(r'\}\s*\{', ', ', content)

            return json.loads(content)
        except Exception as e:
            print(f"Error parsing json: {e}")
            return None

    def run_step_by_step_explanation(self, image):
        image = self._preprocess_image(image)
        self.load_model()
        if self.model is None:
            return "Error: Engine Not Loaded."

        base64_uri = self._image_to_base64_uri(image)
        prompt_text = "Solve this problem step-by-step. Use standard Markdown for lists and headings. Use `$math$` ONLY for equations, variables, and units. End explicitly with the final Answer. No extra commentary."

        try:
            response = self.model.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": base64_uri}}
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )
            content = response["choices"][0]["message"]["content"]
            return self._clean_output(content)
        except Exception as e:
            return f"Engine Inference Error: {e}"


# Initialize core model wrapper
QWEN_ENGINE = UnifiedVisionOCR()


def wrap_text_at_limit(text, limit=40):
    if not text:
        return ""
    paragraphs = text.split("\n")
    wrapped_paragraphs = []
    for para in paragraphs:
        if not para.strip():
            wrapped_paragraphs.append("")
            continue
        chunks = [para[i: i + limit] for i in range(0, len(para), limit)]
        wrapped_paragraphs.extend(chunks)
    return "\n".join(wrapped_paragraphs)


def determine_json_filename():
    current_dir = (
        os.path.dirname(os.path.abspath(__file__))
        if "__file__" in locals()
        else os.getcwd()
    )
    html_files = glob.glob(os.path.join(current_dir, "*.html"))
    return (
        f"{os.path.splitext(os.path.basename(html_files[0]))[0]}.json"
        if html_files
        else "question_bank.json"
    )


FILE_NAME = determine_json_filename()


class ScreenSniper:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.root.withdraw()
        self.root.after(250, self.take_snapshot)

    def take_snapshot(self):
        self.snapshot = ImageGrab.grab()
        self.sniper_win = tk.Toplevel()
        self.sniper_win.attributes("-fullscreen", True, "-topmost", True)
        self.canvas = tk.Canvas(
            self.sniper_win,
            cursor="cross",
            highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.tk_snapshot = ImageTk.PhotoImage(self.snapshot)
        self.canvas.create_image(0, 0, image=self.tk_snapshot, anchor="nw")
        self.canvas.create_rectangle(
            0, 0, self.snapshot.width, self.snapshot.height,
            fill="black", stipple="gray25",
        )
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.start_x = self.start_y = None
        self.rect = None

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="red", width=2
        )

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        x1, y1, x2, y2 = (
            min(self.start_x, e.x), min(self.start_y, e.y),
            max(self.start_x, e.x), max(self.start_y, e.y),
        )
        self.sniper_win.destroy()
        self.root.deiconify()
        if (x2 - x1) > 5 and (y2 - y1) > 5:
            self.callback(self.snapshot.crop((x1, y1, x2, y2)))


class QuestionBankApp:

    def switch_grade(self, grade_key):
        self.current_grade = grade_key
        for key, btn in self.grade_btns.items():
            if key == grade_key:
                btn.config(bg="#e67e22", fg="white")
            else:
                btn.config(bg="#E0E0E0", fg="black")
        self.update_heading()

    def update_question_count(self):
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                try:
                    db_records = json.load(f)
                    if isinstance(db_records, list):
                        self.count_label.config(
                            text=f"Total Questions in DB: {
                                len(db_records)}")
                        return
                except json.JSONDecodeError:
                    pass
        self.count_label.config(text="Total Questions in DB: 0")

    def refresh_db_list(self, select_filename=None):
        current_dir = os.path.dirname(os.path.abspath(
            __file__)) if "__file__" in locals() else os.getcwd()
        json_files = glob.glob(os.path.join(current_dir, "*.json"))
        
        # Exclude specific configuration files from the question bank list
        excluded_files = {"model_config.json", "topics.json"}
        filenames = [
            os.path.basename(f) for f in json_files 
            if os.path.basename(f) not in excluded_files
        ]

        if not filenames:
            filenames = ["question_bank.json"]

        self.db_selector['values'] = filenames

        if select_filename in filenames:
            self.db_selector.set(select_filename)
        elif global_var := getattr(self, 'current_active_file', None):
            if global_var in filenames:
                self.db_selector.set(global_var)
        else:
            self.db_selector.set(filenames[0])

        self.handle_db_switch(None)

    def handle_db_switch(self, event):
        global FILE_NAME
        selected = self.db_selector.get()
        if selected:
            FILE_NAME = selected
            self.current_active_file = selected
            self.update_question_count()

    def create_new_database_file(self):
        new_name = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(
                os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd(),
            title="Create New Question Bank File",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if new_name:
            base_name = os.path.basename(new_name)
            if not os.path.exists(new_name):
                with open(new_name, "w", encoding="utf-8") as f:
                    json.dump([], f)
            self.refresh_db_list(select_filename=base_name)

    def __init__(self, root):
        self.root = root
        self.root.title("Unified Exam Question Bank Creator & OCR Parser")
        self.root.geometry("820x1000")
        self.root.minsize(780, 780)

        # Track active selections
        self.current_grade = "11"
        self.current_type = "mcq"
        self.current_subject = "m"
        self.current_year = "2026"
        self.current_exam_level = "e2"
        self.current_mcq_ans = "a"
        self.current_match_ans = 0

        self.last_focused_text_widget = None
        self.pending_image_object = None
        self.pending_explanation_image_object = None

        # --- CONTAINER SETUP ---
        self.main_container = tk.Frame(root)
        self.main_container.pack(fill="both", expand=True)

        self.bottom_fixed_bar = tk.Frame(
            root, bd=1, relief="groove", pady=12, bg="#F5F5F5"
        )
        self.bottom_fixed_bar.pack(fill="x", side="bottom")

        self.canvas = tk.Canvas(self.main_container, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(
            self.main_container, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        workspace = self.scrollable_frame

        # --- DYNAMIC DATABASE SELECTOR PANEL ---
        db_info_frame = tk.LabelFrame(
            workspace,
            text=" 📂 Target Database Manager ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=8
        )
        db_info_frame.pack(fill="x", padx=20, pady=5)

        self.db_selector = ttk.Combobox(
            db_info_frame, font=(
                "Arial", 10), state="readonly")
        self.db_selector.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.db_selector.bind("<<ComboboxSelected>>", self.handle_db_switch)

        refresh_btn = tk.Button(
            db_info_frame, text="🔄 Refresh", font=("Arial", 9),
            command=self.refresh_db_list, bg="#ECEFF1", bd=1, relief="groove"
        )
        refresh_btn.pack(side="left", padx=2)

        new_db_btn = tk.Button(
            db_info_frame, text="➕ New DB", font=("Arial", 9, "bold"),
            command=self.create_new_database_file, bg="#2196F3", fg="white", bd=1, relief="flat"
        )
        new_db_btn.pack(side="left", padx=2)

        self.count_label = tk.Label(
            db_info_frame, text="Total Questions: 0",
            font=("Arial", 10, "bold"), fg="#1565C0"
        )
        self.count_label.pack(side="right", padx=10)

        # PANEL 0: GRADE SELECTOR
        grade_frame = tk.LabelFrame(
            workspace,
            text=" 0. Select Grade Level ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        grade_frame.pack(fill="x", padx=20, pady=5)

        self.grade_btns = {}
        grades = [("11", "11"), ("8", "8")]
        for display_name, grade_key in grades:
            btn = tk.Button(
                grade_frame,
                text=display_name,
                font=("Arial", 10, "bold"),
                width=15,
                relief="flat",
                command=lambda g=grade_key: self.switch_grade(g),
                bg="#e67e22" if grade_key == "11" else "#E0E0E0",
                fg="white" if grade_key == "11" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.grade_btns[grade_key] = btn

        # PANEL 1: SUBJECT SELECTOR[cite: 11]
        sub_frame = tk.LabelFrame(
            workspace,
            text=" 1. Select Subject ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        sub_frame.pack(fill="x", padx=20, pady=5)

        self.sub_btns = {}
        subjects = [
            ("m", "m", "#E91E63"),
            ("b", "b", "#009688"),
            ("c", "c", "#FF5722"),
            ("x", "x", "#4CAF50"),
        ]

        for name, key, color in subjects:
            btn = tk.Button(
                sub_frame,
                text=name,
                font=("Arial", 10, "bold"),
                width=12,
                relief="flat",
                command=lambda k=key, c=color: self.switch_subject(k, c),
                bg=color if key == "m" else "#E0E0E0",
                fg="white" if key == "m" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.sub_btns[key] = btn

        # PANEL 2: QUESTION TYPE SELECTOR[cite: 11]
        type_frame = tk.LabelFrame(
            workspace,
            text=" 2. Question Type ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        type_frame.pack(fill="x", padx=20, pady=5)

        self.btn_mcq = tk.Button(
            type_frame,
            text="mcq",
            font=("Arial", 10, "bold"),
            width=12,
            command=lambda: self.switch_type("mcq"),
            bg="#2196F3",
            fg="white",
            relief="flat",
        )
        self.btn_mcq.pack(side="left", padx=10, pady=5)

        self.btn_matching = tk.Button(
            type_frame,
            text="matching",
            font=("Arial", 10, "bold"),
            width=12,
            command=lambda: self.switch_type("matching"),
            bg="#E0E0E0",
            fg="black",
            relief="flat",
        )
        self.btn_matching.pack(side="left", padx=10, pady=5)

        self.btn_integer = tk.Button(
            type_frame,
            text="integer",
            font=("Arial", 10, "bold"),
            width=12,
            command=lambda: self.switch_type("integer"),
            bg="#E0E0E0",
            fg="black",
            relief="flat",
        )
        self.btn_integer.pack(side="left", padx=10, pady=5)

        self.btn_subjective = tk.Button(
            type_frame,
            text="subjective",
            font=("Arial", 10, "bold"),
            width=12,
            command=lambda: self.switch_type("subjective"),
            bg="#E0E0E0",
            fg="black",
            relief="flat",
        )
        self.btn_subjective.pack(side="left", padx=10, pady=5)

        # PANEL 2b: YEAR SELECTOR TOOLBAR
        year_frame = tk.LabelFrame(
            workspace,
            text=" 2b. Select Question Year ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        year_frame.pack(fill="x", padx=20, pady=5)

        self.year_btns = {}
        years = ["2026", "2027"]
        for yr in years:
            btn = tk.Button(
                year_frame,
                text=yr,
                font=("Arial", 10, "bold"),
                width=8,
                relief="flat",
                command=lambda y=yr: self.switch_year(y),
                bg="#607D8B" if yr == "2026" else "#E0E0E0",
                fg="white" if yr == "2026" else "black",
            )
            btn.pack(side="left", padx=6, pady=5)
            self.year_btns[yr] = btn

        self.heading_label = tk.Label(
            workspace, text="m | mcq | 2026 (e2)", font=("Arial", 14, "bold"), fg="#2196F3"
        )
        self.heading_label.pack(pady=5)

        # PANEL 2c: EXAM LEVEL SELECTOR TOOLBAR
        level_frame = tk.LabelFrame(
            workspace,
            text=" 2c. Select Exam Level Tag ",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        level_frame.pack(fill="x", padx=20, pady=5)

        self.level_btns = {}
        # Combined levels
        levels = [("e1", "e1"), ("e2", "e2"), ("e3", "e3")]
        for display_name, lvl_key in levels:
            btn = tk.Button(
                level_frame,
                text=display_name,
                font=("Arial", 10, "bold"),
                width=15,
                relief="flat",
                command=lambda l=lvl_key: self.switch_exam_level(l),
                bg="#009688" if lvl_key == "e2" else "#E0E0E0",
                fg="white" if lvl_key == "e2" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.level_btns[lvl_key] = btn

        # PANEL 3: MATH SYMBOL TOOLBAR
        self.toolbar_frame = tk.LabelFrame(
            workspace,
            text=" Quick Symbols Toolbar (Click to insert) ",
            font=("Arial", 9, "bold"),
            fg="#333",
            padx=5,
            pady=5,
        )
        self.toolbar_frame.pack(fill="x", padx=20, pady=5)
        self.build_symbol_toolbar()

        # Global Question Text Area Layout with OCR Button
        tk.Label(workspace, text="Question Text:", font=("Arial", 10, "bold")).pack(
            anchor="w", padx=25, pady=2
        )
        q_layout_frame = tk.Frame(workspace)
        q_layout_frame.pack(fill="x", padx=25, pady=4)

        self.question_text = tk.Text(
            q_layout_frame,
            height=6,
            width=72,
            font=("Courier New", 10),
            bd=1,
            relief="solid",
            padx=8,
            pady=6,
        )
        self.question_text.pack(side="left", fill="both", expand=True)
        self.question_text.bind(
            "<FocusIn>", lambda e: self.set_last_focused(self.question_text)
        )

        q_ocr_btn = tk.Button(
            q_layout_frame,
            text="📷\nO\nC\nR",
            font=("Arial", 9, "bold"),
            bg="#FF9800",
            fg="white",
            bd=1,
            relief="groove",
            padx=5,
            command=lambda: self.trigger_targeted_snipe(self.question_text),
        )
        q_ocr_btn.pack(side="right", fill="y", padx=(5, 0))

        # PANEL 4: OPTIONAL QUESTION IMAGE PANEL
        img_layout_frame = tk.LabelFrame(
            workspace,
            text=" Optional Question Graphic Resource (Saved directly into same directory) ",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=5,
        )
        img_layout_frame.pack(fill="x", padx=20, pady=5)

        self.image_path_entry = tk.Entry(
            img_layout_frame, font=("Courier New", 10), bd=1, relief="solid", bg="#F5F5F5"
        )
        self.image_path_entry.insert(0, "[No Visual Graphic Snipped Yet]")
        self.image_path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        q_img_btn = tk.Button(
            img_layout_frame,
            text="✂️ Snipe Graphic Image",
            font=("Arial", 9, "bold"),
            bg="#009688",
            fg="white",
            bd=1,
            relief="groove",
            padx=10,
            command=self.trigger_image_capture,
        )
        q_img_btn.pack(side="right", padx=(5, 0))

        # Dynamic Layout Area Container
        self.dynamic_frame = tk.Frame(workspace)
        self.dynamic_frame.pack(fill="both", expand=True, pady=5)

        # 10-Line Explanation Discrete Entry Area Section[cite: 11]
        exp_header_frame = tk.Frame(workspace)
        exp_header_frame.pack(fill="x", padx=25, pady=(10, 2))

        tk.Label(
            exp_header_frame,
            text="Explanation / Solution (10 Individual Lines Area):",
            font=("Arial", 10, "bold"),
        ).pack(side="left")

        exp_plain_ocr_btn = tk.Button(
            exp_header_frame,
            text="📷 Snip Plain OCR to 10 Lines",
            font=("Arial", 8, "bold"),
            bg="#FF9800",
            fg="white",
            bd=1,
            relief="groove",
            padx=8,
            command=self.trigger_10_lines_ocr_snipe,
        )
        exp_plain_ocr_btn.pack(side="left", padx=12)

        self.explanation_lines = []
        exp_container = tk.Frame(workspace)
        exp_container.pack(fill="x", padx=25, pady=4)

        for i in range(10):
            frame_line = tk.Frame(exp_container)
            frame_line.pack(fill="x", pady=2)
            tk.Label(
                frame_line,
                text=f"Line {
                    i + 1}:",
                font=(
                    "Arial",
                    9),
                width=7,
                anchor="w").pack(
                side="left")

            entry = tk.Entry(
                frame_line,
                font=(
                    "Courier New",
                    10),
                bd=1,
                relief="solid")
            entry.pack(side="left", fill="x", expand=True, ipady=3)

            entry.bind(
                "<FocusIn>",
                lambda e,
                ent=entry: self.set_last_focused(ent))
            self.explanation_lines.append(entry)

            l_btn = tk.Button(
                frame_line, text="📷 OCR", font=("Arial", 8, "bold"),
                bg="#ECEFF1", fg="#37474F", bd=1, relief="groove",
                command=lambda ent=entry: self.trigger_targeted_snipe(ent),
            )
            l_btn.pack(side="right", padx=(5, 0))

        # --- STEP-BY-STEP SOLUTION BLOCK ---
        step_header_frame = tk.Frame(workspace)
        step_header_frame.pack(fill="x", padx=25, pady=(15, 2))

        tk.Label(
            step_header_frame,
            text="Comprehensive Unconstrained Step-by-Step Proof Box:",
            font=("Arial", 10, "bold"),
        ).pack(side="left")

        step_ocr_btn = tk.Button(
            step_header_frame,
            text="🪄 Snip & Auto-Step Solution",
            font=("Arial", 8, "bold"),
            bg="#9C27B0",
            fg="white",
            bd=1,
            relief="groove",
            padx=8,
            command=self.trigger_step_explanation_snipe,
        )
        step_ocr_btn.pack(side="left", padx=12)

        step_plain_ocr_btn = tk.Button(
            step_header_frame,
            text="📷 Snip Plain OCR Only",
            font=("Arial", 8, "bold"),
            bg="#FF9800",
            fg="white",
            bd=1,
            relief="groove",
            padx=8,
            command=self.trigger_step_ocr_snipe,
        )
        step_plain_ocr_btn.pack(side="left", padx=2)

        step_layout_frame = tk.Frame(workspace)
        step_layout_frame.pack(fill="x", padx=25, pady=4)

        self.step_explanation_text = tk.Text(
            step_layout_frame,
            height=10,
            width=72,
            font=("Courier New", 10),
            bd=1,
            relief="solid",
            padx=8,
            pady=6,
        )
        self.step_explanation_text.pack(side="left", fill="both", expand=True)
        self.step_explanation_text.bind(
            "<FocusIn>", lambda e: self.set_last_focused(
                self.step_explanation_text)
        )

        step_ocr_btn_standard = tk.Button(
            step_layout_frame,
            text="📷\nO\nC\nR",
            font=("Arial", 9, "bold"),
            bg="#FF9800",
            fg="white",
            bd=1,
            relief="groove",
            padx=5,
            command=lambda: self.trigger_targeted_snipe(
                self.step_explanation_text),
        )
        step_ocr_btn_standard.pack(side="right", fill="y", padx=(5, 0))

        # --- EXPLANATION IMAGE PANEL[cite: 10] ---
        expl_img_layout_frame = tk.LabelFrame(
            workspace,
            text=" Optional Explanation Graphic Resource ",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=5,
        )
        expl_img_layout_frame.pack(fill="x", padx=20, pady=15)

        self.expl_image_path_entry = tk.Entry(
            expl_img_layout_frame, font=("Courier New", 10), bd=1, relief="solid", bg="#F5F5F5"
        )
        self.expl_image_path_entry.insert(0, "[No Visual Graphic Snipped Yet]")
        self.expl_image_path_entry.pack(
            side="left", fill="x", expand=True, ipady=4)

        expl_img_btn = tk.Button(
            expl_img_layout_frame,
            text="✂️ Snipe Explanation Graphic",
            font=("Arial", 9, "bold"),
            bg="#009688",
            fg="white",
            bd=1,
            relief="groove",
            padx=10,
            command=self.trigger_explanation_image_capture,
        )
        expl_img_btn.pack(side="right", padx=(5, 0))

        # --- PINNED HARD TO BOTTOM DISPLAY CONTROL ---
        self.save_btn = tk.Button(
            self.bottom_fixed_bar,
            text="Save Question to JSON",
            bg="#4CAF50",
            fg="white",
            command=self.save_question_data,
            font=("Arial", 12, "bold"),
            padx=50,
            pady=8,
        )
        self.save_btn.pack()

        self.mcq_entries = {}
        self.match_left_entries = []
        self.match_right_entries = []
        self.integer_entry = None

        self.setup_mcq_fields()
        self.set_last_focused(self.question_text)
        self.refresh_db_list()
        self.update_question_count()

        # Async load the model engine structure safely
        threading.Thread(target=QWEN_ENGINE.load_model, daemon=True).start()

    def set_last_focused(self, widget):
        self.last_focused_text_widget = widget

    def trigger_batch_options_snipe(self):
        """e3 option extraction from Source 10[cite: 10]"""
        def processing_handler(cropped_image):
            def run_in_thread():
                result = QWEN_ENGINE.analyze_4_options_and_answer(
                    cropped_image)
                if result and "options" in result and "answer" in result:
                    def update_ui():
                        opts_list = result["options"]
                        keys = ["a", "b", "c", "d"]
                        for i, key in enumerate(keys):
                            if i < len(opts_list) and key in self.mcq_entries:
                                self.mcq_entries[key].delete(0, tk.END)
                                self.mcq_entries[key].insert(
                                    0, opts_list[i].strip())

                        ans = result["answer"].lower().strip()
                        if ans in keys:
                            self.mcq_ans_var.set(ans)
                            self.current_mcq_ans = ans
                    self.root.after(0, update_ui)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "OCR JSON Structure Error",
                        "Failed to map structured components. Visual logs generated inside console terminal window."
                    ))

            threading.Thread(target=run_in_thread, daemon=True).start()

        ScreenSniper(self.root, processing_handler)

    def trigger_targeted_snipe(self, target_widget):
        def processing_handler(cropped_image):
            def run_in_thread():
                text = QWEN_ENGINE.run_ocr(cropped_image)
                self.root.after(
                    0, lambda: self.update_widget(
                        target_widget, text))

            threading.Thread(target=run_in_thread, daemon=True).start()

        ScreenSniper(self.root, processing_handler)

    def trigger_10_lines_ocr_snipe(self):
        def processing_handler(cropped_image):
            def run_in_thread():
                raw_text = QWEN_ENGINE.run_ocr(cropped_image)
                extracted_lines = [
                    line.strip() for line in raw_text.split('\n') if line.strip()]

                def update_discrete_fields():
                    for entry in self.explanation_lines:
                        entry.delete(0, tk.END)
                    for i, line_content in enumerate(extracted_lines[:10]):
                        self.explanation_lines[i].insert(0, line_content)

                self.root.after(0, update_discrete_fields)

            threading.Thread(target=run_in_thread, daemon=True).start()

        ScreenSniper(self.root, processing_handler)

    def trigger_step_explanation_snipe(self):
        def processing_handler(cropped_image):
            def run_in_thread():
                text = QWEN_ENGINE.run_step_by_step_explanation(cropped_image)
                self.root.after(
                    0, lambda: self.update_widget(
                        self.step_explanation_text, text))

            threading.Thread(target=run_in_thread, daemon=True).start()

        ScreenSniper(self.root, processing_handler)

    def trigger_step_ocr_snipe(self):
        def processing_handler(cropped_image):
            def run_in_thread():
                raw_text = QWEN_ENGINE.run_ocr(cropped_image)
                modified_text = f"{raw_text}\n\n[Rewritten Extra Word/Context Note]"
                self.root.after(
                    0, lambda: self.update_widget(
                        self.step_explanation_text, modified_text))

            threading.Thread(target=run_in_thread, daemon=True).start()

        ScreenSniper(self.root, processing_handler)

    def trigger_image_capture(self):
        def processing_handler(cropped_image):
            self.pending_image_object = cropped_image
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(
                0, "📸 Graphic Captured! [Unique filename will be generated on save]")

        ScreenSniper(self.root, processing_handler)

    def trigger_explanation_image_capture(self):
        def processing_handler(cropped_image):
            self.pending_explanation_image_object = cropped_image
            self.expl_image_path_entry.delete(0, tk.END)
            self.expl_image_path_entry.insert(
                0, "📸 Explanation Graphic Captured! [Unique filename will be generated on save]")

        ScreenSniper(self.root, processing_handler)

    def update_widget(self, widget, text):
        if isinstance(widget, tk.Text):
            widget.insert(tk.END, text)
        elif isinstance(widget, tk.Entry):
            widget.insert(0, text)

    def switch_subject(self, subject_key, color):
        self.current_subject = subject_key
        for key, btn in self.sub_btns.items():
            if key == subject_key:
                btn.config(bg=color, fg="white")
            else:
                btn.config(bg="#E0E0E0", fg="black")
        self.update_heading()

    def switch_type(self, type_key):
        self.current_type = type_key

        # Loop through all 4 type buttons to update active/inactive highlights
        # safely
        for btn, key in [(self.btn_mcq, "mcq"), (self.btn_matching, "matching"),
                         (self.btn_integer, "integer"), (self.btn_subjective, "subjective")]:
            btn.config(
                bg="#2196F3" if type_key == key else "#E0E0E0",
                fg="white" if type_key == key else "black",
            )

        for child in self.dynamic_frame.winfo_children():
            child.destroy()

        if type_key == "mcq":
            self.setup_mcq_fields()
        elif type_key == "matching":
            self.setup_matching_fields()
        elif type_key == "integer":
            self.setup_integer_fields()
        elif type_key == "subjective":
            lbl = tk.Label(
                self.dynamic_frame,
                text="📝 Subjective Mode Active: Use Question Text and Step-by-Step Proof Box.",
                font=(
                    "Arial",
                    9,
                    "italic"),
                fg="#666")
            lbl.pack(padx=20, pady=10)

        self.update_heading()

    def switch_year(self, year_key):
        self.current_year = year_key
        for yr, btn in self.year_btns.items():
            if yr == year_key:
                btn.config(bg="#607D8B", fg="white")
            else:
                btn.config(bg="#E0E0E0", fg="black")
        self.update_heading()

    def switch_exam_level(self, level_key):
        self.current_exam_level = level_key
        for key, btn in self.level_btns.items():
            if key == level_key:
                btn.config(bg="#009688", fg="white")
            else:
                btn.config(bg="#E0E0E0", fg="black")
        self.update_heading()

    def update_heading(self):
        current_color = self.sub_btns[self.current_subject].cget("bg")
        self.heading_label.config(
            text=f"{
                self.current_subject.upper()} | {
                self.current_type.upper()} | {
                self.current_year} ({
                self.current_exam_level.upper()})",
            fg=current_color
        )

    def build_symbol_toolbar(self):
        symbols = [
            "√", "π", "α", "β", "γ", "θ", "λ", "Δ", "μ", "Σ",
            "∫", "±", "≠", "≤", "≥", "∞", "→", "²", "³", "ⁿ",
        ]
        for sym in symbols:
            btn = tk.Button(
                self.toolbar_frame,
                text=sym,
                font=("Courier New", 10, "bold"),
                width=3,
                bg="#FFFFFF",
                relief="groove",
                command=lambda s=sym: self.insert_symbol(s),
            )
            btn.pack(side="left", padx=2, pady=2)

    def insert_symbol(self, symbol):
        if self.last_focused_text_widget:
            if isinstance(self.last_focused_text_widget, tk.Text):
                self.last_focused_text_widget.insert(tk.INSERT, symbol)
            elif isinstance(self.last_focused_text_widget, tk.Entry):
                self.last_focused_text_widget.insert(tk.INSERT, symbol)

    def setup_mcq_fields(self):
        self.mcq_entries = {}
        options_frame = tk.LabelFrame(
            self.dynamic_frame,
            text=" MCQ Options Data (4 Choice Rows) ",
            padx=10,
            pady=10,
        )
        options_frame.pack(fill="x", padx=20, pady=5)

        # Batch fill options button[cite: 10]
        batch_frame = tk.Frame(options_frame, pady=3)
        batch_frame.pack(fill="x")
        auto_fill_btn = tk.Button(
            batch_frame,
            text="🪄 Snip & Auto-Fill All 4 Options + Answer Key",
            font=("Arial", 9, "bold"),
            bg="#00796B",
            fg="white",
            bd=1,
            relief="groove",
            command=self.trigger_batch_options_snipe
        )
        auto_fill_btn.pack(side="left", pady=2)

        for opt in ["a", "b", "c", "d"]:
            line = tk.Frame(options_frame)
            line.pack(fill="x", pady=3)
            tk.Label(
                line,
                text=f"Option ({opt.upper()}):",
                font=("Arial", 9, "bold"),
                width=12,
                anchor="w",
            ).pack(side="left")

            ent = tk.Entry(
                line,
                font=(
                    "Courier New",
                    10),
                bd=1,
                relief="solid")
            ent.pack(side="left", fill="x", expand=True, ipady=3)
            ent.bind("<FocusIn>", lambda e, w=ent: self.set_last_focused(w))
            self.mcq_entries[opt] = ent

            l_btn = tk.Button(
                line,
                text="📷 OCR",
                font=("Arial", 8, "bold"),
                bg="#ECEFF1",
                fg="#37474F",
                bd=1,
                relief="groove",
                command=lambda w=ent: self.trigger_targeted_snipe(w),
            )
            l_btn.pack(side="right", padx=(5, 0))

        ans_frame = tk.Frame(self.dynamic_frame, pady=5)
        ans_frame.pack(fill="x", padx=25)
        tk.Label(
            ans_frame, text="Correct Option Selection Tag:", font=("Arial", 10, "bold")
        ).pack(side="left", padx=(0, 10))

        self.mcq_ans_var = tk.StringVar(value="a")
        for opt in ["a", "b", "c", "d"]:
            rbtn = tk.Radiobutton(
                ans_frame,
                text=opt.upper(),
                variable=self.mcq_ans_var,
                value=opt,
                font=("Arial", 10, "bold"),
                command=lambda: setattr(
                    self, "current_mcq_ans", self.mcq_ans_var.get()
                ),
            )
            rbtn.pack(side="left", padx=15)

    def setup_matching_fields(self):
        self.match_left_entries = []
        self.match_right_entries = []

        grid_frame = tk.LabelFrame(
            self.dynamic_frame,
            text=" Matrix Match Layout Fields (4x4 Parallel Strings) ",
            padx=10,
            pady=10,
        )
        grid_frame.pack(fill="x", padx=20, pady=5)

        left_col = tk.Frame(grid_frame)
        left_col.pack(side="left", fill="x", expand=True, padx=5)
        tk.Label(
            left_col,
            text="List I (A-D Questions)",
            font=("Arial", 9, "bold"),
            fg="#1565C0",
        ).pack(anchor="w", pady=2)
        for i, label in enumerate(["A", "B", "C", "D"]):
            row = tk.Frame(left_col)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", width=3).pack(side="left")
            ent = tk.Entry(row, font=("Courier New", 10), bd=1, relief="solid")
            ent.pack(side="left", fill="x", expand=True, ipady=2)
            ent.bind("<FocusIn>", lambda e, w=ent: self.set_last_focused(w))
            self.match_left_entries.append(ent)
            l_btn = tk.Button(
                row,
                text="📷",
                font=("Arial", 7),
                command=lambda w=ent: self.trigger_targeted_snipe(w),
            )
            l_btn.pack(side="right", padx=1)

        right_col = tk.Frame(grid_frame)
        right_col.pack(side="right", fill="x", expand=True, padx=5)
        tk.Label(
            right_col,
            text="List II (1-4 Maps)",
            font=("Arial", 9, "bold"),
            fg="#2E7D32",
        ).pack(anchor="w", pady=2)
        for i, label in enumerate(["1", "2", "3", "4"]):
            row = tk.Frame(right_col)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", width=3).pack(side="left")
            ent = tk.Entry(row, font=("Courier New", 10), bd=1, relief="solid")
            ent.pack(side="left", fill="x", expand=True, ipady=2)
            ent.bind("<FocusIn>", lambda e, w=ent: self.set_last_focused(w))
            self.match_right_entries.append(ent)
            l_btn = tk.Button(
                row,
                text="📷",
                font=("Arial", 7),
                command=lambda w=ent: self.trigger_targeted_snipe(w),
            )
            l_btn.pack(side="right", padx=1)

        ans_frame = tk.LabelFrame(
            self.dynamic_frame,
            text=" Dynamic Option Map Key Solution Builder (Matrix Mapping Row) ",
            padx=10,
            pady=5,
        )
        ans_frame.pack(fill="x", padx=20, pady=5)

        self.match_ans_entries = []
        labels = ["A →", "B →", "C →", "D →"]
        for i in range(4):
            lbl_f = tk.Frame(ans_frame)
            lbl_f.pack(side="left", padx=10, pady=5)
            tk.Label(
                lbl_f,
                text=labels[i],
                font=(
                    "Arial",
                    9,
                    "bold")).pack(
                side="left")
            spin = tk.Spinbox(
                lbl_f,
                from_=1,
                to=4,
                width=4,
                font=("Arial", 10, "bold"),
                justify="center",
            )
            spin.pack(side="left", padx=2)
            self.match_ans_entries.append(spin)

    def setup_integer_fields(self):
        int_frame = tk.LabelFrame(
            self.dynamic_frame,
            text=" Numerical/Integer Evaluation Data Answer Value ",
            padx=15,
            pady=15,
        )
        int_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            int_frame, text="Target Integer Output Value:", font=("Arial", 10, "bold")
        ).pack(side="left", padx=(0, 15))
        self.integer_entry = tk.Entry(
            int_frame,
            font=("Arial", 12, "bold"),
            width=15,
            justify="center",
            bd=2,
            relief="groove",
        )
        self.integer_entry.pack(side="left", ipady=4)
        self.integer_entry.bind(
            "<FocusIn>", lambda e: self.set_last_focused(self.integer_entry)
        )

        l_btn = tk.Button(
            int_frame,
            text="📷 OCR Value Extract",
            font=("Arial", 9, "bold"),
            bg="#ECEFF1",
            fg="#37474F",
            bd=1,
            relief="groove",
            command=lambda: self.trigger_targeted_snipe(self.integer_entry),
        )
        l_btn.pack(side="left", padx=15)

    def save_question_data(self):
        q_text = self.question_text.get("1.0", tk.END).strip()
        if not q_text:
            messagebox.showerror(
                "Validation Error", "Question block content structure empty."
            )
            return

        expl_arr = [
            line.get().strip() for line in self.explanation_lines if line.get().strip()
        ]

        step_expl_text = self.step_explanation_text.get("1.0", tk.END).strip()

        current_dir = os.path.dirname(os.path.abspath(
            __file__)) if "__file__" in locals() else os.getcwd()
        images_dir = os.path.join(current_dir, "images")

        relative_image_path = ""
        if self.pending_image_object is not None:
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)

            random_token = uuid.uuid4().hex[:10]
            image_filename = f"img_{random_token}.jpg"
            absolute_image_path = os.path.join(images_dir, image_filename)

            try:
                self.pending_image_object.convert("RGB").save(
                    absolute_image_path, "JPEG", quality=95)
                relative_image_path = f"images/{image_filename}"
            except Exception as img_err:
                messagebox.showerror(
                    "Image Save Error",
                    f"Failed saving image file structure:\n{img_err}")
                return

        relative_expl_image_path = ""
        if getattr(self, "pending_explanation_image_object", None) is not None:
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)

            random_token_expl = uuid.uuid4().hex[:10]
            expl_image_filename = f"expl_img_{random_token_expl}.jpg"
            absolute_expl_image_path = os.path.join(
                images_dir, expl_image_filename)

            try:
                self.pending_explanation_image_object.convert("RGB").save(
                    absolute_expl_image_path, "JPEG", quality=95)
                relative_expl_image_path = f"images/{expl_image_filename}"
            except Exception as img_err:
                messagebox.showerror(
                    "Image Save Error",
                    f"Failed saving explanation image file structure:\n{img_err}")
                return

        db_records = []
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                try:
                    db_records = json.load(f)
                    if not isinstance(db_records, list):
                        db_records = []
                except json.JSONDecodeError:
                    db_records = []

        next_id = len(db_records) + 1

        # Your exact custom schema structure
        parsed_structure = {
            "id": next_id,
            "grade": self.current_grade,            # e.g.,  "11","8"
            "subject": self.current_subject,         # e.g., "m", "clogy", "b", "c","custom"
            # e.g., "mcq", "matching", "integer","subjective"
            "type": self.current_type,
            "year": self.current_year,               # e.g., "2026", "2025", "custom year"
            "exam_level": self.current_exam_level,   # e.g., "e1", "e2", "e3",
            "image": relative_image_path,
            "explanation_image": relative_expl_image_path,
            "question": q_text,
            "explanation": expl_arr,
            "step_by_step_explanation": step_expl_text,
        }

        if self.current_type == "mcq":
            opts = {k: v.get().strip() for k, v in self.mcq_entries.items()}
            if not all(opts.values()):
                messagebox.showerror(
                    "Validation Error",
                    "Please fill all 4 choice parameter arrays before export.",
                )
                return
            parsed_structure.update(
                {"options": opts, "answer": self.mcq_ans_var.get()})
        elif self.current_type == "matching":
            l_list = [e.get().strip() for e in self.match_left_entries]
            r_list = [e.get().strip() for e in self.match_right_entries]
            if not (all(l_list) and all(r_list)):
                messagebox.showerror(
                    "Validation Error",
                    "All Left and Right matrix elements must hold text.",
                )
                return
            ans_map = {
                "a": int(self.match_ans_entries[0].get()),
                "b": int(self.match_ans_entries[1].get()),
                "c": int(self.match_ans_entries[2].get()),
                "d": int(self.match_ans_entries[3].get()),
            }
            parsed_structure.update(
                {"list_1": l_list, "list_2": r_list, "answer": ans_map}
            )
        elif self.current_type == "integer":
            val = self.integer_entry.get().strip()
            if not val:
                messagebox.showerror(
                    "Validation Error",
                    "Integer answer field empty.")
                return
            parsed_structure.update({"answer": val})
        elif self.current_type == "subjective":
            parsed_structure.update(
                {"answer": "Subjective Proof / Derivation"})

        # --- RESTORED FILE WRITING LOGIC ---
        try:
            db_records.append(parsed_structure)
            with open(FILE_NAME, "w", encoding="utf-8") as f:
                json.dump(db_records, f, indent=4, ensure_ascii=False)

            messagebox.showinfo(
                "Success",
                f"Question successfully written to standard store database:\n{FILE_NAME}",
            )
            self.clear_fields_for_next_entry()
        except Exception as ex:
            messagebox.showerror(
                "File I/O Error Failure",
                f"Failed compilation runtime tracking variables:\n{ex}",
            )

    def clear_fields_for_next_entry(self):
        self.question_text.delete("1.0", tk.END)
        self.step_explanation_text.delete("1.0", tk.END)

        for entry in self.explanation_lines:
            if entry.winfo_exists():
                entry.delete(0, tk.END)

        if self.current_type == "mcq":
            for k, v in self.mcq_entries.items():
                if v.winfo_exists():
                    v.delete(0, tk.END)
        elif self.current_type == "matching":
            for e in self.match_left_entries:
                if e.winfo_exists():
                    e.delete(0, tk.END)
            for e in self.match_right_entries:
                if e.winfo_exists():
                    e.delete(0, tk.END)
        elif self.current_type == "integer":
            if self.integer_entry and self.integer_entry.winfo_exists():
                self.integer_entry.delete(0, tk.END)

        self.image_path_entry.delete(0, tk.END)
        self.image_path_entry.insert(0, "[No Visual Graphic Snipped Yet]")
        self.pending_image_object = None

        if hasattr(self, "expl_image_path_entry"):
            self.expl_image_path_entry.delete(0, tk.END)
            self.expl_image_path_entry.insert(
                0, "[No Visual Graphic Snipped Yet]")
        self.pending_explanation_image_object = None

        self.update_question_count()


if __name__ == "__main__":
    try:
        app_root = tk.Tk()
        app_engine = QuestionBankApp(app_root)
        app_root.mainloop()
    except Exception as e:
        import traceback
        print("\n================ DETECTED STARTUP CRASH ================")
        traceback.print_exc()
        print("========================================================\n")
        input("Press Enter to close...")
