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


def detection_loop():
    from detector import VehicleDetector
    from config import YOLO_MODEL_PATH

    def detect_for_direction(direction, cap):
        detector = VehicleDetector(YOLO_MODEL_PATH, device='cpu')
        frame_count = 0
        last_detection_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[Detection-{direction}] End of video or cannot fetch the frame.")
                break

            frame_count += 1
            target_width = 320
            run_detection = (frame_count % 3 == 0)

            if run_detection:
                h, w = frame.shape[:2]
                scale = target_width / w
                frame_resized = cv2.resize(frame, (target_width, int(h * scale)))
                detections, _, _ = detector.detect(frame_resized)

                for det in detections:
                    x1, y1, x2, y2 = det['bbox']
                    cls = det['class']
                    conf = det['conf']
                    color = (0, 255, 0)
                    cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, 2)
                    label = f"{cls} {conf:.2f}"
                    cv2.putText(frame_resized, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                last_detection_frame = frame_resized.copy()
                update_detection_frame(last_detection_frame, direction)
            elif last_detection_frame is not None:
                update_detection_frame(last_detection_frame, direction)

            if frame_count % 30 == 0:
                print(f"[Detection-{direction}] Streaming frame {frame_count}")

            time.sleep(0.01)

    video_files = {
        'north': 'north.mp4',
        'south': 'south.mp4',
        'east': 'east.mp4',
        'west': 'west.mp4',
    }

    all_exist = all(os.path.exists(f) for f in video_files.values())
    if all_exist:
        caps = {d: cv2.VideoCapture(f) for d, f in video_files.items()}
        print('[Detection] Using intersection video files.')
    else:
        print('[Detection] Intersection videos not found. Using webcam for demo mode.')
        caps = {'webcam': cv2.VideoCapture(0)}
        if not caps['webcam'].isOpened():
            print('[Detection] ERROR: Could not open webcam. Please check your camera device.')
            return

    threads = []
    for d in (caps.keys() if all_exist else ['webcam']):
        t = threading.Thread(target=detect_for_direction, args=(d, caps[d]), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


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


if __name__ == '__main__':
    sim_stop_event.clear()
    sim_thread = Thread(target=controller.run_simulation, args=(sim_stop_event,), daemon=True)
    sim_thread.start()

    detection_thread = Thread(target=detection_loop, daemon=True)
    detection_thread.start()

    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
