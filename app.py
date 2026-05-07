import cv2
import threading
import os
import time
from flask import Flask, Response, render_template, jsonify, request
from threading import Thread, Event
from traffic_logic import TrafficController

# --- Globals ---
directions = ['north', 'south', 'east', 'west']
latest_detection_frames = {d: None for d in directions}
frame_locks = {d: threading.Lock() for d in directions}
active_direction = {'dir': 'north'}
controller = TrafficController()
sim_thread = None
sim_stop_event = Event()
ambulance_presence = {d: {'seen_at': 0.0, 'active': False} for d in directions}

# --- Flask App ---
app = Flask(__name__)


def make_video_feed(direction):
    def video_feed():
        frame_counter = 0
        while True:
            with frame_locks[direction]:
                frame = latest_detection_frames[direction].copy() if latest_detection_frames[direction] is not None else None
            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame)
                if ret:
                    frame_counter += 1
                    if frame_counter % 30 == 0:
                        print(f"[video_feed_{direction}] Streaming frame {frame_counter}")
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            else:
                if frame_counter == 0:
                    print(f"[video_feed_{direction}] No frame available yet.")
            time.sleep(0.033)
    return Response(video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')


for d in directions:
    app.add_url_rule(f"/video_feed_{d}", f"video_feed_{d}", lambda d=d: make_video_feed(d))


def update_detection_frame(frame, direction):
    with frame_locks[direction]:
        latest_detection_frames[direction] = frame


def get_geofence_box(frame, direction):
    h, w = frame.shape[:2]
    if direction in ('north', 'south'):
        return (int(w * 0.34), int(h * 0.26), int(w * 0.66), int(h * 0.72))
    return (int(w * 0.26), int(h * 0.34), int(w * 0.72), int(h * 0.66))


def point_in_box(point, box):
    x, y = point
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def get_ambulance_priority_seconds(direction):
    try:
        snap = controller.intersection.get_snapshot()
        dir_data = snap.get(direction, {})
        vehicle_count = int(dir_data.get('vehicle_count', 0) or 0)
        density = int(dir_data.get('density_percentage', 0) or 0)
    except Exception:
        vehicle_count = 0
        density = 0

    # Higher density means we keep the green longer so the ambulance can clear safely.
    base = 8
    density_bonus = max(0, density // 5)
    queue_bonus = max(0, vehicle_count // 2)
    return max(8, min(35, base + density_bonus + queue_bonus))


def refresh_ambulance_priority(direction, frame_resized, geofence, detections):
    ambulance_detected = False
    for det in detections:
        if det['class'] != 'ambulance':
            continue
        x1, y1, x2, y2 = det['bbox']
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        if point_in_box(center, geofence):
            ambulance_detected = True
            break

    now = time.time()
    if ambulance_detected:
        seconds = get_ambulance_priority_seconds(direction)
        ambulance_presence[direction]['seen_at'] = now
        ambulance_presence[direction]['active'] = True
        controller.trigger_emergency_priority(direction, duration=seconds, source='ambulance-detection')
        cv2.putText(frame_resized, f"AMBULANCE GREEN: {seconds}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        # Keep the corridor green briefly after the ambulance leaves, then release.
        if ambulance_presence[direction]['active'] and now - ambulance_presence[direction]['seen_at'] > 2.0:
            ambulance_presence[direction]['active'] = False
            controller.clear_emergency_priority()
            cv2.putText(frame_resized, "AMBULANCE CLEARED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


def detection_loop():
    from detector import VehicleDetector
    from config import YOLO_MODEL_PATH
    
    print("[Detection] Initialization starting...")

    def detect_for_direction(direction, video_file):
        from detector import VehicleDetector
        from config import YOLO_MODEL_PATH
        
        detector = VehicleDetector(YOLO_MODEL_PATH, device='cpu')
        loop_count = 0
        
        while True:
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                print(f"[Detection-{direction}] ERROR: Cannot open video file {video_file}")
                break
                
            loop_count += 1
            if loop_count > 1:
                print(f"[Detection-{direction}] Restarting video (loop #{loop_count})")
            
            frame_count = 0
            last_detection_frame = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    print(f"[Detection-{direction}] End of video reached. Restarting...")
                    break

                frame_count += 1
                target_width = 320
                run_detection = (frame_count % 3 == 0)

                if run_detection:
                    h, w = frame.shape[:2]
                    scale = target_width / w
                    frame_resized = cv2.resize(frame, (target_width, int(h * scale)))
                    detections, _, _ = detector.detect(frame_resized)
                    geofence = get_geofence_box(frame_resized, direction)

                    for det in detections:
                        x1, y1, x2, y2 = det['bbox']
                        cls = det['class']
                        conf = det['conf']
                        color = (0, 255, 0)
                        cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
                        label = f"{cls} {conf:.2f}"
                        cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    refresh_ambulance_priority(direction, frame_resized, geofence, detections)

                    last_detection_frame = frame_resized.copy()
                    update_detection_frame(last_detection_frame, direction)
                elif last_detection_frame is not None:
                    update_detection_frame(last_detection_frame, direction)

                if frame_count % 30 == 0:
                    print(f"[Detection-{direction}] Streaming frame {frame_count}")

                time.sleep(0.01)
            
            cap.release()

    video_files = {
        'north': 'north.mp4',
        'south': 'south.mp4',
        'east': 'east.mp4',
        'west': 'west.mp4',
    }

    all_exist = all(os.path.exists(f) for f in video_files.values())
    if all_exist:
        print('[Detection] Using intersection video files.')
        threads = []
        for d, video_file in video_files.items():
            t = threading.Thread(target=detect_for_direction, args=(d, video_file), daemon=True)
            t.start()
            threads.append(t)
        # Don't join - let threads run in background with infinite looping
    else:
        print('[Detection] Intersection videos not found. Using webcam for demo mode.')
        cap_webcam = cv2.VideoCapture(0)
        if not cap_webcam.isOpened():
            print('[Detection] ERROR: Could not open webcam. Please check your camera device.')
            return
        # For webcam, we still open it normally (no looping)
        def detect_webcam(cap):
            detector = VehicleDetector(YOLO_MODEL_PATH, device='cpu')
            frame_count = 0
            last_detection_frame = None
            while True:
                ret, frame = cap.read()
                if not ret:
                    print('[Detection] Webcam feed lost.')
                    break
                frame_count += 1
                target_width = 320
                run_detection = (frame_count % 3 == 0)
                if run_detection:
                    h, w = frame.shape[:2]
                    scale = target_width / w
                    frame_resized = cv2.resize(frame, (target_width, int(h * scale)))
                    detections, _, _ = detector.detect(frame_resized)
                    geofence = get_geofence_box(frame_resized, 'north')
                    for det in detections:
                        x1, y1, x2, y2 = det['bbox']
                        cls = det['class']
                        conf = det['conf']
                        color = (0, 255, 0)
                        cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
                        label = f"{cls} {conf:.2f}"
                        cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    refresh_ambulance_priority('north', frame_resized, geofence, detections)
                    last_detection_frame = frame_resized.copy()
                    update_detection_frame(last_detection_frame, 'north')
                elif last_detection_frame is not None:
                    update_detection_frame(last_detection_frame, 'north')
                if frame_count % 30 == 0:
                    print(f"[Detection-webcam] Streaming frame {frame_count}")
                time.sleep(0.01)
        
        t = threading.Thread(target=detect_webcam, args=(cap_webcam,), daemon=True)
        t.start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/detection')
def detection():
    return render_template('detection.html')


@app.route('/api/active_direction', methods=['GET', 'POST'])
def api_active_direction():
    global active_direction
    if request.method == 'POST':
        data = request.get_json()
        if data and 'dir' in data:
            active_direction['dir'] = data['dir']
    return jsonify(active_direction)


@app.route('/api/timing_log')
def api_timing_log():
    if controller:
        return jsonify(controller.timing_log)
    return jsonify([])


@app.route('/api/update_counts', methods=['POST'])
def api_update_counts():
    data = request.get_json()
    if controller:
        controller.intersection.update_vehicles(data)
        controller.intersection.update_densities()
        return jsonify({'status': 'updated'})
    return jsonify({'error': 'Controller not initialized'})


@app.route('/api/status')
def api_status():
    if controller:
        return jsonify(controller.get_status())
    return jsonify({'error': 'Simulation not running'})


@app.route('/api/start', methods=['POST'])
def api_start():
    global sim_thread, sim_stop_event
    if not sim_thread or not sim_thread.is_alive():
        sim_stop_event.clear()
        sim_thread = Thread(target=controller.run_simulation, args=(sim_stop_event,), daemon=True)
        sim_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already running'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    global sim_stop_event
    sim_stop_event.set()
    return jsonify({'status': 'stopped'})


@app.route('/api/override', methods=['POST'])
def api_override():
    if controller:
        controller.manual_override()
        return jsonify({'status': 'override_triggered'})
    return jsonify({'error': 'Controller not initialized'}), 400


@app.route('/api/emergency', methods=['POST'])
def api_emergency():
    if not controller:
        return jsonify({'error': 'Controller not initialized'}), 400

    data = request.get_json(silent=True) or {}
    direction = data.get('direction', 'north')
    duration = int(data.get('duration', 12))
    if direction not in directions:
        return jsonify({'error': 'Invalid direction'}), 400

    controller.trigger_emergency_priority(direction, duration=duration, source=data.get('source', 'dashboard'))
    return jsonify({'status': 'emergency_triggered', 'direction': direction, 'duration': duration})


if __name__ == '__main__':
    sim_stop_event.clear()
    sim_thread = Thread(target=controller.run_simulation, args=(sim_stop_event,), daemon=True)
    sim_thread.start()

    detection_thread = Thread(target=detection_loop, daemon=True)
    detection_thread.start()

    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
