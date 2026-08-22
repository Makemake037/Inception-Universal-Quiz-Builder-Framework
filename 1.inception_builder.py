import os
import re
import shutil
import json

def create_universal_framework():
    print("="*65)
    print(" 🌌 INCEPTION QUIZ BUILDER - UNIVERSAL FRAMEWORK GENERATOR 🌌")
    print("="*65)
    print("Tip: Leave any input blank and press Enter to use default values.\n")
    
    # 1. Gather dynamic user parameters (Neutralized Defaults)
    grades_in = input("1. Enter Grades/Classes (comma-separated, e.g., Grade 8, Grade 9):\n> ")
    grades_list = [g.strip() for g in grades_in.split(',')] if grades_in.strip() else ["Grade 11", "Grade 12"]
    grades_tuples = [(g, g.lower().replace(" ", "_")) for g in grades_list]

    subjects_in = input("\n2. Enter Subjects (comma-separated, e.g., History, Geography):\n> ")
    subjects_list = [s.strip() for s in subjects_in.split(',')] if subjects_in.strip() else ["Subject A", "Subject B"]
    colors = ["#E91E63", "#009688", "#FF5722", "#4CAF50", "#9C27B0", "#3F51B5", "#FF9800", "#795548", "#607D8B"]
    subjects_tuples = [(s, s.lower().replace(" ", "_"), colors[i % len(colors)]) for i, s in enumerate(subjects_list)]

    years_in = input("\n3. Enter Years (comma-separated, e.g., 2023, 2024):\n> ")
    years_list = [y.strip() for y in years_in.split(',')] if years_in.strip() else ["2024", "2025", "2026"]
    if years_in.strip().lower() == "none": years_list = ["Any"]

    exams_in = input("\n4. Enter Exam Types / Tags (comma-separated, e.g., Midterm, Final):\n> ")
    levels_list = [l.strip() for l in exams_in.split(',')] if exams_in.strip() else ["Standard Exam", "Advanced Exam"]
    levels_tuples = [(l, l.lower().replace(" ", "_")) for l in levels_list]

    print("\n⚙️  Generating custom framework...")
    
    # 2. Setup the isolated output directory
    out_dir = "inceptionquiz"
    os.makedirs(out_dir, exist_ok=True)
    
    # 3. Generate 4.ocr-AIO.py from ocr-AIO.py
    source_py = "ocr-AIO.py"
    if not os.path.exists(source_py):
        print(f"  [X] ERROR: Could not find '{source_py}'. Make sure it is in this directory.")
        return

    try:
        with open(source_py, "r", encoding="utf-8") as f:
            py_data = f.read()

        # Build dynamic Python strings for the UI builders
        grades_code = "grades = [\n" + ''.join([f'            ("{display}", "{val}"),\n' for display, val in grades_tuples]) + "        ]"
        subjects_code = "subjects = [\n" + ''.join([f'            ("{display}", "{val}", "{col}"),\n' for display, val, col in subjects_tuples]) + "        ]"
        years_code = f"years = {repr(years_list)}"
        levels_code = "levels = [\n" + ''.join([f'            ("{display}", "{val}"),\n' for display, val in levels_tuples]) + "        ]"

        # Replace hardcoded blocks in Python code
        py_data = re.sub(r'grades\s*=\s*\[.*?\]', grades_code, py_data, flags=re.DOTALL)
        py_data = re.sub(r'subjects\s*=\s*\[.*?\]', subjects_code, py_data, flags=re.DOTALL)
        py_data = re.sub(r'years\s*=\s*\[.*?\]', years_code, py_data, flags=re.DOTALL)
        py_data = re.sub(r'levels\s*=\s*\[.*?\]', levels_code, py_data, flags=re.DOTALL)

        # Set boot variables
        py_data = re.sub(r'self\.current_grade\s*=\s*".*?"', f'self.current_grade = "{grades_tuples[0][1]}"', py_data)
        py_data = re.sub(r'self\.current_subject\s*=\s*".*?"', f'self.current_subject = "{subjects_tuples[0][1]}"', py_data)
        py_data = re.sub(r'self\.current_year\s*=\s*".*?"', f'self.current_year = "{years_list[0]}"', py_data)
        py_data = re.sub(r'self\.current_exam_level\s*=\s*".*?"', f'self.current_exam_level = "{levels_tuples[0][1]}"', py_data)

        # Rewrite GUI layout loops dynamically inside Python string
        grade_ui_code = f"""        grades = {repr(grades_tuples)}
        for display_name, grade_key in grades:
            btn = tk.Button(
                grade_frame,
                text=display_name,
                font=("Arial", 10, "bold"),
                width=15,
                relief="flat",
                command=lambda g=grade_key: self.switch_grade(g),
                bg="#e67e22" if grade_key == "{grades_tuples[0][1]}" else "#E0E0E0",
                fg="white" if grade_key == "{grades_tuples[0][1]}" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.grade_btns[grade_key] = btn"""
        
        py_data = re.sub(r'grades\s*=\s*\[\("Class 11".*?self\.grade_btns\[grade_key\]\s*=\s*btn', grade_ui_code, py_data, flags=re.DOTALL)

        subject_ui_code = f"""        subjects = {repr(subjects_tuples)}
        for name, key, color in subjects:
            btn = tk.Button(
                sub_frame,
                text=name,
                font=("Arial", 10, "bold"),
                width=12,
                relief="flat",
                command=lambda k=key, c=color: self.switch_subject(k, c),
                bg=color if key == "{subjects_tuples[0][1]}" else "#E0E0E0",
                fg="white" if key == "{subjects_tuples[0][1]}" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.sub_btns[key] = btn"""
            
        py_data = re.sub(r'subjects\s*=\s*\[\("Maths".*?self\.sub_btns\[key\]\s*=\s*btn', subject_ui_code, py_data, flags=re.DOTALL)

        year_ui_code = f"""        years = {repr(years_list)}
        for yr in years:
            btn = tk.Button(
                year_frame,
                text=yr,
                font=("Arial", 10, "bold"),
                width=8,
                relief="flat",
                command=lambda y=yr: self.switch_year(y),
                bg="#607D8B" if yr == "{years_list[0]}" else "#E0E0E0",
                fg="white" if yr == "{years_list[0]}" else "black",
            )
            btn.pack(side="left", padx=6, pady=5)
            self.year_btns[yr] = btn"""
            
        py_data = re.sub(r'years\s*=\s*\["2020".*?self\.year_btns\[yr\]\s*=\s*btn', year_ui_code, py_data, flags=re.DOTALL)

        level_ui_code = f"""        levels = {repr(levels_tuples)}
        for display_name, lvl_key in levels:
            btn = tk.Button(
                level_frame,
                text=display_name,
                font=("Arial", 10, "bold"),
                width=15,
                relief="flat",
                command=lambda l=lvl_key: self.switch_exam_level(l),
                bg="#009688" if lvl_key == "{levels_tuples[0][1]}" else "#E0E0E0",
                fg="white" if lvl_key == "{levels_tuples[0][1]}" else "black",
            )
            btn.pack(side="left", padx=10, pady=5)
            self.level_btns[lvl_key] = btn"""
            
        py_data = re.sub(r'levels\s*=\s*\[\("NEET UG".*?self\.level_btns\[lvl_key\]\s*=\s*btn', level_ui_code, py_data, flags=re.DOTALL)

        with open(os.path.join(out_dir, "4.ocr-AIO.py"), "w", encoding="utf-8") as f:
            f.write(py_data)
        print("  [✓] 4.ocr-AIO.py generated successfully inside /inceptionquiz!")
    except Exception as e:
        print(f"  [X] ERROR building Python creator script: {e}")

    # 4. Modify spawn.html (Inject Grade & Exam Filters)
    try:
        with open("spawn.html", "r", encoding="utf-8") as f:
            html_data = f.read()

        grade_options = '<option value="all">All Grades</option>\n'
        for display, val in grades_tuples:
            grade_options += f'                <option value="{val}">{display}</option>\n'
        
        grade_html = f'''<!-- Custom Grade Filter -->
        <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-weight: bold; padding: 0; margin: 0; cursor: default;">Select Grade:</label>
            <select id="gradeFilterSelect" class="time-select" onchange="processQuestionsDataset()">
{grade_options}            </select>
        </div>'''

        level_options = '<option value="all">All Exam Levels</option>\n'
        for display, val in levels_tuples:
            level_options += f'                <option value="{val}">{display}</option>\n'

        html_data = re.sub(
            r'<!-- Exam Level Filter.*?<select id="levelFilterSelect".*?>.*?</select>',
            f'{grade_html}\n\n        <!-- Custom Exam Level Filter -->\n        <div style="display: flex; flex-direction: column; gap: 4px;">\n            <label style="font-weight: bold; padding: 0; margin: 0; cursor: default;">Exam Level:</label>\n            <select id="levelFilterSelect" class="time-select" onchange="processQuestionsDataset()">\n{level_options}            </select>',
            html_data,
            flags=re.DOTALL
        )
        
        with open(os.path.join(out_dir, "spawn.html"), "w", encoding="utf-8") as f:
            f.write(html_data)
        print("  [✓] spawn.html interface re-wired successfully!")
    except Exception as e:
        print(f"  [X] ERROR building HTML: {e}")

    # 5. Modify quizlogic.js (Inject Grade Filter logic)
    try:
        with open("quizlogic.js", "r", encoding="utf-8") as f:
            js_data = f.read()
        
        grade_filter_logic = """
        // D. Dynamic Grade Filter Block (Injected by Builder)
        const selectedGrade = document.getElementById('gradeFilterSelect')?.value;
        if (selectedGrade && selectedGrade !== 'all' && q.grade !== selectedGrade) {
            return false;
        }
        """
        
        js_data = re.sub(
            r'(const selectedFormat = .*?;.*?if \(selectedFormat !== \'all\' && q\.type !== selectedFormat\) \{.*?return false;\n\s*\})',
            r'\1\n' + grade_filter_logic,
            js_data,
            flags=re.DOTALL
        )
        
        with open(os.path.join(out_dir, "quizlogic.js"), "w", encoding="utf-8") as f:
            f.write(js_data)
        print("  [✓] quizlogic.js data routing patched successfully!")
    except Exception as e:
        print(f"  [X] ERROR building JavaScript: {e}")

    # 6. Generate topics.json and port remaining web assets
    topics_blueprint = [
        {"file": "question_bank.json", "name": "Default Universal Question Bank"}
    ]
    with open(os.path.join(out_dir, "topics.json"), "w", encoding="utf-8") as f:
        json.dump(topics_blueprint, f, indent=4)

    for asset in ["canvas.js", "timer.js", "6.RefreshYourTopicsJSON.py", "5.Setup-multiple-JSON.PY", "3.model_manager.py", "7a.localserver.py", "7b.localserver.bat", "4.ocr-AIO.bat"]:
        if os.path.exists(asset):
            shutil.copy(asset, os.path.join(out_dir, asset))

    print(f"\n✅ SYSTEM OVERHAUL COMPLETE! Navigate to the '{out_dir}' folder to run your tailored framework.")

if __name__ == "__main__":
    create_universal_framework()