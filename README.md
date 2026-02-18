# Smart Traffic Signal Optimization System

This project uses YOLOv8, OpenCV, and NumPy to detect vehicles in traffic video and dynamically recommend green signal duration based on traffic density.

## Features
- Vehicle detection (car, bus, truck, motorcycle) using YOLOv8n
- Weighted density calculation
- Intelligent green signal timing
- Real-time bounding boxes, overlays, and FPS
- Modular, clean code

## Usage
1. Place your traffic video (e.g., `traffic.mp4`) in the project directory.
2. Run the main application:

   ```bash
   python main.py
   ```

3. Press 'q' to quit.

## Project Structure
- `main.py`: Main application loop
- `detector.py`: Vehicle detection logic
- `traffic_logic.py`: Signal timing calculation
- `config.py`: Configuration (weights, thresholds, model path)
- `requirements.txt`: Dependencies

## Requirements
- Python 3.10+
- ultralytics
- opencv-python
- numpy

## Notes
- Uses pretrained YOLOv8n weights (no training required)
- Processes every 2nd frame for performance
- Resize frames to width 640
- CPU-only inference

## License
MIT
