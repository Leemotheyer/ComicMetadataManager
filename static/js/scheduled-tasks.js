/**
 * Scheduled Tasks Management JavaScript
 * Handles the scheduled tasks configuration and monitoring interface
 */

// Global variables
let currentConfig = {};
let currentStats = {};
let currentTasks = [];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadSystemStatus();
    loadCurrentConfig();
    
    // Set up form submission handler
    document.getElementById('taskConfigForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveConfiguration();
    });
});

/**
 * Load and display system status
 */
function loadSystemStatus() {
    fetch('/api/scheduled-tasks/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displaySystemStatus(data);
                displayTaskStats(data.stats);
                displayScheduledTasks(data.scheduled_tasks);
            } else {
                showNotification('Error', data.error || 'Failed to load system status');
            }
        })
        .catch(error => {
            showNotification('Error', error.message);
        });
}

/**
 * Display system status information
 */
function displaySystemStatus(data) {
    const systemStatusDiv = document.getElementById('systemStatus');
    const startBtn = document.getElementById('startSystemBtn');
    const stopBtn = document.getElementById('stopSystemBtn');
    
    const statusHtml = `
        <div class="mb-3">
            <div class="d-flex align-items-center mb-2">
                <span class="badge ${data.running ? 'bg-success' : 'bg-danger'} me-2">
                    ${data.running ? 'Running' : 'Stopped'}
                </span>
                <strong>System Status</strong>
            </div>
            <p class="text-muted mb-0">
                ${data.running ? 'Scheduled tasks are currently running' : 'Scheduled tasks are stopped'}
            </p>
        </div>
    `;
    
    systemStatusDiv.innerHTML = statusHtml;
    
    // Show/hide control buttons
    if (data.running) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
    } else {
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
    }
    
    // Set up button event handlers
    startBtn.onclick = startSystem;
    stopBtn.onclick = stopSystem;
}

/**
 * Display task statistics
 */
function displayTaskStats(stats) {
    const taskStatsDiv = document.getElementById('taskStats');
    
    const statsHtml = `
        <div class="row text-center">
            <div class="col-6 mb-3">
                <div class="border rounded p-2">
                    <div class="h4 text-primary mb-0">${stats.volumes_updated || 0}</div>
                    <small class="text-muted">Volumes Updated</small>
                </div>
            </div>
            <div class="col-6 mb-3">
                <div class="border rounded p-2">
                    <div class="h4 text-success mb-0">${stats.metadata_processed || 0}</div>
                    <small class="text-muted">Metadata Processed</small>
                </div>
            </div>
            <div class="col-6 mb-3">
                <div class="border rounded p-2">
                    <div class="h4 text-warning mb-0">${stats.cleanup_runs || 0}</div>
                    <small class="text-muted">Cleanup Runs</small>
                </div>
            </div>
            <div class="col-6 mb-3">
                <div class="border rounded p-2">
                    <div class="h4 text-danger mb-0">${stats.errors || 0}</div>
                    <small class="text-muted">Errors</small>
                </div>
            </div>
        </div>
        ${stats.last_run ? `
        <div class="mt-3">
            <small class="text-muted">
                <strong>Last Run:</strong> ${new Date(stats.last_run).toLocaleString()}
            </small>
        </div>
        ` : ''}
        ${stats.next_run ? `
        <div class="mt-1">
            <small class="text-muted">
                <strong>Next Run:</strong> ${new Date(stats.next_run).toLocaleString()}
            </small>
        </div>
        ` : ''}
    `;
    
    taskStatsDiv.innerHTML = statsHtml;
}

/**
 * Display scheduled tasks list
 */
function displayScheduledTasks(tasks) {
    const tasksListDiv = document.getElementById('scheduledTasksList');
    
    if (!tasks || tasks.length === 0) {
        tasksListDiv.innerHTML = '<p class="text-muted text-center">No scheduled tasks found</p>';
        return;
    }
    
    let tasksHtml = '<div class="table-responsive"><table class="table table-sm">';
    tasksHtml += '<thead><tr><th>Task Name</th><th>Next Run</th><th>Interval</th></tr></thead><tbody>';
    
    tasks.forEach(task => {
        const nextRun = task.next_run ? new Date(task.next_run).toLocaleString() : 'Unknown';
        const interval = task.interval_display || (task.interval ? `${task.interval} seconds` : 'Variable');
        
        tasksHtml += `
            <tr>
                <td><code>${task.name}</code></td>
                <td>${nextRun}</td>
                <td>${interval}</td>
            </tr>
        `;
    });
    
    tasksHtml += '</tbody></table></div>';
    tasksListDiv.innerHTML = tasksHtml;
}

/**
 * Load current configuration into form
 */
function loadCurrentConfig() {
    fetch('/api/scheduled-tasks/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentConfig = data.config;
                populateConfigForm(currentConfig);
            } else {
                showNotification('Error', data.error || 'Failed to load configuration');
            }
        })
        .catch(error => {
            showNotification('Error', error.message);
        });
}

/**
 * Populate configuration form with current values
 */
function populateConfigForm(config) {
    document.getElementById('volumeUpdateInterval').value = config.volume_update_interval || 3600;
    document.getElementById('cleanupInterval').value = config.cleanup_interval || 1800;
    document.getElementById('maxMetadataTasks').value = config.max_concurrent_metadata_tasks || 5;
    document.getElementById('tempFileRetention').value = config.temp_file_retention_hours || 24;
    document.getElementById('logRetentionDays').value = config.log_retention_days || 7;
    
    document.getElementById('autoMetadataNewVolumes').checked = config.auto_metadata_for_new_volumes || false;
    document.getElementById('metadataProcessingEnabled').checked = config.metadata_processing_enabled || false;
    document.getElementById('monitoringEnabled').checked = config.monitoring_enabled || false;
}

/**
 * Save configuration changes
 */
function saveConfiguration() {
    const newConfig = {
        volume_update_interval: parseInt(document.getElementById('volumeUpdateInterval').value),
        cleanup_interval: parseInt(document.getElementById('cleanupInterval').value),
        max_concurrent_metadata_tasks: parseInt(document.getElementById('maxMetadataTasks').value),
        temp_file_retention_hours: parseInt(document.getElementById('tempFileRetention').value),
        log_retention_days: parseInt(document.getElementById('logRetentionDays').value),
        auto_metadata_for_new_volumes: document.getElementById('autoMetadataNewVolumes').checked,
        metadata_processing_enabled: document.getElementById('metadataProcessingEnabled').checked,
        monitoring_enabled: document.getElementById('monitoringEnabled').checked
    };
    
    fetch('/api/scheduled-tasks/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(newConfig)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Configuration saved successfully');
            currentConfig = newConfig;
        } else {
            showNotification('Error', data.error || 'Failed to save configuration');
        }
    })
    .catch(error => {
        showNotification('Error', error.message);
    });
}

/**
 * Start the scheduled task system
 */
function startSystem() {
    fetch('/api/scheduled-tasks/start', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Scheduled task system started successfully');
            loadSystemStatus();
        } else {
            showNotification('Error', data.error || 'Failed to start system');
        }
    })
    .catch(error => {
        showNotification('Error', error.message);
    });
}

/**
 * Stop the scheduled task system
 */
function stopSystem() {
    fetch('/api/scheduled-tasks/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Scheduled task system stopped successfully');
            loadSystemStatus();
        } else {
            showNotification('Error', data.error || 'Failed to stop system');
        }
    })
    .catch(error => {
        showNotification('Error', error.message);
    });
}

/**
 * Run a specific task immediately
 */
function runTaskNow(taskName) {
    const taskNames = {
        'volume_update': 'Volume Update',
        'metadata_processing': 'Metadata Processing',
        'cleanup': 'Cleanup',
        'monitoring': 'System Monitoring'
    };
    
    const taskDisplayName = taskNames[taskName] || taskName;
    
    fetch('/api/scheduled-tasks/run-task', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ task_name: taskName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', `${taskDisplayName} task started successfully`);
            // Refresh status after a short delay
            setTimeout(loadSystemStatus, 2000);
        } else {
            showNotification('Error', data.error || `Failed to start ${taskDisplayName} task`);
        }
    })
    .catch(error => {
        showNotification('Error', error.message);
    });
}

/**
 * Refresh status button handler
 */
document.getElementById('refreshStatusBtn').onclick = function() {
    loadSystemStatus();
    showNotification('Info', 'Status refreshed');
};

/**
 * Utility function to show notifications
 */
function showNotification(title, message) {
    const toast = document.getElementById('notificationToast');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

/**
 * Reset configuration to default values
 */
function resetToDefaults() {
    if (confirm('Are you sure you want to reset the configuration to default values? This cannot be undone.')) {
        fetch('/api/scheduled-tasks/config/reset', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Success', 'Configuration reset to defaults successfully');
                // Reload the configuration
                loadCurrentConfig();
                loadSystemStatus();
            } else {
                showNotification('Error', data.error || 'Failed to reset configuration');
            }
        })
        .catch(error => {
            showNotification('Error', error.message);
        });
    }
}

/**
 * Auto-refresh status every 30 seconds
 */
setInterval(loadSystemStatus, 30000);
