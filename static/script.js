// Professional Police Traffic Dashboard JavaScript
let vehicleChart, congestionChart;
let congestionHistory = [];
let updateInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    startDataUpdates();
    updateClock();
    setInterval(updateClock, 1000);
    
    // Control button handlers
    document.getElementById('start-btn').addEventListener('click', startSystem);
    document.getElementById('stop-btn').addEventListener('click', stopSystem);
    document.getElementById('override-btn').addEventListener('click', manualOverride);
});

// Update clock
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    document.getElementById('current-time').textContent = timeString;
}

// Initialize charts
function initializeCharts() {
    // Vehicle Distribution Chart
    const vehicleCtx = document.getElementById('vehicleChart').getContext('2d');
    vehicleChart = new Chart(vehicleCtx, {
        type: 'bar',
        data: {
            labels: ['North', 'South', 'East', 'West'],
            datasets: [{
                label: 'Vehicle Count',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderColor: [
                    'rgb(59, 130, 246)',
                    'rgb(16, 185, 129)',
                    'rgb(245, 158, 11)',
                    'rgb(239, 68, 68)'
                ],
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });

    // Congestion Trends Chart
    const congestionCtx = document.getElementById('congestionChart').getContext('2d');
    congestionChart = new Chart(congestionCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Vehicles',
                data: [],
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

// Start data updates
function startDataUpdates() {
    updateInterval = setInterval(fetchDashboardData, 1000);
}

// Fetch and update dashboard data
async function fetchDashboardData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error fetching data:', data.error);
            return;
        }
        
        updateDashboard(data);
    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
    }
}

// Update all dashboard elements
function updateDashboard(data) {
    // Update total vehicles
    const totalVehicles = data.total_vehicles || 0;
    document.getElementById('total-vehicles').textContent = totalVehicles;
    
    // Update congestion level
    const congestionLevel = data.congestion_level || 'LOW';
    document.getElementById('congestion-level').textContent = congestionLevel;
    document.getElementById('congestion-level').className = 'stat-value ' + congestionLevel.toLowerCase();
    
    // Update congestion trend
    const trendTexts = {
        'LOW': 'Normal flow',
        'MEDIUM': 'Moderate traffic',
        'HIGH': 'Heavy congestion'
    };
    document.getElementById('congestion-trend').textContent = trendTexts[congestionLevel] || 'Normal flow';
    
    // Update active phase
    document.getElementById('active-phase').textContent = data.active_phase || 'N/A';
    
    // Update countdown timer
    const timeRemaining = data.green_time_remaining || 0;
    document.getElementById('countdown-value').textContent = timeRemaining;
    document.getElementById('phase-timer').textContent = timeRemaining + 's remaining';
    
    // Update direction cards and signals
    const directions = ['north', 'south', 'east', 'west'];
    directions.forEach(dir => {
        const dirData = data[dir];
        if (dirData) {
            // Update vehicle count
            document.getElementById(`vehicles-${dir}`).textContent = dirData.vehicle_count || 0;
            
            // Update density
            const density = dirData.density_percentage || 0;
            document.getElementById(`density-${dir}`).textContent = density + '%';
            document.getElementById(`density-fill-${dir}`).style.width = density + '%';
            
            // Update wait time
            document.getElementById(`wait-${dir}`).textContent = dirData.waiting_time + 's';
            
            // Update signal indicator
            const indicator = document.getElementById(`indicator-${dir}`);
            const signal = dirData.signal_state || 'RED';
            indicator.className = 'signal-indicator ' + signal.toLowerCase();
            
            // Update intersection signal lights
            updateSignalLights(dir, signal);
        }
    });
    
    // Update charts
    updateCharts(data);
    
    // Update activity log
    updateActivityLog(data);
    
    // Update insights
    updateInsights(data);
}

// Update signal lights on intersection visual
function updateSignalLights(direction, state) {
    const signalElement = document.getElementById(`signal-${direction}`);
    if (!signalElement) return;
    
    const lights = signalElement.querySelectorAll('.signal-light');
    lights.forEach(light => light.classList.remove('active'));
    
    if (state === 'RED') {
        lights[0].classList.add('active');
    } else if (state === 'YELLOW') {
        lights[1].classList.add('active');
    } else if (state === 'GREEN') {
        lights[2].classList.add('active');
    }
}

// Update charts
function updateCharts(data) {
    // Update vehicle distribution bar chart
    const vehicleCounts = [
        data.north?.vehicle_count || 0,
        data.south?.vehicle_count || 0,
        data.east?.vehicle_count || 0,
        data.west?.vehicle_count || 0
    ];
    vehicleChart.data.datasets[0].data = vehicleCounts;
    vehicleChart.update('none');
    
    // Update congestion line chart
    const now = new Date();
    const timeLabel = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    congestionHistory.push({
        time: timeLabel,
        total: data.total_vehicles || 0
    });
    
    // Keep only last 20 data points
    if (congestionHistory.length > 20) {
        congestionHistory.shift();
    }
    
    congestionChart.data.labels = congestionHistory.map(d => d.time);
    congestionChart.data.datasets[0].data = congestionHistory.map(d => d.total);
    congestionChart.update('none');
}

// Update activity log
let lastLoggedPhase = '';
function updateActivityLog(data) {
    const logContainer = document.getElementById('activity-log');
    const activePhase = data.active_phase;
    
    // Only log when phase changes
    if (activePhase && activePhase !== lastLoggedPhase) {
        lastLoggedPhase = activePhase;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `
            <span class="log-time">${timeString}</span>
            <span class="log-message">Signal changed to ${activePhase}</span>
        `;
        
        logContainer.insertBefore(entry, logContainer.firstChild);
        
        // Keep only last 10 entries
        while (logContainer.children.length > 10) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }
}

// Update AI insights
function updateInsights(data) {
    const insightsContainer = document.getElementById('insights-container');
    const insights = [];
    
    // Generate dynamic insights based on data
    const totalVehicles = data.total_vehicles || 0;
    const congestionLevel = data.congestion_level || 'LOW';
    
    // Traffic flow insight
    if (congestionLevel === 'HIGH') {
        insights.push({
            icon: '⚠️',
            title: 'High Traffic Alert',
            text: `Heavy congestion detected with ${totalVehicles} total vehicles. Consider extending green light duration.`
        });
    } else {
        insights.push({
            icon: '💡',
            title: 'Optimal Flow',
            text: 'Traffic flow is optimal. AI system maintaining efficient signal timing.'
        });
    }
    
    // Direction analysis
    const directions = ['north', 'south', 'east', 'west'];
    let maxDir = 'north';
    let maxCount = 0;
    
    directions.forEach(dir => {
        const count = data[dir]?.vehicle_count || 0;
        if (count > maxCount) {
            maxCount = count;
            maxDir = dir;
        }
    });
    
    if (maxCount > 0) {
        insights.push({
            icon: '📊',
            title: 'Traffic Analysis',
            text: `Highest vehicle density on ${maxDir.toUpperCase()} direction with ${maxCount} vehicles.`
        });
    }
    
    // Wait time alert
    directions.forEach(dir => {
        const waitTime = data[dir]?.waiting_time || 0;
        if (waitTime > 60) {
            insights.push({
                icon: '⏱️',
                title: 'Wait Time Alert',
                text: `${dir.toUpperCase()} direction waiting for ${waitTime}s. Priority may be needed.`
            });
        }
    });
    
    // Keep only first 3 insights
    const displayInsights = insights.slice(0, 3);
    
    // Update HTML
    insightsContainer.innerHTML = displayInsights.map(insight => `
        <div class="insight-card">
            <div class="insight-icon">${insight.icon}</div>
            <div class="insight-content">
                <div class="insight-title">${insight.title}</div>
                <div class="insight-text">${insight.text}</div>
            </div>
        </div>
    `).join('');
}

// Control functions
async function startSystem() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        console.log('System started:', data);
        
        document.getElementById('system-status-text').textContent = 'System Active';
        
        addLogEntry('System started successfully');
    } catch (error) {
        console.error('Failed to start system:', error);
    }
}

async function stopSystem() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        console.log('System stopped:', data);
        
        document.getElementById('system-status-text').textContent = 'System Stopped';
        
        addLogEntry('System stopped');
    } catch (error) {
        console.error('Failed to stop system:', error);
    }
}

async function manualOverride() {
    const confirmed = confirm('Are you sure you want to enable manual override? This will override the AI traffic control.');
    if (confirmed) {
        console.log('Manual override activated');
        addLogEntry('Manual override activated');
    }
}

// Add log entry helper
function addLogEntry(message) {
    const logContainer = document.getElementById('activity-log');
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="log-time">${timeString}</span>
        <span class="log-message">${message}</span>
    `;
    
    logContainer.insertBefore(entry, logContainer.firstChild);
}
