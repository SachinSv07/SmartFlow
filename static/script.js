// Professional Police Traffic Dashboard JavaScript
let vehicleChart, congestionChart;
let congestionHistory = [];
let updateInterval;
let lastStatusSnapshot = null;
let timingLogInterval;
const seenTimingEntries = new Set();

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    initializeInteractions();
    startDataUpdates();
    fetchDashboardData();
    updateClock();
    setInterval(updateClock, 1000);
});

function initializeInteractions() {
    // Control button handlers
    document.getElementById('start-btn').addEventListener('click', startSystem);
    document.getElementById('stop-btn').addEventListener('click', stopSystem);
    document.getElementById('override-btn').addEventListener('click', manualOverride);
    const ambulanceBtn = document.getElementById('ambulance-btn');
    if (ambulanceBtn) {
        ambulanceBtn.addEventListener('click', triggerAmbulancePriority);
    }

    // Utility controls
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            refreshBtn.classList.add('is-loading');
            await fetchDashboardData();
            refreshBtn.classList.remove('is-loading');
            showToast('Dashboard refreshed');
        });
    }

    const clearLogBtn = document.getElementById('clear-log-btn');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', () => {
            const logContainer = document.getElementById('activity-log');
            logContainer.innerHTML = '';
            addLogEntry('Log cleared by operator');
        });
    }

    const notificationBtn = document.getElementById('notification-btn');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', () => {
            const total = lastStatusSnapshot?.total_vehicles ?? 0;
            showToast(`Current load: ${total} vehicles`);
        });
    }

    // Non-implemented tabs feedback
    document.querySelectorAll('.nav-tab[data-tab="analytics"], .nav-tab[data-tab="reports"]').forEach((tabBtn) => {
        tabBtn.addEventListener('click', () => {
            showToast(`${tabBtn.textContent.trim()} module coming soon`);
        });
    });
}

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
    timingLogInterval = setInterval(refreshTimingLog, 3000);
    refreshTimingLog();
}

// Fetch and update dashboard data
async function fetchDashboardData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error fetching data:', data.error);
            setSystemStatus('Error', false);
            return;
        }

        lastStatusSnapshot = data;
        setSystemStatus('System Active', true);
        updateDashboard(data);
    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        setSystemStatus('Offline', false);
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
    const emergencyActive = !!data.emergency_active;
    const emergencyDirection = (data.priority_direction || data.emergency_direction || '').toLowerCase();
    document.getElementById('active-phase').textContent = data.active_phase || 'N/A';

    // Emergency / ambulance priority state
    const emergencyStatus = document.getElementById('emergency-status');
    const emergencyDetail = document.getElementById('emergency-detail');
    const emergencyCard = document.getElementById('emergency-card');
    const emergencyBanner = document.getElementById('emergency-banner');
    const emergencyBannerSubtitle = document.getElementById('emergency-banner-subtitle');
    const emergencyBannerBadge = document.getElementById('emergency-banner-badge');
    if (emergencyActive) {
        const direction = (emergencyDirection || 'north').toUpperCase();
        const remaining = data.emergency_remaining ?? data.green_time_remaining ?? 0;
        if (emergencyStatus) emergencyStatus.textContent = `${direction} GREEN`;
        if (emergencyDetail) emergencyDetail.textContent = `Ambulance priority active: ${remaining}s remaining`;
        if (emergencyCard) emergencyCard.classList.add('active');
        if (emergencyBanner) emergencyBanner.classList.add('active');
        if (emergencyBannerSubtitle) emergencyBannerSubtitle.textContent = `Green corridor open for ${direction} approach • Auto-clear in ${remaining}s`;
        if (emergencyBannerBadge) emergencyBannerBadge.textContent = `${direction} GREEN`;
        setSystemStatus('EMERGENCY', true);
    } else {
        if (emergencyStatus) emergencyStatus.textContent = 'Normal';
        if (emergencyDetail) emergencyDetail.textContent = 'Geofence monitoring active';
        if (emergencyCard) emergencyCard.classList.remove('active');
        if (emergencyBanner) emergencyBanner.classList.remove('active');
        if (emergencyBannerSubtitle) emergencyBannerSubtitle.textContent = 'Geofence monitoring active';
        if (emergencyBannerBadge) emergencyBannerBadge.textContent = 'Normal';
    }
    
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

    // Hard-sync the visual lights in emergency mode to avoid stale states.
    if (emergencyActive && emergencyDirection) {
        directions.forEach(dir => {
            const forcedState = dir === emergencyDirection ? 'GREEN' : 'RED';
            const indicator = document.getElementById(`indicator-${dir}`);
            if (indicator) {
                indicator.className = 'signal-indicator ' + forcedState.toLowerCase();
            }
            updateSignalLights(dir, forcedState);
        });
    }
    
    // Update charts
    updateCharts(data);
    
    // Update insights
    updateInsights(data);
}

function setSystemStatus(text, isActive) {
    const statusText = document.getElementById('system-status-text');
    const dot = document.querySelector('.status-dot');
    if (!statusText || !dot) return;
    statusText.textContent = text;
    dot.classList.toggle('active', !!isActive);
}

async function triggerAmbulancePriority() {
    const direction = document.getElementById('ambulance-direction')?.value || 'north';
    try {
        const response = await fetch('/api/emergency', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction, duration: 12, source: 'dashboard' })
        });
        const result = await response.json();
        if (!response.ok) {
            showToast(result.error || 'Failed to trigger ambulance priority');
            return;
        }
        showToast(`Ambulance green activated for ${direction.toUpperCase()}`);
        addLogEntry(`Ambulance priority triggered for ${direction.toUpperCase()}`);
        await fetchDashboardData();
    } catch (error) {
        console.error('Failed to trigger ambulance priority:', error);
        showToast('Failed to trigger ambulance priority');
    }
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

async function refreshTimingLog() {
    try {
        const response = await fetch('/api/timing_log');
        const logs = await response.json();
        if (!Array.isArray(logs) || logs.length === 0) {
            return;
        }

        const logContainer = document.getElementById('activity-log');
        logs.forEach((entry) => {
            const key = `${entry.timestamp}|${entry.phase}|${entry.green_time}|${entry.total_vehicles}`;
            if (seenTimingEntries.has(key)) return;

            seenTimingEntries.add(key);
            const densityPercent = Math.round((Number(entry.density_ratio || 0)) * 100);

            const row = document.createElement('div');
            row.className = 'log-entry';
            row.innerHTML = `
                <span class="log-time">${entry.timestamp || '--:--:--'}</span>
                <span class="log-message">${entry.phase || 'Phase'} | Density: ${densityPercent}% | Vehicles: ${entry.total_vehicles ?? 0} | Green: ${entry.green_time ?? 0}s</span>
            `;

            logContainer.insertBefore(row, logContainer.firstChild);
        });

        while (logContainer.children.length > 50) {
            logContainer.removeChild(logContainer.lastChild);
        }
    } catch (error) {
        console.error('Failed to fetch timing log:', error);
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
    const btn = document.getElementById('start-btn');
    setButtonBusy(btn, true);
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        console.log('System started:', data);

        setSystemStatus('System Active', true);
        addLogEntry(data.status === 'already running' ? 'System already running' : 'System started successfully');
        showToast(data.status === 'already running' ? 'System already running' : 'System started');
    } catch (error) {
        console.error('Failed to start system:', error);
        showToast('Failed to start system');
    } finally {
        setButtonBusy(btn, false);
    }
}

async function stopSystem() {
    const btn = document.getElementById('stop-btn');
    setButtonBusy(btn, true);
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        console.log('System stopped:', data);

        setSystemStatus('System Stopped', false);
        addLogEntry('System stopped');
        showToast('System stopped');
    } catch (error) {
        console.error('Failed to stop system:', error);
        showToast('Failed to stop system');
    } finally {
        setButtonBusy(btn, false);
    }
}

async function manualOverride() {
    const confirmed = confirm('Are you sure you want to enable manual override? This will override the AI traffic control.');
    if (!confirmed) return;

    const btn = document.getElementById('override-btn');
    setButtonBusy(btn, true);
    try {
        const response = await fetch('/api/override', { method: 'POST' });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        console.log('Manual override activated:', data);
        addLogEntry('Manual override activated by operator');
        showToast('Manual override activated');
    } catch (error) {
        console.error('Failed to trigger manual override:', error);
        showToast('Manual override failed');
    } finally {
        setButtonBusy(btn, false);
    }
}

function setButtonBusy(buttonEl, isBusy) {
    if (!buttonEl) return;
    buttonEl.disabled = isBusy;
    buttonEl.style.opacity = isBusy ? '0.7' : '1';
    buttonEl.style.pointerEvents = isBusy ? 'none' : 'auto';
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

    while (logContainer.children.length > 25) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

function showToast(message) {
    const old = document.getElementById('dashboard-toast');
    if (old) old.remove();

    const toast = document.createElement('div');
    toast.id = 'dashboard-toast';
    toast.className = 'dashboard-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 250);
    }, 2200);
}
