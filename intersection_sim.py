
# --- Realistic Intersection Simulation with Moving Cars ---

import random
import cv2
import numpy as np
import time
from traffic_logic import IntersectionSignalController

VEHICLE_TYPES = [
    {"type": "car", "length": 30, "width": 15, "color": (255,0,0)},
    {"type": "bus", "length": 50, "width": 18, "color": (0,128,255)},
    {"type": "truck", "length": 40, "width": 18, "color": (0,255,128)},
    {"type": "bike", "length": 18, "width": 8, "color": (200,200,200)}
]

# Vehicle class for animation
class Vehicle:
    _id_counter = 1
    def __init__(self, direction, lane, start_pos, vtype=None):
        self.direction = direction  # 'north', 'south', 'east', 'west'
        self.lane = lane
        self.pos = start_pos  # (x, y)
        if vtype is None:
            vtype = random.choice(VEHICLE_TYPES)
        self.vtype = vtype["type"]
        self.length = vtype["length"]
        self.width = vtype["width"]
        self.color = vtype["color"]
        self.v = random.uniform(6, 10)  # initial speed (pixels/frame)
        self.a = 0  # acceleration
        self.active = True  # Is moving
        self.desired_v = 12  # desired speed (pixels/frame)
        self.T = 1.5  # safe time headway (s)
        self.s0 = 20  # minimum gap (pixels)
        self.max_a = 2.0  # max acceleration (pixels/frame^2)
        self.b = 3.0  # comfortable deceleration (pixels/frame^2)
        self.lane_change_cooldown = 0  # frames to wait before next lane change
        self.id = Vehicle._id_counter
        Vehicle._id_counter += 1

    def can_change_lane(self, my_lane_vehicles, target_lane_vehicles, idx, direction):
        # MOBIL: Check if lane change is safe and beneficial
        # idx: index of self in my_lane_vehicles
        # direction: +1 for right, -1 for left
        if self.lane_change_cooldown > 0:
            return False
        # Find leader and follower in target lane
        my_pos = self.pos[1] if self.direction in ['north', 'south'] else self.pos[0]
        # Find leader in target lane (ahead of self)
        leader = None
        follower = None
        for v in target_lane_vehicles:
            v_pos = v.pos[1] if self.direction in ['north', 'south'] else v.pos[0]
            if (self.direction in ['north', 'west'] and v_pos < my_pos) or (self.direction in ['south', 'east'] and v_pos > my_pos):
                if leader is None or (self.direction in ['north', 'west'] and v_pos > (leader.pos[1] if self.direction in ['north', 'south'] else leader.pos[0])) or (self.direction in ['south', 'east'] and v_pos < (leader.pos[1] if self.direction in ['north', 'south'] else leader.pos[0])):
                    leader = v
            elif (self.direction in ['north', 'west'] and v_pos > my_pos) or (self.direction in ['south', 'east'] and v_pos < my_pos):
                if follower is None or (self.direction in ['north', 'west'] and v_pos < (follower.pos[1] if self.direction in ['north', 'south'] else follower.pos[0])) or (self.direction in ['south', 'east'] and v_pos > (follower.pos[1] if self.direction in ['north', 'south'] else follower.pos[0])):
                    follower = v
        # Safety: follower in target lane must not brake too hard
        safe = True
        if follower:
            s = abs((self.pos[1] if self.direction in ['north', 'south'] else self.pos[0]) - (follower.pos[1] if self.direction in ['north', 'south'] else follower.pos[0])) - self.length
            s = max(s, 0.1)
            s_star = follower.s0 + max(0, follower.v * follower.T + follower.v * (follower.v - self.v) / (2 * np.sqrt(follower.max_a * follower.b)))
            a_follower_new = follower.max_a * (1 - (follower.v / follower.desired_v) ** 4 - (s_star / s) ** 2)
            if a_follower_new < -follower.b:
                safe = False
        # Incentive: own acceleration must improve by threshold
        if safe:
            # Compute current and new acceleration
            leader_current = my_lane_vehicles[idx-1] if idx > 0 else None
            s_current = 1000
            delta_v_current = 0
            if leader_current:
                if self.direction == 'north':
                    s_current = self.pos[1] - leader_current.pos[1] - leader_current.length
                    delta_v_current = self.v - leader_current.v
                elif self.direction == 'south':
                    s_current = leader_current.pos[1] - self.pos[1] - self.length
                    delta_v_current = self.v - leader_current.v
                elif self.direction == 'east':
                    s_current = leader_current.pos[0] - self.pos[0] - self.length
                    delta_v_current = self.v - leader_current.v
                elif self.direction == 'west':
                    s_current = self.pos[0] - leader_current.pos[0] - leader_current.length
                    delta_v_current = self.v - leader_current.v
            s_current = max(s_current, 0.1)
            s_star_current = self.s0 + max(0, self.v * self.T + self.v * delta_v_current / (2 * np.sqrt(self.max_a * self.b)))
            a_current = self.max_a * (1 - (self.v / self.desired_v) ** 4 - (s_star_current / s_current) ** 2)
            # New acceleration in target lane
            s_new = 1000
            delta_v_new = 0
            if leader:
                if self.direction == 'north':
                    s_new = self.pos[1] - leader.pos[1] - leader.length
                    delta_v_new = self.v - leader.v
                elif self.direction == 'south':
                    s_new = leader.pos[1] - self.pos[1] - self.length
                    delta_v_new = self.v - leader.v
                elif self.direction == 'east':
                    s_new = leader.pos[0] - self.pos[0] - self.length
                    delta_v_new = self.v - leader.v
                elif self.direction == 'west':
                    s_new = self.pos[0] - leader.pos[0] - leader.length
                    delta_v_new = self.v - leader.v
            s_new = max(s_new, 0.1)
            s_star_new = self.s0 + max(0, self.v * self.T + self.v * delta_v_new / (2 * np.sqrt(self.max_a * self.b)))
            a_new = self.max_a * (1 - (self.v / self.desired_v) ** 4 - (s_star_new / s_new) ** 2)
            # Incentive threshold (pixels/frame^2)
            threshold = 0.2
            if a_new - a_current > threshold:
                return True
        return False

    def move(self, green_phase, intersection_box, leader=None, conflict_checker=None):
        if not self.active:
            return
        # IDM logic: adjust speed based on leader
        dt = 1  # time step (frame)
        s = 1000  # large gap by default
        delta_v = 0
        if leader is not None:
            # Calculate gap to leader (in movement direction)
            if self.direction == 'north':
                s = self.pos[1] - leader.pos[1] - leader.length
                delta_v = self.v - leader.v
            elif self.direction == 'south':
                s = leader.pos[1] - self.pos[1] - self.length
                delta_v = self.v - leader.v
            elif self.direction == 'east':
                s = leader.pos[0] - self.pos[0] - self.length
                delta_v = self.v - leader.v
            elif self.direction == 'west':
                s = self.pos[0] - leader.pos[0] - leader.length
                delta_v = self.v - leader.v
        s = max(s, 0.1)
        # IDM acceleration
        s_star = self.s0 + max(0, self.v * self.T + self.v * delta_v / (2 * np.sqrt(self.max_a * self.b)))
        self.a = self.max_a * (1 - (self.v / self.desired_v) ** 4 - (s_star / s) ** 2)
        # Only move if green for this direction
        if self.direction in ['north', 'south'] and green_phase != 'NS':
            self.a = -self.b  # brake if not green
        if self.direction in ['east', 'west'] and green_phase != 'EW':
            self.a = -self.b
        # Intersection conflict management: yield if conflict_checker says so
        if conflict_checker is not None:
            approaching = False
            if self.direction == 'north' and self.pos[1] > intersection_box[1] and self.pos[1] - self.v <= intersection_box[1]:
                approaching = True
            elif self.direction == 'south' and self.pos[1] < intersection_box[3] and self.pos[1] + self.v >= intersection_box[3]:
                approaching = True
            elif self.direction == 'east' and self.pos[0] < intersection_box[2] and self.pos[0] + self.v >= intersection_box[2]:
                approaching = True
            elif self.direction == 'west' and self.pos[0] > intersection_box[0] and self.pos[0] - self.v <= intersection_box[0]:
                approaching = True
            if approaching and conflict_checker(self):
                self.a = -self.b  # yield: brake hard
        # Update speed and position
        self.v = max(0, self.v + self.a * dt)
        if self.direction == 'north':
            if green_phase == 'NS' and self.pos[1] > intersection_box[1]:
                if not (conflict_checker and conflict_checker(self) and self.pos[1] - self.v <= intersection_box[1]):
                    self.pos = (self.pos[0], self.pos[1] - self.v)
            elif self.pos[1] <= intersection_box[1]:
                self.active = False
        elif self.direction == 'south':
            if green_phase == 'NS' and self.pos[1] < intersection_box[3]:
                if not (conflict_checker and conflict_checker(self) and self.pos[1] + self.v >= intersection_box[3]):
                    self.pos = (self.pos[0], self.pos[1] + self.v)
            elif self.pos[1] >= intersection_box[3]:
                self.active = False
        elif self.direction == 'east':
            if green_phase == 'EW' and self.pos[0] < intersection_box[2]:
                if not (conflict_checker and conflict_checker(self) and self.pos[0] + self.v >= intersection_box[2]):
                    self.pos = (self.pos[0] + self.v, self.pos[1])
            elif self.pos[0] >= intersection_box[2]:
                self.active = False
        elif self.direction == 'west':
            if green_phase == 'EW' and self.pos[0] > intersection_box[0]:
                if not (conflict_checker and conflict_checker(self) and self.pos[0] - self.v <= intersection_box[0]):
                    self.pos = (self.pos[0] - self.v, self.pos[1])
            elif self.pos[0] <= intersection_box[0]:
                self.active = False

    def draw(self, frame):
        x, y = self.pos
        # Draw schematic white car (rectangle with black outline)
        if self.direction in ['north', 'south']:
            pt1 = (int(x - self.width), int(y - self.length))
            pt2 = (int(x + self.width), int(y + self.length))
        else:
            pt1 = (int(x - self.length), int(y - self.width))
            pt2 = (int(x + self.length), int(y + self.width))
        cv2.rectangle(frame, pt1, pt2, (255,255,255), -1, cv2.LINE_AA)
        cv2.rectangle(frame, pt1, pt2, (0,0,0), 2, cv2.LINE_AA)
        # Draw car ID
        cv2.putText(frame, str(self.id), (int(x)-8, int(y)+6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)

# Generate vehicles for each direction
vehicle_colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]
def spawn_vehicles(direction, lane, count, frame_size):
    vehicles = []
    w, h = frame_size
    for i in range(count):
        vtype = random.choice(VEHICLE_TYPES)
        if direction == 'north':
            x = w//2 - 40 + lane*20
            y = h - 40 - i*50
        elif direction == 'south':
            x = w//2 + 40 - lane*20
            y = 40 + i*50
        elif direction == 'east':
            x = 40 + i*50
            y = h//2 + 40 - lane*20
        elif direction == 'west':
            x = w - 40 - i*50
            y = h//2 - 40 + lane*20
        vehicles.append(Vehicle(direction, lane, (x, y), vtype))
    return vehicles

def draw_intersection(frame):
    h, w = frame.shape[:2]
    # Schematic dark background
    frame[:] = (10, 10, 10)
    # Draw main roads (wide dark gray)
    cv2.rectangle(frame, (w//2-60, 0), (w//2+60, h), (40,40,40), -1, cv2.LINE_AA)
    cv2.rectangle(frame, (0, h//2-60), (w, h//2+60), (40,40,40), -1, cv2.LINE_AA)
    # Draw intersection box (slightly lighter)
    cv2.rectangle(frame, (w//2-60, h//2-60), (w//2+60, h//2+60), (60,60,60), -1, cv2.LINE_AA)
    # Lane lines: yellow center, white edges, dashed white for lanes
    for i in range(-2,3):
        x = w//2-60+i*20
        y = h//2-60+i*20
        # Vertical
        if i == 0:
            cv2.line(frame, (x, 0), (x, h), (0,220,255), 3, cv2.LINE_AA)  # yellow center
        else:
            for y0 in range(0, h, 40):
                cv2.line(frame, (x, y0), (x, y0+20), (255,255,255), 2, cv2.LINE_AA)
        # Horizontal
        if i == 0:
            cv2.line(frame, (0, y), (w, y), (0,220,255), 3, cv2.LINE_AA)
        else:
            for x0 in range(0, w, 40):
                cv2.line(frame, (x0, y), (x0+20, y), (255,255,255), 2, cv2.LINE_AA)
    # Edge lines (solid white)
    cv2.line(frame, (w//2-60-20, 0), (w//2-60-20, h), (255,255,255), 3, cv2.LINE_AA)
    cv2.line(frame, (w//2+60+20, 0), (w//2+60+20, h), (255,255,255), 3, cv2.LINE_AA)
    cv2.line(frame, (0, h//2-60-20), (w, h//2-60-20), (255,255,255), 3, cv2.LINE_AA)
    cv2.line(frame, (0, h//2+60+20), (w, h//2+60+20), (255,255,255), 3, cv2.LINE_AA)
    # Draw slot markings (stop/tail slots)
    slot_color = (180,180,180)
    for i in range(3):
        # North
        cv2.rectangle(frame, (w//2-40+i*20, h//2-120), (w//2-20+i*20, h//2-60), slot_color, 1, cv2.LINE_AA)
        # South
        cv2.rectangle(frame, (w//2-40+i*20, h//2+60), (w//2-20+i*20, h//2+120), slot_color, 1, cv2.LINE_AA)
        # East
        cv2.rectangle(frame, (w//2+60, h//2-40+i*20), (w//2+120, h//2-20+i*20), slot_color, 1, cv2.LINE_AA)
        # West
        cv2.rectangle(frame, (w//2-120, h//2-40+i*20), (w//2-60, h//2-20+i*20), slot_color, 1, cv2.LINE_AA)
    # Draw arrows for direction
    arrow_color = (255,255,255)
    # North
    cv2.arrowedLine(frame, (w//2, h//2-100), (w//2, h//2-70), arrow_color, 2, tipLength=0.3)
    # South
    cv2.arrowedLine(frame, (w//2, h//2+100), (w//2, h//2+70), arrow_color, 2, tipLength=0.3)
    # East
    cv2.arrowedLine(frame, (w//2+100, h//2), (w//2+70, h//2), arrow_color, 2, tipLength=0.3)
    # West
    cv2.arrowedLine(frame, (w//2-100, h//2), (w//2-70, h//2), arrow_color, 2, tipLength=0.3)
    return frame
    for i in range(0, 120, 20):
        cv2.rectangle(frame, (w//2-60+i, h//2-80), (w//2-50+i, h//2-60), crosswalk_color, -1, cv2.LINE_AA)
        cv2.rectangle(frame, (w//2-60+i, h//2+60), (w//2-50+i, h//2+80), crosswalk_color, -1, cv2.LINE_AA)
        cv2.rectangle(frame, (w//2-80, h//2-60+i), (w//2-60, h//2-50+i), crosswalk_color, -1, cv2.LINE_AA)
        cv2.rectangle(frame, (w//2+60, h//2-60+i), (w//2+80, h//2-50+i), crosswalk_color, -1, cv2.LINE_AA)
    # Lane arrows
    # North arrow
    pts = np.array([[w//2, 40],[w//2-10,60],[w//2+10,60]], np.int32)
    cv2.fillPoly(frame, [pts], arrow_color, cv2.LINE_AA)
    cv2.line(frame, (w//2, 60), (w//2, h//2-80), arrow_color, 2, cv2.LINE_AA)
    # South arrow
    pts = np.array([[w//2, h-40],[w//2-10,h-60],[w//2+10,h-60]], np.int32)
    cv2.fillPoly(frame, [pts], arrow_color, cv2.LINE_AA)
    cv2.line(frame, (w//2, h-60), (w//2, h//2+80), arrow_color, 2, cv2.LINE_AA)
    # East arrow
    pts = np.array([[w-40, h//2],[w-60, h//2-10],[w-60, h//2+10]], np.int32)
    cv2.fillPoly(frame, [pts], arrow_color, cv2.LINE_AA)
    cv2.line(frame, (w-60, h//2), (w//2+80, h//2), arrow_color, 2, cv2.LINE_AA)
    # West arrow
    pts = np.array([[40, h//2],[60, h//2-10],[60, h//2+10]], np.int32)
    cv2.fillPoly(frame, [pts], arrow_color, cv2.LINE_AA)
    cv2.line(frame, (60, h//2), (w//2-80, h//2), arrow_color, 2, cv2.LINE_AA)
    return frame

def run_realistic_intersection_sim():
    controller = IntersectionSignalController()
    width, height = 800, 800
    intersection_box = (width//2-60, height//2-60, width//2+60, height//2+60)
    timers = {'green': 0, 'yellow': 0, 'all_red': 0, 'red': 0}
    signal_state = None
    phase = None
    # Vehicle queues for each direction
    vehicle_queues = {d: [] for d in ['north','south','east','west']}
    lanes = 2

    # --- Interactive GUI controls ---
    cv2.namedWindow('Realistic Intersection Simulation')
    # Sliders for vehicle spawn rate and green time
    cv2.createTrackbar('SpawnRate', 'Realistic Intersection Simulation', 5, 20, lambda x: None)
    cv2.createTrackbar('GreenTime', 'Realistic Intersection Simulation', 20, 60, lambda x: None)
    paused = [False]
    def toggle_pause():
        paused[0] = not paused[0]
    def reset_sim():
        nonlocal timers, vehicle_queues
        timers = {'green': 0, 'yellow': 0, 'all_red': 0, 'red': 0}
        vehicle_queues = {d: [] for d in ['north','south','east','west']}
    # Conflict management: track vehicles in intersection
    intersection_occupants = []  # list of (vehicle, direction)
    def conflict_checker(vehicle):
        # If another vehicle is in the intersection and has conflicting movement, yield
        # For simplicity, conflict if another vehicle is in intersection and not same direction
        for occ, occ_dir in intersection_occupants:
            if occ.active and occ != vehicle and occ_dir != vehicle.direction:
                return True
        return False
    # Try to load a background image for the intersection
    import os
    bg_path = os.path.join(os.path.dirname(__file__), 'assets', 'road_bg.png')
    bg_img = None
    if os.path.exists(bg_path):
        bg_img = cv2.imread(bg_path)
        if bg_img is not None:
            bg_img = cv2.resize(bg_img, (width, height))

    while True:
        # Handle pause
        if paused[0]:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame = draw_intersection(frame)
            cv2.putText(frame, "PAUSED", (width//2-100, height//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 4)
            cv2.imshow('Realistic Intersection Simulation', frame)
            key = cv2.waitKey(100) & 0xFF
            if key == ord('p'):
                toggle_pause()
            elif key == ord('r'):
                reset_sim()
            elif key == ord('q'):
                break
            continue
        # On new cycle or phase end, spawn new vehicles and decide phase
        if timers['green'] == 0 and timers['yellow'] == 0 and timers['all_red'] == 0:
            # Get spawn rate and green time from sliders
            spawn_rate = cv2.getTrackbarPos('SpawnRate', 'Realistic Intersection Simulation')
            green_time_slider = cv2.getTrackbarPos('GreenTime', 'Realistic Intersection Simulation')
            # Use spawn_rate for all directions (simulate density)
            densities = {d: spawn_rate for d in vehicle_queues}
            for d in vehicle_queues:
                vehicle_queues[d] = []
                for lane in range(lanes):
                    vehicle_queues[d] += spawn_vehicles(d, lane, densities[d]//lanes, (width, height))
            # Override green time in controller
            signal_state = controller.decide_phase(
                densities['north'], densities['south'], densities['east'], densities['west']
            )
            signal_state['green_time'] = green_time_slider
            timers['green'] = signal_state['green_time']
            timers['yellow'] = signal_state['yellow_time']
            timers['all_red'] = signal_state.get('all_red_time', 0)
            timers['red'] = signal_state['red_time_other_phase']
            phase = signal_state['active_phase']
        # Draw intersection
        if bg_img is not None:
            frame = bg_img.copy()
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame = draw_intersection(frame)
        # --- MOBIL lane-changing logic ---
        for d in vehicle_queues:
            for lane in range(lanes):
                lane_vehicles = [v for v in vehicle_queues[d] if v.lane == lane and v.active]
                lane_vehicles.sort(key=lambda v: v.pos[1] if d in ['north','south'] else v.pos[0], reverse=(d in ['north','west']))
                for idx, v in enumerate(lane_vehicles):
                    # Try to change lane left (-1) or right (+1)
                    for dir_offset in [-1, 1]:
                        target_lane = v.lane + dir_offset
                        if 0 <= target_lane < lanes:
                            target_lane_vehicles = [tv for tv in vehicle_queues[d] if tv.lane == target_lane and tv.active]
                            if v.can_change_lane(lane_vehicles, target_lane_vehicles, idx, dir_offset):
                                v.lane = target_lane
                                v.lane_change_cooldown = 10  # Prevent rapid switching
                                break
        # Decrement lane change cooldowns
        for d in vehicle_queues:
            for v in vehicle_queues[d]:
                if v.lane_change_cooldown > 0:
                    v.lane_change_cooldown -= 1
        # Draw vehicles and move them if green
        intersection_occupants.clear()
        for d in vehicle_queues:
            for v in vehicle_queues[d]:
                # Check if vehicle is in intersection box
                in_intersection = False
                if v.direction == 'north' and v.pos[1] <= intersection_box[1]:
                    in_intersection = True
                elif v.direction == 'south' and v.pos[1] >= intersection_box[3]:
                    in_intersection = True
                elif v.direction == 'east' and v.pos[0] >= intersection_box[2]:
                    in_intersection = True
                elif v.direction == 'west' and v.pos[0] <= intersection_box[0]:
                    in_intersection = True
                if in_intersection and v.active:
                    intersection_occupants.append((v, v.direction))
                v.move(phase if timers['green']>0 else None, intersection_box, leader=None, conflict_checker=conflict_checker)
                v.draw(frame)
        # Draw traffic lights
        font = cv2.FONT_HERSHEY_SIMPLEX
        # Determine light color for each direction and left-turn
        ns_straight_green = (phase == 'NS' and timers['green'] > 0)
        ns_left_green = (phase == 'NS_L' and timers['green'] > 0)
        ew_straight_green = (phase == 'EW' and timers['green'] > 0)
        ew_left_green = (phase == 'EW_L' and timers['green'] > 0)
        yellow = (timers['yellow'] > 0)
        all_red = (timers['all_red'] > 0)
        # NS lights
        ns_color = (0,255,0) if ns_straight_green else (255,0,255) if ns_left_green else (0,255,255) if yellow and phase.startswith('NS') else (0,0,255) if not all_red else (255,255,255)
        cv2.circle(frame, (width//2, 60), 30, ns_color, -1)
        cv2.circle(frame, (width//2, height-60), 30, ns_color, -1)
        # EW lights
        ew_color = (0,255,0) if ew_straight_green else (255,0,255) if ew_left_green else (0,255,255) if yellow and phase.startswith('EW') else (0,0,255) if not all_red else (255,255,255)
        cv2.circle(frame, (60, height//2), 30, ew_color, -1)
        cv2.circle(frame, (width-60, height//2), 30, ew_color, -1)
        # Overlay info
        cv2.putText(frame, f"Phase: {phase}", (20, 40), font, 1, (255,255,255), 2)
        cv2.putText(frame, f"Green: {timers['green']}s", (20, 80), font, 1, (0,255,0), 2)
        cv2.putText(frame, f"Yellow: {timers['yellow']}s", (20, 120), font, 1, (0,255,255), 2)
        cv2.putText(frame, f"All-Red: {timers['all_red']}s", (20, 160), font, 1, (255,255,255), 2)
        cv2.putText(frame, f"Red: {timers['red']}s", (20, 200), font, 1, (0,0,255), 2)
        cv2.imshow('Realistic Intersection Simulation', frame)
        key = cv2.waitKey(200) & 0xFF
        if key == ord('p'):
            toggle_pause()
        elif key == ord('r'):
            reset_sim()
        elif key == ord('q'):
            break
        # Update timers
        if timers['green'] > 0:
            timers['green'] -= 1
        elif timers['yellow'] > 0:
            timers['yellow'] -= 1
        elif timers['all_red'] > 0:
            timers['all_red'] -= 1
        else:
            timers['red'] -= 1 if timers['red'] > 0 else 0
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_realistic_intersection_sim()
