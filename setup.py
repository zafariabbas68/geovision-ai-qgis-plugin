"""
Setup script for GeoVision AI plugin
"""
from setuptools import setup, find_packages

setup(
    name='geovision-ai-plugin',
    version='1.0.0',
    description='AI-powered raster-to-vector segmentation for QGIS',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'torch>=2.0.0',
        'torchvision>=0.15.0',
        'numpy>=1.24.0',
        'opencv-python>=4.8.0',
        'pillow>=9.0.0',
        'segment-anything>=1.0',
        'ultralytics>=8.0.0',
    ],
    entry_points={
        'qgis.plugins': [
            'geovision-ai-plugin = geovision_ai_plugin:GeoVisionAIPlugin',
        ],
    },
)
