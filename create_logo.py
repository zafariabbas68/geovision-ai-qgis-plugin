#!/usr/bin/env python3
"""
Create a professional logo for GeoVision AI
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_logo():
    """Create a professional logo for the plugin"""
    
    # Create a 128x128 image with transparent background
    size = 128
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    primary_color = (74, 144, 217)  # Professional blue
    secondary_color = (255, 255, 255)  # White
    accent_color = (0, 200, 150)  # Teal accent
    
    # Draw a rounded rectangle background
    rect_margin = 8
    draw.rounded_rectangle(
        [(rect_margin, rect_margin), (size - rect_margin, size - rect_margin)],
        radius=20,
        fill=primary_color,
        outline=secondary_color,
        width=2
    )
    
    # Draw a stylized "G" or geometric shape
    center = size // 2
    
    # Draw a modern geometric pattern - a stylized eye/vision icon
    # Outer circle
    draw.ellipse(
        [(center - 40, center - 40), (center + 40, center + 40)],
        outline=secondary_color,
        width=3
    )
    
    # Inner circle (pupil/vision)
    draw.ellipse(
        [(center - 18, center - 18), (center + 18, center + 18)],
        fill=accent_color,
        outline=secondary_color,
        width=2
    )
    
    # Vision rays (like a lens)
    for i in range(8):
        angle = i * 45
        import math
        rad = math.radians(angle)
        x1 = center + 45 * math.cos(rad)
        y1 = center + 45 * math.sin(rad)
        x2 = center + 55 * math.cos(rad)
        y2 = center + 55 * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=secondary_color, width=2)
    
    # Try to add text "GV" if font is available
    try:
        # Try to load a font
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/HelveticaNeue.ttc'
        ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, 24)
                    break
                except:
                    continue
        
        if font:
            # Add "GV" text at the bottom
            text = "GV"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size - text_width) // 2
            y = size - 30
            draw.text((x, y), text, fill=secondary_color, font=font)
    except:
        pass
    
    # Save the logo
    output_path = 'geovision_ai_plugin/resources/icons/icon.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    print(f"✅ Logo created: {output_path}")
    
    # Also create a 256x256 version for high DPI
    img_high = img.resize((256, 256), Image.Resampling.LANCZOS)
    output_path_high = 'geovision_ai_plugin/resources/icons/icon@2x.png'
    img_high.save(output_path_high, 'PNG')
    print(f"✅ High-res logo created: {output_path_high}")
    
    return True

if __name__ == '__main__':
    try:
        create_logo()
        print("\n🎨 Logo creation complete!")
        print("📌 The logo has been saved to the plugin resources.")
    except Exception as e:
        print(f"❌ Error creating logo: {e}")
        print("\n📌 Falling back to alternative logo creation...")
