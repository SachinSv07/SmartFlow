// Modern Traffic Intersection Simulation
const canvas = document.getElementById('intersection');
const ctx = canvas.getContext('2d');
const statsDiv = document.getElementById('stats');
let vehicles = [];
let signalState = { north: 'red', south: 'red', east: 'red', west: 'red' };
let speed = 1;
let vehicleId = 0;

const directions = ['north', 'south', 'east', 'west'];
const colors = { green: '#2ecc40', yellow: '#ffdc00', red: '#ff4136' };
const entryPoints = {
  north: { x: 300, y: 0, dx: 0, dy: 1 },
  south: { x: 300, y: 600, dx: 0, dy: -1 },
  east: { x: 600, y: 300, dx: -1, dy: 0 },
  west: { x: 0, y: 300, dx: 1, dy: 0 }
};

function addVehicle() {
  const dir = directions[Math.floor(Math.random() * 4)];
  vehicles.push({
    id: vehicleId++,
    direction: dir,
    x: entryPoints[dir].x,
    y: entryPoints[dir].y,
    dx: entryPoints[dir].dx,
    dy: entryPoints[dir].dy,
    stopped: false,
    progress: 0
  });
}

function removeVehicle() {
  vehicles.pop();
}

function setSpeed(val) {
  speed = parseFloat(val);
  document.getElementById('speedValue').textContent = val + 'x';
}

document.getElementById('speedRange').addEventListener('input', e => setSpeed(e.target.value));

async function fetchSignalState() {
  try {
    const response = await fetch('http://localhost:5000/signal_state');
    signalState = await response.json();
  } catch (e) {
    // fallback: all red
    signalState = { north: 'red', south: 'red', east: 'red', west: 'red' };
  }
}

function drawIntersection() {
  ctx.clearRect(0, 0, 600, 600);
  // Draw roads
  ctx.fillStyle = '#888';
  ctx.fillRect(250, 0, 100, 600); // vertical
  ctx.fillRect(0, 250, 600, 100); // horizontal
  // Draw crosswalks
  ctx.fillStyle = '#fff';
  for (let i = 0; i < 6; i++) {
    ctx.fillRect(245, 60 + i * 30, 10, 20);
    ctx.fillRect(345, 60 + i * 30, 10, 20);
    ctx.fillRect(60 + i * 30, 245, 20, 10);
    ctx.fillRect(60 + i * 30, 345, 20, 10);
  }
  // Draw traffic lights
  drawSignal(300, 60, signalState.north);
  drawSignal(300, 540, signalState.south);
  drawSignal(540, 300, signalState.east);
  drawSignal(60, 300, signalState.west);
  // Draw direction labels
  ctx.fillStyle = '#2d3a4b';
  ctx.font = 'bold 18px Segoe UI';
  ctx.fillText('N', 310, 40);
  ctx.fillText('S', 310, 590);
  ctx.fillText('E', 570, 320);
  ctx.fillText('W', 20, 320);
}

function drawSignal(x, y, state) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, 18, 0, 2 * Math.PI);
  ctx.fillStyle = colors[state] || '#bbb';
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#222';
  ctx.stroke();
  ctx.restore();
}

function updateVehicles(dt) {
  for (let v of vehicles) {
    // Stop at red/yellow if near intersection
    let stopLine = 250;
    let go = signalState[v.direction] === 'green';
    if (v.direction === 'north' && v.y + 20 >= stopLine && v.y < stopLine + 40) {
      v.stopped = !go;
    } else if (v.direction === 'south' && v.y - 20 <= 350 && v.y > 350 - 40) {
      v.stopped = !go;
    } else if (v.direction === 'east' && v.x - 20 <= 350 && v.x > 350 - 40) {
      v.stopped = !go;
    } else if (v.direction === 'west' && v.x + 20 >= stopLine && v.x < stopLine + 40) {
      v.stopped = !go;
    }
    if (!v.stopped) {
      v.x += v.dx * 120 * dt * speed;
      v.y += v.dy * 120 * dt * speed;
      v.progress += 120 * dt * speed;
    }
  }
  // Remove vehicles that have exited
  vehicles = vehicles.filter(v => v.x >= -40 && v.x <= 640 && v.y >= -40 && v.y <= 640 && v.progress < 700);
}

function drawVehicles() {
  for (let v of vehicles) {
    ctx.save();
    ctx.translate(v.x, v.y);
    if (v.direction === 'north') ctx.rotate(Math.PI / 2);
    if (v.direction === 'south') ctx.rotate(-Math.PI / 2);
    if (v.direction === 'west') ctx.rotate(Math.PI);
    ctx.fillStyle = v.stopped ? '#aaa' : '#0074d9';
    ctx.fillRect(-12, -18, 24, 36);
    ctx.restore();
  }
}

function updateStats() {
  const stopped = vehicles.filter(v => v.stopped).length;
  statsDiv.textContent = `Vehicles: ${vehicles.length} | Stopped: ${stopped}`;
}

let lastTime = null;
function animate(ts) {
  if (!lastTime) lastTime = ts;
  const dt = Math.min((ts - lastTime) / 1000, 0.05);
  lastTime = ts;
  updateVehicles(dt);
  drawIntersection();
  drawVehicles();
  updateStats();
  requestAnimationFrame(animate);
}

// Initial vehicles
for (let i = 0; i < 6; i++) addVehicle();

setInterval(fetchSignalState, 1000);
fetchSignalState();
requestAnimationFrame(animate);
