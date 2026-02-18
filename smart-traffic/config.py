# YOLOv8 vehicle class weights
CLASS_WEIGHTS = {
    'car': 1,
    'motorcycle': 1,
    'bus': 3,
    'truck': 4
}

# Signal timing thresholds (weighted score: (min, max, duration))
SIGNAL_THRESHOLDS = [
    (0, 5, 20),
    (6, 15, 40),
    (16, float('inf'), 60)
]

# YOLOv8n model path (pretrained from ultralytics)
YOLO_MODEL_PATH = 'yolov8n.pt'  # Uses ultralytics default pretrained weights
