
import os
import struct
import zlib

def create_png(width, height, pixels):
    """Create a PNG file from pixel data"""
    # PNG header
    header = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr = struct.pack('>I4sIIBBBBB', width, height, 8, 2, 0, 0, 0, b'IHDR')
    ihdr = struct.pack('>I', len(ihdr)-4) + ihdr
    
    # IDAT chunk (compressed image data)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            raw_data += pixels[y][x]
    
    compressed = zlib.compress(raw_data, 9)
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed
    idat += struct.pack('>I', zlib.crc32(b'IDAT' + compressed))
    
    # IEND chunk
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', 0xae426082)
    
    return header + ihdr + idat + iend

def create_logo():
    """Create a professional logo"""
    size = 128
    
    # Define colors (RGBA)
    blue = (74, 144, 217, 255)      # #4A90D9
    white = (255, 255, 255, 255)    # #FFFFFF
    teal = (0, 200, 150, 255)       # #00C896
    dark_blue = (44, 84, 177, 255)  # #2C54B1
    
    # Create pixel array
    pixels = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]
    
    # Draw rounded rectangle background (approximate)
    margin = 8
    radius = 20
    for y in range(size):
        for x in range(size):
            # Check if inside rounded rectangle
            if (x >= margin and x < size - margin and 
                y >= margin and y < size - margin):
                # Check corners for rounding
                in_corner = False
                # Top-left corner
                if x < margin + radius and y < margin + radius:
                    if ((x - margin - radius) ** 2 + (y - margin - radius) ** 2) > radius ** 2:
                        in_corner = True
                # Top-right corner
                if x > size - margin - radius and y < margin + radius:
                    if ((x - (size - margin - radius)) ** 2 + (y - margin - radius) ** 2) > radius ** 2:
                        in_corner = True
                # Bottom-left corner
                if x < margin + radius and y > size - margin - radius:
                    if ((x - margin - radius) ** 2 + (y - (size - margin - radius)) ** 2) > radius ** 2:
                        in_corner = True
                # Bottom-right corner
                if x > size - margin - radius and y > size - margin - radius:
                    if ((x - (size - margin - radius)) ** 2 + (y - (size - margin - radius)) ** 2) > radius ** 2:
                        in_corner = True
                
                if not in_corner:
                    pixels[y][x] = blue
    
    # Draw outer circle (vision ring)
    center = size // 2
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            dist = (dx ** 2 + dy ** 2) ** 0.5
            
            # Draw ring (between radius 32 and 38)
            if 32 <= dist <= 38:
                if pixels[y][x] == (0, 0, 0, 0):
                    # Make sure it's in the background
                    continue
                # Calculate angle for anti-aliasing
                ring_dist = abs(dist - 35)
                if ring_dist < 2:
                    alpha = int(255 * (1 - ring_dist / 2))
                    pixels[y][x] = (255, 255, 255, alpha)
                else:
                    pixels[y][x] = white
    
    # Draw inner circle (pupil)
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            dist = (dx ** 2 + dy ** 2) ** 0.5
            
            if dist <= 16:
                pixels[y][x] = teal
            elif 16 < dist <= 18:
                # Anti-aliased edge
                alpha = int(255 * (1 - (dist - 16) / 2))
                pixels[y][x] = (teal[0], teal[1], teal[2], alpha)
    
    # Draw vision rays (simple lines)
    for angle in range(0, 360, 45):
        import math
        rad = math.radians(angle)
        for t in range(42, 54):
            x = int(center + t * math.cos(rad))
            y = int(center + t * math.sin(rad))
            if 0 <= x < size and 0 <= y < size:
                pixels[y][x] = white
    
    # Save as PNG
    output_path = 'geovision_ai_plugin/resources/icons/icon.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    png_data = create_png(size, size, pixels)
    with open(output_path, 'wb') as f:
        f.write(png_data)
    
    print(f"✅ Logo created: {output_path}")
    
    # Also create a 256x256 version (scaled up)
    # For simplicity, we'll just use the same image
    # QGIS will scale it if needed
    
    return True

if __name__ == '__main__':
    try:
        create_logo()
        print("\n🎨 Logo creation complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
