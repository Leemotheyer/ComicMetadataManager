/**
 * Comic Metadata Manager - Settings Page JavaScript
 * Handles settings form, connection testing, and configuration management
 */

/**
 * Settings Page Specific Functions
 */
function togglePasswordVisibility(fieldId) {
    const input = document.getElementById(fieldId);
    const icon = document.getElementById(fieldId + 'Icon');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

function testConnection() {
    const formData = new FormData(document.getElementById('settingsForm'));
    const settings = Object.fromEntries(formData.entries());
    
    // Show loading state
    const testButton = document.querySelector('button[onclick="testConnection()"]');
    const originalText = testButton.innerHTML;
    testButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Testing...';
    testButton.disabled = true;
    
    // Hide previous results
    document.getElementById('connectionTestResults').style.display = 'none';
    
    // Use backend connection testing instead of frontend
    fetch('/api/settings/test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayConnectionTestResults(data);
            showNotification('Success', 'Connection test completed');
        } else {
            throw new Error(data.error || 'Connection test failed');
        }
    })
    .catch(error => {
        displayConnectionTestResults({ 
            kapowarr: { success: false, message: `Backend error: ${error.message}` }, 
            comicvine: { success: false, message: `Backend error: ${error.message}` } 
        });
        showNotification('Error', 'Connection test failed');
    })
    .finally(() => {
        // Restore button state
        testButton.innerHTML = originalText;
        testButton.disabled = false;
    });
}

// Connection testing is now handled by the backend

function displayConnectionTestResults(results) {
    const resultsDiv = document.getElementById('connectionTestResults');
    const contentDiv = document.getElementById('connectionTestContent');
    
    let html = '<div class="row">';
    
    // Kapowarr results
    html += '<div class="col-md-6">';
    html += '<h6><i class="fas fa-server me-1"></i>Kapowarr Connection</h6>';
    if (results.kapowarr.success) {
        html += `<div class="alert alert-success"><i class="fas fa-check-circle me-1"></i>${results.kapowarr.message}</div>`;
        if (results.kapowarr.data) {
            // Handle both data structures (result.volumes or volumes)
            const volumeCount = results.kapowarr.data.result?.volumes || results.kapowarr.data.volumes;
            if (volumeCount !== undefined) {
                html += `<small class="text-muted">Volumes: ${volumeCount}</small>`;
            }
        }
    } else {
        html += `<div class="alert alert-danger"><i class="fas fa-times-circle me-1"></i>${results.kapowarr.message}</div>`;
    }
    html += '</div>';
    
    // ComicVine results
    html += '<div class="col-md-6">';
    html += '<h6><i class="fas fa-key me-1"></i>ComicVine Connection</h6>';
    if (results.comicvine.success) {
        html += `<div class="alert alert-success"><i class="fas fa-check-circle me-1"></i>${results.comicvine.message}</div>`;
    } else {
        html += `<div class="alert alert-danger"><i class="fas fa-times-circle me-1"></i>${results.comicvine.message}</div>`;
    }
    html += '</div>';
    
    html += '</div>';
    
    contentDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to their default values? This will clear your API keys and other customizations.')) {
        document.getElementById('kapowarrUrl').value = 'http://192.168.1.205:5656';
        document.getElementById('kapowarrApiKey').value = '';
        document.getElementById('comicvineApiKey').value = '';
        document.getElementById('tempDirectory').value = './temp';
        document.getElementById('maxConcurrentTasks').value = '3';
        document.getElementById('taskTimeout').value = '30';
        document.getElementById('flaskSecretKey').value = 'your-secret-key-here-change-this-in-production';
        
        showNotification('Info', 'Settings reset to defaults');
    }
}

function saveSettings(formData) {
    return fetch('/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Settings saved successfully!');
            
            // Update current configuration display
            updateCurrentConfigurationDisplay(formData);
            
            // Hide connection test results since settings changed
            document.getElementById('connectionTestResults').style.display = 'none';
            
            return true;
        } else {
            throw new Error(data.error || 'Failed to save settings');
        }
    });
}

function updateCurrentConfigurationDisplay(settings) {
    // Update the current configuration display
    if (document.getElementById('currentKapowarrUrl')) {
        document.getElementById('currentKapowarrUrl').textContent = settings.kapowarr_url || 'Not set';
    }
    if (document.getElementById('currentKapowarrKey')) {
        document.getElementById('currentKapowarrKey').textContent = settings.kapowarr_api_key ? '••••••••' : 'Not set';
    }
    if (document.getElementById('currentComicVineKey')) {
        document.getElementById('currentComicVineKey').textContent = settings.comicvine_api_key ? '••••••••' : 'Not set';
    }
    if (document.getElementById('currentTempDir')) {
        document.getElementById('currentTempDir').textContent = settings.temp_directory || 'Not set';
    }
    if (document.getElementById('currentMaxTasks')) {
        document.getElementById('currentMaxTasks').textContent = settings.max_concurrent_tasks || 'Not set';
    }
    if (document.getElementById('currentTaskTimeout')) {
        document.getElementById('currentTaskTimeout').textContent = (settings.task_timeout || 'Not set') + ' minutes';
    }
    if (document.getElementById('currentFlaskKey')) {
        document.getElementById('currentFlaskKey').textContent = settings.flask_secret_key ? '••••••••' : 'Not set';
    }
}

/**
 * Event Listeners Setup
 */
function setupSettingsEventListeners() {
    // Form submission
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const settings = Object.fromEntries(formData.entries());
            
            // Validate required fields
            if (!settings.kapowarr_url || !settings.kapowarr_api_key || !settings.comicvine_api_key) {
                showNotification('Error', 'Please fill in all required fields');
                return;
            }
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
            submitButton.disabled = true;
            
            // Save settings
            saveSettings(settings)
                .then(() => {
                    // Success - form will be updated
                })
                .catch(error => {
                    showNotification('Error', error.message);
                })
                .finally(() => {
                    // Restore button state
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                });
        });
    }
}

/**
 * Page Initialization
 */
function initializeSettingsPage() {
    setupSettingsEventListeners();
    console.log('Settings page initialized');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeSettingsPage);

// Export functions for use in other scripts (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        testConnection,
        resetToDefaults,
        saveSettings,
        togglePasswordVisibility
    };
}
