
import configparser
import os

metadata_file = 'geovision_ai_plugin/metadata.txt'

if not os.path.exists(metadata_file):
    print(f"❌ metadata.txt not found at {metadata_file}")
    exit(1)

try:
    config = configparser.ConfigParser()
    config.read(metadata_file)
    
    # Check if [General] section exists
    if config.has_section('General'):
        print("✅ [General] section found")
        print(f"   name: {config.get('General', 'name')}")
        print(f"   version: {config.get('General', 'version')}")
        print(f"   description: {config.get('General', 'description')}")
    else:
        print("❌ [General] section not found")
        print("Available sections:", config.sections())
        exit(1)
    
    # Check if [Processing] section exists
    if config.has_section('Processing'):
        print("✅ [Processing] section found")
    else:
        print("⚠️  [Processing] section not found (optional)")
    
    print("\n✅ metadata.txt is valid!")
    
except Exception as e:
    print(f"❌ Error reading metadata: {e}")
    exit(1)
