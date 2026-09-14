
import sys
import os
import numpy as np

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("🧪 Testing Segmentation Engine")
print("=" * 60)

try:
    from geovision_ai_plugin.core.segmentation_engine import SegmentationEngine
    print("✅ SegmentationEngine imported successfully")
    
    # Test creation without a real model (mock)
    class MockPredictor:
        def __init__(self):
            self.model = None
            
        def set_image(self, image):
            pass
            
        def predict(self, point_coords=None, point_labels=None, multimask_output=True):
            # Return dummy data
            masks = [np.ones((100, 100), dtype=bool)]
            scores = [0.8]
            logits = [None]
            return masks, scores, logits
    
    mock_predictor = MockPredictor()
    engine = SegmentationEngine(mock_predictor)
    
    print(f"✅ Engine initialized with device: {engine.device}")
    
    # Create a test image
    test_image = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    
    # Test segmentation (should return empty for mock)
    masks, confidences = engine.segment(test_image, confidence_threshold=0.5)
    print(f"✅ Segmentation completed: {len(masks)} masks")
    
    # Test post-processing
    processed = engine.post_process_masks([np.ones((50, 50), dtype=bool)], min_area=10)
    print(f"✅ Post-processing completed: {len(processed)} masks")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
