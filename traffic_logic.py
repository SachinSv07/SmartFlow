

# --- Traffic Signal Decision Logic for 4-Way Intersection ---
import time
import random
import math
from threading import Lock

class Intersection:
    def __init__(self):
        self.directions = {
            'north': {'vehicle_count': 0, 'density_percentage': 0, 'waiting_time': 0, 'signal_state': 'RED'},
            'south': {'vehicle_count': 0, 'density_percentage': 0, 'waiting_time': 0, 'signal_state': 'RED'},
            'east':  {'vehicle_count': 0, 'density_percentage': 0, 'waiting_time': 0, 'signal_state': 'RED'},
            'west':  {'vehicle_count': 0, 'density_percentage': 0, 'waiting_time': 0, 'signal_state': 'RED'},
        }
        self.lock = Lock()

    def update_vehicles(self, vehicle_counts=None):
        with self.lock:
            if vehicle_counts:
                for dir in self.directions:
                    self.directions[dir]['vehicle_count'] = vehicle_counts.get(dir, 0)
            else:
                for dir in self.directions:
                    self.directions[dir]['vehicle_count'] = random.randint(0, 30)

    def update_densities(self):
        with self.lock:
            total = sum(self.directions[dir]['vehicle_count'] for dir in self.directions)
            for dir in self.directions:
                if total > 0:
                    self.directions[dir]['density_percentage'] = int(100 * self.directions[dir]['vehicle_count'] / total)
                else:
                    self.directions[dir]['density_percentage'] = 0

    def increment_waiting(self, active_dirs):
        with self.lock:
            for dir in self.directions:
                if dir not in active_dirs:
                    self.directions[dir]['waiting_time'] += 1
                else:
                    self.directions[dir]['waiting_time'] = 0

    def set_signal_states(self, active_dirs, yellow_dirs=None):
        with self.lock:
            for dir in self.directions:
                if yellow_dirs and dir in yellow_dirs:
                    self.directions[dir]['signal_state'] = 'YELLOW'
                elif dir in active_dirs:
                    self.directions[dir]['signal_state'] = 'GREEN'
                else:
                    self.directions[dir]['signal_state'] = 'RED'

    def get_snapshot(self):
        with self.lock:
            return {dir: self.directions[dir].copy() for dir in self.directions}



# --- TrafficController class ---
class TrafficController:
    def __init__(self):
        self.intersection = Intersection()
        self.active_phase = 1  # 1: NS, 2: EW
        self.green_time_remaining = 10
        self.last_switch_time = time.time()
        self.phase_start_time = time.time()
        self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        self.starvation_limit = 120
        self.min_green = 10
        self.max_extension = 30
        self.yellow_duration = 3
        self.manual_override_flag = False
        self.emergency_override = {
            'active': False,
            'direction': None,
            'source': None,
            'expires_at': 0.0,
        }
        self.lock = Lock()
        self.congestion_history = []
        self.timing_log = []

    def _phase_for_direction(self, direction):
        return 1 if direction in ('north', 'south') else 2

    def _refresh_emergency_state(self):
        if self.emergency_override['active'] and time.time() >= self.emergency_override['expires_at']:
            self.emergency_override = {
                'active': False,
                'direction': None,
                'source': None,
                'expires_at': 0.0,
            }

    def trigger_emergency_priority(self, direction, duration=12, source='ambulance'):
        with self.lock:
            self.emergency_override = {
                'active': True,
                'direction': direction,
                'source': source,
                'expires_at': time.time() + max(3, duration),
            }
            self.active_phase = self._phase_for_direction(direction)
            self.green_time_remaining = duration
            self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}

    def clear_emergency_priority(self):
        with self.lock:
            self.emergency_override = {
                'active': False,
                'direction': None,
                'source': None,
                'expires_at': 0.0,
            }

    def get_status(self):
        with self.lock:
            self._refresh_emergency_state()
            emergency_active = self.emergency_override['active']
            emergency_direction = self.emergency_override['direction']
            emergency_source = self.emergency_override['source']
            emergency_remaining = 0
            if emergency_active:
                emergency_remaining = max(0, int(math.ceil(self.emergency_override['expires_at'] - time.time())))

        snap = self.intersection.get_snapshot()
        total_vehicles = sum(snap[dir]['vehicle_count'] for dir in snap)
        if total_vehicles <= 20:
            congestion = 'LOW'
        elif total_vehicles <= 50:
            congestion = 'MEDIUM'
        else:
            congestion = 'HIGH'

        if emergency_active and emergency_direction:
            active_phase_label = f"Emergency - {emergency_direction.title()}"
        else:
            active_phase_label = 'North-South' if self.active_phase == 1 else 'East-West'

        return {
            **snap,
            'active_phase': active_phase_label,
            'green_time_remaining': self.green_time_remaining,
            'total_vehicles': total_vehicles,
            'congestion_level': congestion,
            'emergency_active': emergency_active,
            'emergency_direction': emergency_direction,
            'emergency_source': emergency_source,
            'emergency_remaining': emergency_remaining,
            'priority_direction': emergency_direction,
            'operating_mode': 'EMERGENCY' if emergency_active else 'NORMAL'
        }

    def manual_override(self):
        with self.lock:
            self.manual_override_flag = True

    def run_simulation(self, stop_event):
        while not stop_event.is_set():
            with self.lock:
                self._refresh_emergency_state()
                self.intersection.update_vehicles()
                self.intersection.update_densities()

                if self.emergency_override['active']:
                    emergency_direction = self.emergency_override['direction']
                    emergency_until = self.emergency_override['expires_at']
                    emergency_phase = self._phase_for_direction(emergency_direction)
                    self.active_phase = emergency_phase

                    # Force a single-direction green during emergency priority.
                    active_dirs = [emergency_direction]
                    self.intersection.set_signal_states(active_dirs)
                    self.intersection.increment_waiting(active_dirs)
                    self.green_time_remaining = max(0, int(math.ceil(emergency_until - time.time())))
                    self.congestion_history.append(sum(self.intersection.directions[dir]['vehicle_count'] for dir in self.intersection.directions))
                    if len(self.congestion_history) > 30:
                        self.congestion_history.pop(0)

                else:
                    total_vehicles = sum(self.intersection.directions[dir]['vehicle_count'] for dir in self.intersection.directions)
                    if self.active_phase == 1:
                        active_dirs = ['north', 'south']
                        waiting_dirs = ['east', 'west']
                    else:
                        active_dirs = ['east', 'west']
                        waiting_dirs = ['north', 'south']
                    # Calculate green time
                    if total_vehicles == 0:
                        green_time = self.min_green
                        density_ratio = 0
                    else:
                        density = sum(self.intersection.directions[dir]['vehicle_count'] for dir in active_dirs)
                        density_ratio = density / total_vehicles
                        green_time = int(self.min_green + density_ratio * self.max_extension)
                    # Log timing
                    self.timing_log.append({
                        'timestamp': time.strftime('%H:%M:%S'),
                        'phase': 'North-South' if self.active_phase == 1 else 'East-West',
                        'green_time': green_time,
                        'total_vehicles': total_vehicles,
                        'density_ratio': round(density_ratio, 2) if total_vehicles > 0 else 0
                    })
                    if len(self.timing_log) > 50:
                        self.timing_log.pop(0)
                    # Starvation prevention
                    for dir in waiting_dirs:
                        self.phase_wait[dir] += 1
                        if self.phase_wait[dir] >= self.starvation_limit:
                            self.active_phase = 2 if self.active_phase == 1 else 1
                            self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
                            break
                    # Manual override
                    if self.manual_override_flag:
                        self.active_phase = 2 if self.active_phase == 1 else 1
                        self.manual_override_flag = False
                        self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
                    # Set signals
                    self.intersection.set_signal_states(active_dirs)
                    self.intersection.increment_waiting(active_dirs)
                    self.green_time_remaining = green_time
                    self.congestion_history.append(total_vehicles)
                    if len(self.congestion_history) > 30:
                        self.congestion_history.pop(0)

            if self.emergency_override['active']:
                while not stop_event.is_set():
                    with self.lock:
                        self._refresh_emergency_state()
                        if not self.emergency_override['active']:
                            self.green_time_remaining = 0
                            self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
                            break
                        emergency_direction = self.emergency_override['direction']
                        self.active_phase = self._phase_for_direction(emergency_direction)
                        self.intersection.set_signal_states([emergency_direction])
                        self.intersection.increment_waiting([emergency_direction])
                        self.green_time_remaining = max(0, int(math.ceil(self.emergency_override['expires_at'] - time.time())))
                    time.sleep(1)
                continue

            # Green phase
            for t in range(green_time, 0, -1):
                if stop_event.is_set():
                    break
                with self.lock:
                    self.green_time_remaining = t
                time.sleep(1)
            # Yellow phase
            with self.lock:
                self.intersection.set_signal_states([], yellow_dirs=active_dirs)
            for t in range(self.yellow_duration, 0, -1):
                if stop_event.is_set():
                    break
                with self.lock:
                    self.green_time_remaining = t
                time.sleep(1)
            # Switch phase
            with self.lock:
                self.active_phase = 2 if self.active_phase == 1 else 1
                self.phase_wait = {'north': 0, 'south': 0, 'east': 0, 'west': 0}




