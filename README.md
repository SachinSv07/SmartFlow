# Smart Traffic Control Dashboard

An AI-assisted traffic signal management system built with Flask, OpenCV, YOLOv8, and a web dashboard. The project detects vehicles from live or recorded video, estimates traffic density, and adjusts signal timing dynamically. It also includes an ambulance priority mode with geofence-based emergency handling.

## Highlights

- Real-time vehicle detection using YOLOv8n
- Dynamic signal timing based on traffic density
- Web dashboard for live traffic monitoring
- Live video feeds for four directions
- Ambulance priority mode with geofence detection
- Manual override and live status controls
- Traffic logs and analytics panels

## Tech Stack

- Python 3.10+
- Flask
- OpenCV
- Ultralytics YOLOv8
- NumPy
- HTML, CSS, JavaScript

## Project Layout

- [app.py](app.py): Flask application, API endpoints, live detection feeds
- [main.py](main.py): Console-based detection and simulation entry point
- [detector.py](detector.py): YOLO vehicle detection wrapper
- [traffic_logic.py](traffic_logic.py): Signal timing and emergency priority logic
- [intersection_sim.py](intersection_sim.py): Realistic intersection simulator
- [config.py](config.py): Model path, class weights, and thresholds
- [templates/](templates): Dashboard and detection pages
- [static/](static): CSS and JavaScript assets

## Features

### Vehicle Detection

- Detects cars, buses, trucks, motorcycles, and ambulances when supported by the model
- Draws bounding boxes and labels on live video

### Signal Control

- Calculates green time from vehicle density
- Updates signal phases automatically
- Logs timing decisions for the dashboard

### Ambulance Priority

- Detects ambulance presence in a geofenced area
- Forces the matching direction green
- Keeps the green light active until the ambulance clears the geofence
- Shows emergency state in the dashboard UI

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/SachinSv07/SmartFlow.git
cd SmartFlow
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the web application

```bash
python app.py
```

Open the dashboard in your browser at the local address shown in the terminal.

## Optional: Run the console simulation

```bash
python main.py
```

## API Endpoints

- `GET /api/status` — current traffic and emergency status
- `GET /api/timing_log` — signal timing log
- `POST /api/start` — start the simulation
- `POST /api/stop` — stop the simulation
- `POST /api/override` — trigger manual override
- `POST /api/emergency` — trigger ambulance priority manually

## Notes

- The default model is `yolov8n.pt`.
- Ambulance detection requires the model to support an `ambulance` class.
- If no intersection videos are found, the app falls back to webcam mode.

## Troubleshooting

- If Flask or OpenCV is missing, reinstall dependencies with `pip install -r requirements.txt`.
- If the video feed is blank, check that the `north.mp4`, `south.mp4`, `east.mp4`, and `west.mp4` files exist.
- If ambulance detection does not trigger, confirm that the model includes the ambulance class.

## License

MIT
