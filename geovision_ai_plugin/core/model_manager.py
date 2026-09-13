"""
AI Model manager - SAM1 vit_b/vit_l/vit_h
"""

import os
import urllib.request
from pathlib import Path


SAM1_CHECKPOINTS = {
    "vit_b": {"filename": "sam_vit_b_01ec64.pth", "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth", "size_mb": 375},
    "vit_l": {"filename": "sam_vit_l_0b3195.pth", "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth", "size_mb": 1200},
    "vit_h": {"filename": "sam_vit_h_4b8939.pth", "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", "size_mb": 2400},
}


class ModelManager:
    """Manage SAM models"""

    MODEL_ARCH_MAP = {
        "sam2_tiny": "vit_b",
        "sam2_1_b": "vit_l",
        "sam3": "vit_h",
    }

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.model_dir = config_manager.get_model_dir()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.models = {}
        self.device = self._get_device()
        print(f"Model directory: {self.model_dir}")
        print(f"Device: {self.device}")

    def _get_device(self):
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        except Exception:
            return "cpu"

    def get_model(self, model_type):
        if model_type in self.models:
            return self.models[model_type]

        arch = self.MODEL_ARCH_MAP.get(model_type)
        if arch is None:
            print(f"Unknown model type: {model_type}")
            return None

        print(f"Loading {model_type} (SAM1 {arch})...")

        try:
            model = self._load_sam1(arch)
            if model is not None:
                self.models[model_type] = model
                print(f"{model_type} loaded successfully")
            return model
        except Exception as e:
            print(f"Failed to load {model_type}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_sam1(self, arch):
        from segment_anything import sam_model_registry, SamPredictor

        ckpt_info = SAM1_CHECKPOINTS[arch]
        ckpt_path = self.model_dir / ckpt_info["filename"]

        if not ckpt_path.exists():
            print(f"Downloading {ckpt_info['filename']} (~{ckpt_info['size_mb']} MB)...")
            self._download_file(ckpt_info["url"], ckpt_path)
            print(f"Downloaded to {ckpt_path}")

        actual_size_mb = ckpt_path.stat().st_size / (1024 * 1024)
        if actual_size_mb < ckpt_info["size_mb"] * 0.9:
            print(f"Checkpoint size ({actual_size_mb:.0f} MB) seems incomplete")
            ckpt_path.unlink()
            raise RuntimeError("Checkpoint download incomplete, retry")

        print(f"Loading SAM1 {arch} from {ckpt_path}")
        sam = sam_model_registry[arch](checkpoint=str(ckpt_path))
        sam.to(device=self.device)
        return SamPredictor(sam)

    def _download_file(self, url, dest_path):
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0 and block_num % 100 == 0:
                percent = min(100, 100 * downloaded // total_size)
                print(f"   {percent}% ({downloaded // (1024*1024)} MB)")

        urllib.request.urlretrieve(url, dest_path, reporthook=progress_hook)

    def get_available_models(self):
        return list(self.MODEL_ARCH_MAP.keys())

    def get_model_info(self, model_type):
        arch = self.MODEL_ARCH_MAP.get(model_type, "vit_b")
        info = {
            "vit_b": {"name": "SAM vit_b", "size": "~375 MB", "speed": "Fast"},
            "vit_l": {"name": "SAM vit_l", "size": "~1.2 GB", "speed": "Medium"},
            "vit_h": {"name": "SAM vit_h", "size": "~2.4 GB", "speed": "Slow"},
        }
        return info.get(arch, {"name": "Unknown"})
