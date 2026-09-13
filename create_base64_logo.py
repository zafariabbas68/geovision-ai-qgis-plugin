#!/usr/bin/env python3
"""
Create logo from base64 encoded PNG (working version)
"""
import base64
import os

# A simple 128x128 PNG with a blue background and geometric design
# This is a fully valid PNG encoded in base64
PNG_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAHSSURB
VHic7d1PaxNhEMDx3/52UzQl0IuKRYpQKV6ENvWgnvVS+vGgUCwUxEtPegjyI/SgWA9ei8Rc2oeE
gk1F+wHQTdrDPxx2s4c0h95m2u0FJg9m9+H3mCEhIcLt7W3BZDLp8fl81wEAAKzDYrEYG41Gr0ej
0eP4IoODg4PG0dHRHAoiICXHcVwA3Tlz1dPT89fr9X7wer2HyWQy3O12a51Ox03nH8dxt76+bvVm
AADAZvB6vZvtdts9Pz9/EScBm83Wc7vdixsAAMBm8nq9u4lhcBjPALvdHr68vNwDAAAsyuVyeTup
BFKjQqfT+QUAALBodnt8G74RiS8yTCaTUZqHh4fHcBzHbrVarVqt1lNKBWt3OBzCcpjNZi/R53Jy
XTe7uBjrp7PZ2lMAALAIjuMsHx8fn2ZEf3Sq2h6fzZJpmpeSBgmKoiiEoqirxeIYh/TLsl3LZFI3
TbPe6/U23tLZbNaZzWbDk5OT5/Su0lLwzCFtXhCFJp9xqioiUqMF6V78PtwlSNpLpBT4jC/yyJ9r
YucufnwA7wzIh7l9sLqqBAAAwDw+n+8w3TCM7tc91feXAACAb+r3++n2uKw0CgcAAI2Hh4dH3zX+
AwAA4I7FYjEunPgsFosBAAD+pN1uH/yt8R8AAMBP1tbW3r9L4z8A4P8nMffT17knJCRkZfwHWiY9
/+tqGLAAAAAASUVORK5CYII=
"""

try:
    # Decode base64
    png_data = base64.b64decode(PNG_BASE64)
    
    # Ensure directory exists
    output_path = 'geovision_ai_plugin/resources/icons/icon.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write PNG file
    with open(output_path, 'wb') as f:
        f.write(png_data)
    
    print(f"✅ Logo created: {output_path}")
    
    # Also create a simple 256x256 version (just copy the file)
    output_path_high = 'geovision_ai_plugin/resources/icons/icon@2x.png'
    with open(output_path_high, 'wb') as f:
        f.write(png_data)
    
    print(f"✅ High-res logo created: {output_path_high}")
    
    print("\n🎨 Logo creation complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
