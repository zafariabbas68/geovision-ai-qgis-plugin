#!/usr/bin/env python3
"""
Create logo from base64 encoded data
"""
import base64
import os
from PIL import Image
import io

# Base64 encoded professional logo (blue with geometric pattern)
logo_base64 = """
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
SUVORK5CYII=
"""

try:
    # Decode base64
    image_data = base64.b64decode(logo_base64)
    image = Image.open(io.BytesIO(image_data))
    
    # Ensure directory exists
    output_path = 'geovision_ai_plugin/resources/icons/icon.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the image
    image.save(output_path, 'PNG')
    print(f"✅ Logo created: {output_path}")
    
    # Also save high-res version
    image_high = image.resize((256, 256), Image.Resampling.LANCZOS)
    output_path_high = 'geovision_ai_plugin/resources/icons/icon@2x.png'
    image_high.save(output_path_high, 'PNG')
    print(f"✅ High-res logo created: {output_path_high}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Please install PIL: pip install Pillow")
