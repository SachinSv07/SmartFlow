import cv2
import numpy as np
import threading
from ultralytics import YOLO
from config import CLASS_WEIGHTS

class VehicleDetector:
    def __init__(self, model_path, device='cpu'):
        self.model = YOLO(model_path)
        self.device = device
        self.model.to(device)
        self._infer_lock = threading.Lock()
        self.vehicle_classes = ['car', 'motorcycle', 'bus', 'truck']

    def detect(self, frame):
        # Run YOLOv8 detection
        with self._infer_lock:
            results = self.model(frame, device=self.device, verbose=False)[0]
        detections = []
        vehicle_counts = {cls: 0 for cls in self.vehicle_classes}
        weighted_score = 0

        for box in results.boxes:
            cls_id = int(box.cls[0])
            cls_name = self.model.names[cls_id]
            if cls_name in self.vehicle_classes:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    'class': cls_name,
                    'conf': conf,
                    'bbox': (x1, y1, x2, y2)
                })
                vehicle_counts[cls_name] += 1
                weighted_score += CLASS_WEIGHTS[cls_name]

        return detections, vehicle_counts, weighted_score
