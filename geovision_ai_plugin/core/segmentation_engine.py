"""
Lightweight segmentation engine with crash protection
"""
import numpy as np
import gc

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from typing import List, Tuple


class SegmentationEngine:
    """Lightweight segmentation with crash protection"""

    def __init__(self, model_predictor):
        self.predictor = model_predictor
        self.device = self._get_device()
        self.use_opencv = OPENCV_AVAILABLE

    def _get_device(self):
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'
            else:
                return 'cpu'
        except:
            return 'cpu'

    def segment(self, image: np.ndarray, class_name: str = None, 
                confidence_threshold: float = 0.5, feedback=None) -> Tuple[List, List]:
        """Run segmentation with crash protection"""
        
        if feedback:
            feedback.setProgress(10)
            feedback.pushInfo(f"Starting segmentation for: {class_name or 'objects'}")

        try:
            # Check if predictor is available
            if self.predictor is None:
                feedback.pushWarning("Model not available - using mock segmentation")
                return self._mock_segmentation(image)
            
            # Check image
            if image is None or len(image.shape) != 3:
                raise ValueError("Invalid image")
            
            # Limit image size to prevent crashes
            h, w = image.shape[:2]
            max_size = 512
            if h > max_size or w > max_size:
                # Scale down
                scale = min(max_size / h, max_size / w)
                new_h = int(h * scale)
                new_w = int(w * scale)
                if self.use_opencv:
                    image = cv2.resize(image, (new_w, new_h))
                else:
                    # Simple resize without OpenCV
                    image = image[::int(1/scale), ::int(1/scale)]
                feedback.pushInfo(f"Resized image to {image.shape[1]}x{image.shape[0]} for memory")

            if feedback:
                feedback.setProgress(20)

            # Convert to BGR
            if self.use_opencv:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = image[:, :, ::-1]
            
            if feedback:
                feedback.setProgress(30)

            # Set image
            self.predictor.set_image(image_bgr)
            
            if feedback:
                feedback.setProgress(40)

            # Generate masks with limited points
            masks, confidences = self._safe_segmentation(image_bgr, confidence_threshold, feedback)
            
            if feedback:
                feedback.setProgress(80)
                feedback.pushInfo(f"Generated {len(masks)} masks")
            
            # Filter
            filtered_masks = []
            filtered_confidences = []
            for mask, conf in zip(masks, confidences):
                if conf >= confidence_threshold:
                    filtered_masks.append(mask)
                    filtered_confidences.append(conf)
            
            # Clean up
            gc.collect()
            
            if feedback:
                feedback.setProgress(90)
                feedback.pushInfo(f"Filtered to {len(filtered_masks)} masks")
            
            return filtered_masks, filtered_confidences
            
        except Exception as e:
            if feedback:
                feedback.pushWarning(f"Segmentation error: {e}")
            return self._mock_segmentation(image)

    def _safe_segmentation(self, image_bgr, confidence_threshold, feedback):
        """Safe segmentation with limited operations"""
        try:
            from segment_anything import SamAutomaticMaskGenerator
            
            sam_model = self.predictor.model
            mask_generator = SamAutomaticMaskGenerator(
                model=sam_model,
                points_per_side=16,  # Reduced for speed
                pred_iou_thresh=confidence_threshold,
                stability_score_thresh=0.95,
                crop_n_layers=0,  # No cropping for speed
                min_mask_region_area=50
            )
            
            if feedback:
                feedback.pushInfo("Generating masks (this may take a moment)...")
            
            masks_data = mask_generator.generate(image_bgr)
            
            masks = []
            confidences = []
            for mask_data in masks_data:
                masks.append(mask_data['segmentation'])
                confidences.append(mask_data.get('predicted_iou', 0.5))
            
            return masks, confidences
            
        except Exception as e:
            print(f"Mask generation failed: {e}")
            return [], []

    def _mock_segmentation(self, image):
        """Return mock segmentation for testing"""
        h, w = image.shape[:2]
        # Create a simple square mask
        mask = np.zeros((h, w), dtype=bool)
        margin = int(min(h, w) * 0.2)
        mask[margin:h-margin, margin:w-margin] = True
        return [mask], [0.5]

    def post_process_masks(self, masks: List[np.ndarray], min_area: float = 0) -> List[np.ndarray]:
        """Post-process masks with crash protection"""
        processed_masks = []
        
        for mask in masks:
            try:
                if min_area > 0:
                    area = np.sum(mask)
                    if area < min_area:
                        continue
                processed_masks.append(mask)
            except:
                continue
        
        return processed_masks

    def segment_with_text_prompt(self, image: np.ndarray, text_prompt: str,
                                 confidence_threshold: float = 0.5) -> Tuple[List, List]:
        """Text prompt placeholder"""
        return [], []
