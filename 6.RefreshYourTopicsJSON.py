import os
import json

def generate_topics_json():
    output_filename = 'topics.json'
    topics = []

    # Scan the current directory[cite: 15]
    for filename in os.listdir('.'):
        # Look for JSON files, but skip the output file if it already exists[cite: 15]
        if filename.endswith('.json') and filename != output_filename:
            
            # Remove the '.json' extension[cite: 15]
            name_without_ext = os.path.splitext(filename)[0]
            
            # Convert snake_case or kebab-case to a readable Title Case string[cite: 15]
            # Example: "sets_and_relations" -> "Sets And Relations"[cite: 15]
            readable_name = name_without_ext.replace('_', ' ').replace('-', ' ').title()
            
            topics.append({
                "name": readable_name,
                "file": filename
            })

    # --- POST-BUILD CLEANUP STEP ---
    # Automatically filter out system configurations like model_config.json 
    # right after the array is built, keeping your UI completely pristine.
    topics = [t for t in topics if t['file'] != 'model_config.json']

    # Sort the topics alphabetically by name so your dropdown looks organized[cite: 15]
    topics = sorted(topics, key=lambda x: x['name'])

    # Write the data into topics.json[cite: 15]
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(topics, f, indent=4)

    print(f"✅ Successfully generated {output_filename} with {len(topics)} topics.")

if __name__ == '__main__':
    generate_topics_json()[cite: 15]