import os
import sys

# Ensure we can import from src
current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, 'new_workflow'))

from src.config_loader import save_config, load_config

def fix():
    config_path = os.path.join(current_dir, 'new_workflow', 'config.yaml')
    print(f"Target config file: {config_path}")

    if not os.path.exists(config_path):
        print(f"Error: File not found at {config_path}")
        return

    try:
        # Load existing config
        config = load_config(config_path)
        
        # Update paths to match user's structure (txts_zsk)
        config['paths']['summary_save_path'] = "new_workflow/txts_zsk/literature_summary.json"
        config['paths']['result_csv'] = "new_workflow/txts_zsk/summary_sorted.csv"
        
        # Save back
        save_config(config_path, config)
        print("✅ Config updated successfully!")
        print(f"New summary_save_path: {config['paths']['summary_save_path']}")
        
    except Exception as e:
        print(f"❌ Failed to update config: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix()
