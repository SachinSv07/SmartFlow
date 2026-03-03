import cv2
import time
import numpy as np
import requests
from app import update_detection_frame
from detector import VehicleDetector
## from traffic_logic import calculate_signal_time
from config import YOLO_MODEL_PATH, CLASS_WEIGHTS, SIGNAL_THRESHOLDS

print("main.py loaded.")
# --- Main Application ---
def main():
    # Try to use intersection videos, else fallback to webcam
    import os
    video_files = {
        'north': 'north.mp4',
        'south': 'south.mp4',
        'east': 'east.mp4',
        'west': 'west.mp4'
    }
    all_exist = all(os.path.exists(f) for f in video_files.values())
    if all_exist:
        caps = {d: cv2.VideoCapture(f) for d, f in video_files.items()}
        print("Using intersection video files.")
    else:
        print("Intersection videos not found. Using webcam for demo mode.")
        caps = {'webcam': cv2.VideoCapture(0)}
        if not caps['webcam'].isOpened():
            print("ERROR: Could not open webcam. Please check your camera device.")
            return

    detector = VehicleDetector(YOLO_MODEL_PATH, device='cpu')
    from traffic_logic import TrafficController
    controller = TrafficController()
    frame_count = 0
    prev_time = time.time()
    fps = 0

    print("Detection loop starting...")
    while True:
        frames = {}
        ret_flags = {}
        for d, cap in caps.items():
            ret, frame = cap.read()
            ret_flags[d] = ret
            frames[d] = frame if ret else None
        if not all(ret_flags.values()):
            print("End of video or cannot fetch the frame. ret_flags:", ret_flags)
            break
        # Print a heartbeat every 100 frames
        if hasattr(main, 'frame_counter'):
            main.frame_counter += 1
        else:
            main.frame_counter = 1
        if main.frame_counter % 100 == 0:
            print(f"Processed {main.frame_counter} frames...")

        frame_count += 1
        if frame_count % 2 != 0:
            continue

        densities = {}
        display_frames = {}
        vehicle_counts_for_dashboard = {}
        if 'webcam' in caps:
            d = 'webcam'
            frame = frames[d]
            if frame is None:
                break
            h, w = frame.shape[:2]
            scale = 640 / w
            frame_resized = cv2.resize(frame, (640, int(h * scale)))
            detections, vehicle_counts, weighted_score = detector.detect(frame_resized)
            densities[d] = weighted_score
            display_frames[d] = frame_resized
            vehicle_counts_for_dashboard[d] = sum(vehicle_counts.values())
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                cls = det['class']
                conf = det['conf']
                color = (0, 255, 0)
                cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
                label = f"{cls} {conf:.2f}"
                cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            update_detection_frame(frame_resized)
        else:
            for d in ['north', 'south', 'east', 'west']:
                frame = frames[d]
                h, w = frame.shape[:2]
                scale = 640 / w
                frame_resized = cv2.resize(frame, (640, int(h * scale)))
                detections, vehicle_counts, weighted_score = detector.detect(frame_resized)
                densities[d] = weighted_score
                display_frames[d] = frame_resized
                vehicle_counts_for_dashboard[d] = sum(vehicle_counts.values())
                for det in detections:
                    x1, y1, x2, y2 = det['bbox']
                    cls = det['class']
                    conf = det['conf']
                    color = (0, 255, 0)
                    cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
                    label = f"{cls} {conf:.2f}"
                    cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            # Send latest detection frame to dashboard (show north view)
            update_detection_frame(display_frames['north'])

        # Send vehicle counts to dashboard
        try:
            requests.post('http://localhost:5000/api/update_counts', json=vehicle_counts_for_dashboard, timeout=0.5)
        except Exception as e:
            print(f"Dashboard update failed: {e}")

        # Intersection signal logic
        result = controller.get_status()

        # Overlay info on each frame
        y0 = 30
        dy = 30
        for d in ['north', 'south', 'east', 'west']:
            cv2.putText(display_frames[d], f"Density: {densities[d]}", (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(display_frames[d], f"Active phase: {result['active_phase']}", (10, y0+dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.putText(display_frames[d], f"Green remaining: {result['green_time_remaining']}s", (10, y0+2*dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.putText(display_frames[d], f"FPS: {fps:.2f}", (10, y0+5*dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)


        # Log to console
        print(f"Frame {frame_count}: Densities={densities}, Signal={result}")

        # FPS calculation
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time)
        prev_time = curr_time

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Quitting...")
            break


    for cap in caps.values():
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    print("main.py __main__ entrypoint reached.")
    main()
