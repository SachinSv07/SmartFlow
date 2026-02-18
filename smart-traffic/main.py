import cv2
import time
import numpy as np
from detector import VehicleDetector
from traffic_logic import calculate_signal_time
from config import YOLO_MODEL_PATH, CLASS_WEIGHTS, SIGNAL_THRESHOLDS

# --- Main Application ---
def main():
    video_path = 'traffic.mp4'  # Change to your video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return

    detector = VehicleDetector(YOLO_MODEL_PATH, device='cpu')
    frame_count = 0
    prev_time = time.time()
    fps = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video or cannot fetch the frame.")
            break

        frame_count += 1
        # Process every 2nd frame for performance
        if frame_count % 2 != 0:
            continue

        # Resize frame to width 640
        h, w = frame.shape[:2]
        scale = 640 / w
        frame_resized = cv2.resize(frame, (640, int(h * scale)))

        # Detect vehicles
        detections, vehicle_counts, weighted_score = detector.detect(frame_resized)
        green_time = calculate_signal_time(weighted_score, SIGNAL_THRESHOLDS)

        # Draw bounding boxes and labels
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cls = det['class']
            conf = det['conf']
            color = (0, 255, 0)
            cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
            label = f"{cls} {conf:.2f}"
            cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Overlay info
        y0 = 30
        dy = 30
        cv2.putText(frame_resized, f"Vehicle counts: {vehicle_counts}", (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_resized, f"Weighted density: {weighted_score}", (10, y0+dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_resized, f"Green signal: {green_time} sec", (10, y0+2*dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.putText(frame_resized, f"FPS: {fps:.2f}", (10, y0+3*dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

        # Show frame
        cv2.imshow('Smart Traffic Signal Optimization', frame_resized)

        # Log to console
        print(f"Frame {frame_count}: Weighted={weighted_score}, Green={green_time}s, Counts={vehicle_counts}")

        # FPS calculation
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time)
        prev_time = curr_time

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Quitting...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
