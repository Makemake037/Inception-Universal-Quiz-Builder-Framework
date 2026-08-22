import os
import json
import re

def slugify_chapter_name(name):
    """Converts a full chapter title into a clean, safe filename."""
    clean = name.lower()
    clean = re.sub(r'[–—\-\(\)]', '', clean)  # Remove dashes and parentheses
    clean = re.sub(r'\s+', '_', clean.strip())  # Replace spaces with underscores
    clean = re.sub(r'[^a-z0-9_]', '', clean)    # Remove any remaining punctuation
    return clean

def generate_batch_json_files():
    print("="*65)
    print(" 📦 NUMBERED CHAPTER JSON BANK GENERATOR 📦")
    print("="*65)
    print('Paste your chapter names below (e.g., "one", "two", ...).')
    print("Press Enter on an empty line when finished:\n")
    
    # 1. Multi-line input collection (terminates on empty line)
    lines = []
    while True:
        try:
            line = input()
            if line == "":  # Empty line signals completion
                break
            if line.strip():
                lines.append(line)
        except EOFError:
            break

    if not lines:
        print("  [X] Error: No chapters provided. Aborted.")
        return

    # Parse names (handles comma-separated and newline-separated lists)
    raw_chapters = []
    for line in lines:
        parts = [p.strip().strip('"\'') for p in line.split(',')]
        for part in parts:
            if part:
                raw_chapters.append(part)

    # 2. Target directory check (saves inside /inceptionquiz if it exists)
    target_dir = "inceptionquiz" if os.path.exists("inceptionquiz") else "."
    
    print(f"\n⚙️  Processing {len(raw_chapters)} chapters with serial numbers into '{target_dir}'...")
    
    created_count = 0
    for index, title in enumerate(raw_chapters, start=1):
        # Format with a two-digit serial prefix (e.g., 01_, 02_, ..., 25_)
        serial_prefix = f"{index:02d}"
        slug = slugify_chapter_name(title)
        filename = f"{serial_prefix}_{slug}.json"
        filepath = os.path.join(target_dir, filename)
        
        # Write empty array structure if it doesn't already exist
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)
            print(f"  [✓] Created: {filename}  -->  ('{title}')")
            created_count += 1
        else:
            print(f"  [-] Skipped (Exists): {filename}")
            
    print(f"\n✅ Successfully generated {created_count} numbered chapter JSON files!")

if __name__ == "__main__":
    generate_batch_json_files()