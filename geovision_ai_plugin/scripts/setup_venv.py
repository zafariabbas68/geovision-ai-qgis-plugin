"""
Setup virtual environment for AI dependencies
"""
import os
import sys
import subprocess
import venv
from pathlib import Path


def setup_venv():
    """Create and configure virtual environment"""
    plugin_dir = Path(__file__).parent.parent
    venv_dir = plugin_dir / 'venv'
    
    if not venv_dir.exists():
        print('Creating virtual environment...')
        venv.create(venv_dir, with_pip=True)
    
    # Install dependencies
    requirements = plugin_dir / 'requirements.txt'
    
    if requirements.exists():
        print('Installing dependencies...')
        
        python_exe = venv_dir / 'bin' / 'python'
        if sys.platform == 'win32':
            python_exe = venv_dir / 'Scripts' / 'python.exe'
        
        subprocess.run([
            str(python_exe),
            '-m', 'pip', 'install',
            '-r', str(requirements)
        ])
    
    print('Setup complete!')


if __name__ == '__main__':
    setup_venv()
