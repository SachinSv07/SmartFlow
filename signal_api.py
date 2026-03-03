from flask import Flask, jsonify, request
from traffic_logic import IntersectionSignalController

app = Flask(__name__)

# Initialize your signal controller (customize as needed)
signal_controller = IntersectionSignalController()

@app.route('/signal_state', methods=['GET'])
def get_signal_state():
    # Example: get current signal state (customize logic as needed)
    state = signal_controller.get_current_state()
    return jsonify(state)

@app.route('/update', methods=['POST'])
def update_signals():
    # Example: update signal logic based on posted data
    data = request.json
    # You can process vehicle counts, queue lengths, etc. here
    signal_controller.update(data)
    return jsonify({'status': 'updated'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
