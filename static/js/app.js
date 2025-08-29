/**
 * Comic Metadata Manager - Main Application JavaScript
 * Centralized JavaScript functionality for all pages
 */

// Global variables
let currentVolumes = [];
let filteredVolumes = [];
let selectedVolumes = new Set(); // Track selected volume IDs

/**
 * Toast Notification System
 */
function showNotification(title, message, type = 'info') {
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    if (toastTitle && toastBody) {
        toastTitle.textContent = title;
        toastBody.textContent = message;
        
        // Apply appropriate styling based on notification type
        const toastElement = document.getElementById('notificationToast');
        if (toastElement) {
            toastElement.className = 'toast'; // Reset classes
            
            if (type === 'success') {
                toastElement.classList.add('success-toast');
            } else if (type === 'error') {
                toastElement.classList.add('error-toast');
            } else {
                toastElement.classList.add('info-toast');
            }
            
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
        }
    }
}

/**
 * Status Update System
 */
function updateStatus(message, type = 'info') {
    const statusInfo = document.getElementById('statusInfo');
    if (statusInfo) {
        const statusClass = type === 'error' ? 'text-danger' : 
                           type === 'success' ? 'text-success' : 'text-muted';
        statusInfo.innerHTML = `<p class="${statusClass} mb-0">${message}</p>`;
        
        // Also update the page title to show progress
        if (type === 'info' && (message.includes('Searching') || message.includes('Loading'))) {
            document.title = `🔄 ${message} - Comic Metadata Manager`;
        } else if (type === 'success') {
            document.title = `✅ Comic Metadata Manager`;
        } else if (type === 'error') {
            document.title = `❌ Comic Metadata Manager`;
        }
    }
}

/**
 * Loading State Management
 */
function showLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const volumesContainer = document.getElementById('volumesContainer');
    
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    
    if (volumesContainer) {
        volumesContainer.innerHTML = '';
    }
}

function hideLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
}

/**
 * API Key Management
 */
function getApiKey() {
    // This will be replaced by the server-side template
    return window.KAPOWARR_API_KEY || '';
}

function getKapowarrUrl() {
    // Get Kapowarr URL from settings or use default
    return window.KAPOWARR_URL || 'http://192.168.1.205:5656';
}

/**
 * Multi-Select Management Functions
 */
function toggleVolumeSelection(volumeId) {
    if (selectedVolumes.has(volumeId)) {
        selectedVolumes.delete(volumeId);
    } else {
        selectedVolumes.add(volumeId);
    }
    updateSelectionUI();
}

function selectAllVolumes() {
    filteredVolumes.forEach(volume => {
        selectedVolumes.add(volume.id);
    });
    updateSelectionUI();
}

function deselectAllVolumes() {
    selectedVolumes.clear();
    updateSelectionUI();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox.checked) {
        selectAllVolumes();
    } else {
        deselectAllVolumes();
    }
}

function updateSelectionUI() {
    const selectedCount = document.getElementById('selectedCount');
    const batchOperationsPanel = document.getElementById('batchOperationsPanel');
    const selectAllContainer = document.getElementById('selectAllContainer');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const batchMetadataBtn = document.getElementById('batchMetadataBtn');
    
    // Update selected count
    if (selectedCount) {
        selectedCount.textContent = `${selectedVolumes.size} selected`;
    }
    
    // Show/hide batch operations panel
    if (batchOperationsPanel) {
        batchOperationsPanel.style.display = selectedVolumes.size > 0 ? 'block' : 'none';
    }
    
    // Show/hide select all container
    if (selectAllContainer) {
        selectAllContainer.style.display = filteredVolumes.length > 0 ? 'block' : 'none';
    }
    
    // Update select all checkbox state
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedVolumes.size === filteredVolumes.length && filteredVolumes.length > 0;
        selectAllCheckbox.indeterminate = selectedVolumes.size > 0 && selectedVolumes.size < filteredVolumes.length;
    }
    
    // Enable/disable batch operation buttons
    if (batchMetadataBtn) {
        batchMetadataBtn.disabled = selectedVolumes.size === 0;
    }
    
    // Update individual volume checkboxes
    filteredVolumes.forEach(volume => {
        const checkbox = document.getElementById(`volume-checkbox-${volume.id}`);
        if (checkbox) {
            // Only update if the checkbox state doesn't match the selection state
            const shouldBeChecked = selectedVolumes.has(volume.id);
            if (checkbox.checked !== shouldBeChecked) {
                checkbox.checked = shouldBeChecked;
            }
        }
    });
    
    // Add visual feedback to selected volume cards
    filteredVolumes.forEach(volume => {
        const card = document.querySelector(`[data-volume-id="${volume.id}"]`);
        if (card) {
            if (selectedVolumes.has(volume.id)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        }
    });
}

/**
 * Batch Operations Functions
 */
function batchGetMetadata() {
    if (selectedVolumes.size === 0) {
        showNotification('Warning', 'No volumes selected');
        return;
    }
    
    const volumeIds = Array.from(selectedVolumes);
    const confirmMessage = `Are you sure you want to get metadata for ${selectedVolumes.size} volume(s)? This may take some time.`;
    
    if (confirm(confirmMessage)) {
        updateStatus(`Starting batch metadata processing for ${selectedVolumes.size} volumes...`, 'info');
        
        // Use the batch API endpoint
        fetch('/api/volumes/batch/metadata', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                volume_ids: volumeIds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateStatus(`Batch processing started. Task ID: ${data.task_id}`, 'info');
                showNotification('Batch Started', data.message);
                
                // Poll for task completion
                pollBatchTaskStatus(data.task_id);
            } else {
                updateStatus(`Error: ${data.error}`, 'error');
                showNotification('Error', data.error);
            }
        })
        .catch(error => {
            updateStatus(`Error: ${error.message}`, 'error');
            showNotification('Error', error.message);
        });
    }
}

function pollBatchTaskStatus(taskId) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    updateStatus(data.message, 'success');
                    showNotification('Batch Complete', data.message);
                    
                    // Show detailed results if available
                    if (data.result && Array.isArray(data.result)) {
                        const successful = data.result.filter(r => r.success).length;
                        const failed = data.result.filter(r => !r.success).length;
                        console.log(`Batch results: ${successful} successful, ${failed} failed`);
                    }
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    updateStatus(`Error: ${data.error}`, 'error');
                    showNotification('Error', data.error);
                }
                // If status is 'running', continue polling
            })
            .catch(error => {
                clearInterval(pollInterval);
                updateStatus(`Error polling task status: ${error.message}`, 'error');
                showNotification('Error', `Error polling task status: ${error.message}`);
            });
    }, 2000); // Poll every 2 seconds
}

function batchViewDetails() {
    if (selectedVolumes.size === 0) {
        showNotification('Warning', 'No volumes selected');
        return;
    }
    
    if (selectedVolumes.size === 1) {
        // Single volume - navigate directly
        const volumeId = Array.from(selectedVolumes)[0];
        window.location.href = `/volume/${volumeId}`;
    } else {
        // Multiple volumes - open in new tabs
        selectedVolumes.forEach(volumeId => {
            window.open(`/volume/${volumeId}`, '_blank');
        });
        showNotification('Info', `Opened ${selectedVolumes.size} volume details in new tabs`);
    }
}

function batchGenerateXML() {
    if (selectedVolumes.size === 0) {
        showNotification('Warning', 'No volumes selected');
        return;
    }
    
    const volumeIds = Array.from(selectedVolumes);
    const confirmMessage = `Are you sure you want to generate XML for ${selectedVolumes.size} volume(s)? This will process metadata first if needed.`;
    
    if (confirm(confirmMessage)) {
        updateStatus(`Starting batch XML generation for ${selectedVolumes.size} volumes...`, 'info');
        
        // Process volumes one by one to avoid overwhelming the server
        let processed = 0;
        let errors = 0;
        
        function processNextVolume() {
            if (volumeIds.length === 0) {
                updateStatus(`Batch XML generation completed. ${processed} successful, ${errors} errors.`, 'success');
                showNotification('Batch Complete', `Generated XML for ${processed} volumes successfully, ${errors} errors.`);
                return;
            }
            
            const volumeId = volumeIds.shift();
            updateStatus(`Generating XML for volume ${volumeId}... (${processed + errors + 1}/${processed + errors + volumeIds.length + 1})`, 'info');
            
            fetch(`/api/volume/${volumeId}/xml`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    processed++;
                } else {
                    errors++;
                    console.error(`Error generating XML for volume ${volumeId}:`, data.error);
                }
                
                // Process next volume after a short delay
                setTimeout(processNextVolume, 1000);
            })
            .catch(error => {
                errors++;
                console.error(`Error generating XML for volume ${volumeId}:`, error);
                setTimeout(processNextVolume, 1000);
            });
        }
        
        processNextVolume();
    }
}

/**
 * Volume Management Functions
 */
function loadVolumes() {
    // Check if app is configured before attempting to load volumes
    if (!window.IS_CONFIGURED) {
        updateStatus('Please configure API keys in Settings first', 'error');
        showNotification('Configuration Required', 'Please configure your API keys in the Settings page before loading volumes.');
        return;
    }
    
    // Additional check for placeholder values
    const apiKey = window.KAPOWARR_API_KEY || '';
    const baseUrl = window.KAPOWARR_URL || '';
    
    if (apiKey === 'your-kapowarr-api-key-here' || apiKey === '' || 
        baseUrl === 'http://your-kapowarr-server:port' || baseUrl === '') {
        updateStatus('Please configure API keys in Settings first', 'error');
        showNotification('Configuration Required', 'Please configure your API keys in the Settings page before loading volumes.');
        return;
    }
    
    showLoading();
    updateStatus('Loading volumes from database...', 'info');

    // Load volumes from database (fast)
    fetch('/api/volumes')
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                currentVolumes = data.volumes;
                displayVolumes(data.volumes);
                updateStatus(`Loaded ${data.volumes.length} volumes`, 'success');
                showNotification('Success', `Loaded ${data.volumes.length} volumes`);
            } else {
                updateStatus(`Error: ${data.error}`, 'error');
                showNotification('Error', data.error);
            }
        })
        .catch(error => {
            hideLoading();
            updateStatus(`Error: ${error.message}`, 'error');
            showNotification('Error', error.message);
        });
}

function refreshAndLoadVolumes() {
    // Check if app is configured before attempting to load volumes
    if (!window.IS_CONFIGURED) {
        updateStatus('Please configure API keys in Settings first', 'error');
        showNotification('Configuration Required', 'Please configure your API keys in the Settings page before loading volumes.');
        return;
    }
    
    // Additional check for placeholder values
    const apiKey = window.KAPOWARR_API_KEY || '';
    const baseUrl = window.KAPOWARR_URL || '';
    
    if (apiKey === 'your-kapowarr-api-key-here' || apiKey === '' || 
        baseUrl === 'http://your-kapowarr-server:port' || baseUrl === '') {
        updateStatus('Please configure API keys in Settings first', 'error');
        showNotification('Configuration Required', 'Please configure your API keys in the Settings page before loading volumes.');
        return;
    }
    
    showLoading();
    updateStatus('Refreshing volumes from Kapowarr...', 'info');

    // First refresh the cache from Kapowarr
    fetch('/api/cache/refresh', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus('Cache refreshed, loading volumes...', 'info');
            
            // Now load the refreshed volumes
            return fetch('/api/volumes');
        } else {
            throw new Error(data.error || 'Failed to refresh cache');
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            currentVolumes = data.volumes;
            displayVolumes(data.volumes);
            updateStatus(`Loaded ${data.volumes.length} volumes (fresh from Kapowarr)`, 'success');
            showNotification('Success', `Loaded ${data.volumes.length} volumes (fresh from Kapowarr)`);
        } else {
            updateStatus(`Error: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        hideLoading();
        updateStatus(`Error: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function displayVolumes(volumes) {
    const container = document.getElementById('volumesContainer');
    const countElement = document.getElementById('volumeCount');
    
    if (!container) return;
    
    // Show search controls when volumes are loaded
    const searchControls = document.getElementById('searchControls');
    if (searchControls) {
        searchControls.style.display = 'block';
    }
    
    // Populate folder filter dropdown
    populateFolderFilter(volumes);
    
    // Apply current filters and display
    applyFiltersAndDisplay();
}

function populateFolderFilter(volumes) {
    const folderFilter = document.getElementById('folderFilter');
    if (!folderFilter) return;
    
    // Extract only the main folder names (first level, before any slashes) from stripped paths
    const mainFolders = [...new Set(volumes.map(v => {
        if (v.volume_folder) {
            // Strip parent directory and take only the first part
            const strippedPath = stripParentDirectory(v.volume_folder);
            const parts = strippedPath.split('/');
            return parts[0];
        }
        return null;
    }).filter(f => f))];
    
    // Clear existing options except "All Folders"
    folderFilter.innerHTML = '<option value="">All Folders</option>';
    
    // Add main folder options
    mainFolders.sort().forEach(folder => {
        const option = document.createElement('option');
        option.value = folder;
        option.textContent = folder;
        folderFilter.appendChild(option);
    });
}

function applyFiltersAndDisplay() {
    const searchInput = document.getElementById('searchInput');
    const folderFilter = document.getElementById('folderFilter');
    const sortOrder = document.getElementById('sortOrder');
    
    if (!searchInput || !folderFilter || !sortOrder) return;
    
    const searchTerm = searchInput.value.toLowerCase();
    const folderFilterValue = folderFilter.value;
    const sortOrderValue = sortOrder.value;
    
    // Apply search filter
    filteredVolumes = currentVolumes.filter(volume => {
        const strippedPath = stripParentDirectory(volume.volume_folder);
        const matchesSearch = !searchTerm || 
            strippedPath?.toLowerCase().includes(searchTerm) ||
            volume.id.toString().includes(searchTerm);
        
        // Check if the volume's main folder matches the selected filter
        const matchesFolder = !folderFilterValue || 
            (strippedPath && strippedPath.split('/')[0] === folderFilterValue);
        
        return matchesSearch && matchesFolder;
    });
    
    // Apply sorting
    if (sortOrderValue === 'alphabetical') {
        filteredVolumes.sort((a, b) => {
            const folderA = stripParentDirectory(a.volume_folder) || `Volume ${a.id}`;
            const folderB = stripParentDirectory(b.volume_folder) || `Volume ${b.id}`;
            
            // Extract just the filename (last part after the last slash) for sorting
            const filenameA = folderA.split('/').pop() || folderA;
            const filenameB = folderB.split('/').pop() || folderB;
            
            return filenameA.localeCompare(filenameB);
        });
    } else {
        // Sort by ID (default)
        filteredVolumes.sort((a, b) => a.id - b.id);
    }
    
    // Display filtered volumes
    displayFilteredVolumes(filteredVolumes);
}

function displayFilteredVolumes(volumes) {
    const container = document.getElementById('volumesContainer');
    const countElement = document.getElementById('volumeCount');
    
    if (!container) return;
    
    if (countElement) {
        countElement.textContent = `${volumes.length} volumes`;
    }
    
    if (volumes.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-4">No volumes match your search criteria</p>';
        return;
    }

    const volumesHTML = volumes.map(volume => `
        <div class="col-md-6 col-lg-4 mb-3">
            <div class="card volume-card h-100" data-volume-id="${volume.id}">
                <div class="card-body p-0">
                    <div class="d-flex">
                        <div class="cover-image-container position-relative">
                            <!-- Selection Checkbox -->
                            <div class="position-absolute top-0 start-0 m-2" style="z-index: 10;">
                                <div class="form-check">
                                    <input class="form-check-input volume-checkbox" type="checkbox" 
                                           id="volume-checkbox-${volume.id}" 
                                           data-volume-id="${volume.id}"
                                           ${selectedVolumes.has(volume.id) ? 'checked' : ''}>
                                </div>
                            </div>
                            <div class="cover-loading">
                                <div class="spinner-border spinner-border-sm text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                            <img src="${getKapowarrUrl()}/api/volumes/${volume.id}/cover?api_key=${getApiKey()}" 
                                 class="cover-image" 
                                 alt="Cover for ${stripParentDirectory(volume.volume_folder) || `Volume ${volume.id}`}"
                                 onload="this.classList.add('loaded'); this.previousElementSibling.style.display='none';"
                                 onerror="this.style.display='none'; this.previousElementSibling.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="no-cover-placeholder" style="display: none;">
                                <i class="fas fa-book fa-3x text-muted"></i>
                                <p class="text-muted mt-2">No Cover</p>
                            </div>
                        </div>
                        <div class="flex-grow-1 p-3">
                            <h6 class="card-title">${stripParentDirectory(volume.volume_folder) || `Volume ${volume.id}`}</h6>
                            <small class="text-muted">ID: ${volume.id}</small>
                            <span class="badge bg-success status-badge ms-2">${volume.status}</span>
                            <div class="mt-3">
                                <div class="d-grid gap-2 d-md-block">
                                    <a href="/volume/${volume.id}" class="btn btn-outline-primary btn-sm me-md-2 mb-2">
                                        <i class="fas fa-eye me-1"></i>View Details
                                    </a>
                                    <button class="btn btn-primary btn-sm me-2" onclick="processMetadataAndInject(${volume.id})">
                                        <i class="fas fa-magic me-1"></i>Get Metadata
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        <div class="row">
            ${volumesHTML}
        </div>
    `;
    
    // Add event listeners to checkboxes
    document.querySelectorAll('.volume-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const volumeId = parseInt(this.getAttribute('data-volume-id'));
            toggleVolumeSelection(volumeId);
        });
    });
    
    // Update selection UI after rendering
    updateSelectionUI();
}

/**
 * Metadata and XML Processing Functions
 */
function processMetadataAndInject(volumeId = null) {
    // If no volumeId provided, try to get it from the page context
    if (!volumeId) {
        volumeId = getVolumeIdFromPage();
    }
    
    if (!volumeId) {
        updateStatus('Error: Could not determine volume ID', 'error');
        showNotification('Error', 'Could not determine volume ID');
        return;
    }
    
    updateStatus(`Starting complete metadata workflow for volume ${volumeId}...`, 'info');
    
    // Step 1: Process metadata
    fetch(`/api/volume/${volumeId}/metadata`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Metadata processing started for volume ${volumeId}, waiting for completion...`, 'info');
            showNotification('Success', 'Metadata processing started');
            
            // Poll for metadata completion, then generate XML
            pollTaskStatusAndGenerateXML(volumeId, data.task_id);
        } else {
            updateStatus(`Error: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function pollTaskStatusAndGenerateXML(volumeId, taskId) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                updateStatus(`Metadata processing and injection completed for volume ${volumeId}!`, 'success');
                showNotification('Success', data.message);
                
                // Reload the page to show updated data
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                updateStatus(`Error: ${data.error}`, 'error');
                showNotification('Error', data.error);
            }
        })
        .catch(error => {
            clearInterval(pollInterval);
            updateStatus(`Error checking task status: ${error.message}`, 'error');
        });
    }, 2000);
}

// This function is no longer needed - the new workflow handles everything in one step
// function generateXMLAfterMetadata(volumeId) {
//     // Removed - new workflow processes everything in one step
// }

// This function is no longer needed - the new workflow handles everything in one step
// function injectMetadataIntoComics(volumeId) {
//     // Removed - new workflow processes everything in one step
// }

/**
 * Utility Functions
 */
function stripParentDirectory(path) {
    if (!path) return path;
    const parts = path.split('/');
    // Remove the first directory (parent) and join the rest
    return parts.slice(1).join('/');
}

function getVolumeIdFromPage() {
    // Try to get volume ID from the URL path
    const pathParts = window.location.pathname.split('/');
    const volumeId = pathParts[pathParts.length - 1];
    
    // Validate that it's a number
    if (volumeId && !isNaN(volumeId)) {
        return volumeId;
    }
    
    // Fallback: try to get from a data attribute or other source
    const volumeElement = document.querySelector('[data-volume-id]');
    if (volumeElement) {
        return volumeElement.getAttribute('data-volume-id');
    }
    
    return null;
}

function clearFilters() {
    const searchInput = document.getElementById('searchInput');
    const folderFilter = document.getElementById('folderFilter');
    const sortOrder = document.getElementById('sortOrder');
    
    if (searchInput) searchInput.value = '';
    if (folderFilter) folderFilter.value = '';
    if (sortOrder) sortOrder.value = 'id';
    
    applyFiltersAndDisplay();
}

function cleanupTempFiles() {
    if (confirm('Are you sure you want to clean up all temporary files?')) {
        fetch('/cleanup', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateStatus('Temporary files cleaned up', 'success');
                showNotification('Success', 'Temporary files cleaned up');
            } else {
                updateStatus(`Error: ${data.error}`, 'error');
                showNotification('Error', data.error);
            }
        })
        .catch(error => {
            updateStatus(`Error: ${error.message}`, 'error');
            showNotification('Error', error.message);
        });
    }
}

function getCacheInfo() {
    fetch('/api/cache/info')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCacheInfo(data.cache_info);
            } else {
                showNotification('Error', 'Failed to get cache information');
            }
        })
        .catch(error => {
            showNotification('Error', 'Error getting cache information: ' + error.message);
        });
}

function displayCacheInfo(cacheInfo) {
    const cacheDetails = document.getElementById('cacheDetails');
    const cacheInfoDiv = document.getElementById('cacheInfo');
    
    let html = '';
    
    if (cacheInfo.volumes_count > 0) {
        const cacheAge = cacheInfo.cache_age;
        const ageText = cacheAge ? formatTimeDifference(cacheAge) : 'Unknown';
        
        html += `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Volumes Cached:</strong> ${cacheInfo.volumes_count}</p>
                    <p><strong>Cache Age:</strong> ${ageText}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Metadata Processed:</strong> ${cacheInfo.processing_stats.metadata_processed}</p>
                    <p><strong>XML Generated:</strong> ${cacheInfo.processing_stats.xml_generated}</p>
                </div>
            </div>
        `;
        
        // Show Kapowarr stats comparison if available
        if (cacheInfo.last_kapowarr_total !== undefined && cacheInfo.last_kapowarr_total !== null) {
            html += `
                <div class="row mt-2">
                    <div class="col-12">
                        <hr>
                        <p><strong>Kapowarr Stats:</strong> Last known total: ${cacheInfo.last_kapowarr_total} volumes</p>
                        <small class="text-muted">This helps detect when new volumes are added to Kapowarr</small>
                    </div>
                </div>
            `;
        }
    } else {
        html += '<p class="text-muted">No volumes cached</p>';
    }
    
    cacheDetails.innerHTML = html;
    cacheInfoDiv.style.display = 'block';
}

function formatTimeDifference(timeDiff) {
    if (!timeDiff) return 'Unknown';
    
    // Handle both old format (timedelta object) and new format (object with components)
    if (typeof timeDiff === 'object' && timeDiff.total_seconds !== undefined) {
        const hours = Math.floor(timeDiff.total_seconds / 3600);
        const minutes = Math.floor((timeDiff.total_seconds % 3600) / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ago`;
        } else {
            return `${minutes}m ago`;
        }
    } else if (typeof timeDiff === 'object' && timeDiff.days !== undefined) {
        // New format with individual components
        if (timeDiff.days > 0) {
            return `${timeDiff.days}d ${timeDiff.hours}h ${timeDiff.minutes}m ago`;
        } else if (timeDiff.hours > 0) {
            return `${timeDiff.hours}h ${timeDiff.minutes}m ago`;
        } else {
            return `${timeDiff.minutes}m ago`;
        }
    } else {
        return 'Unknown';
    }
}

function refreshCache() {
    if (confirm('Are you sure you want to refresh the volume cache? This will fetch fresh data from Kapowarr.')) {
        fetch('/api/cache/refresh', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Success', data.message);
                // Reload volumes to show updated data
                refreshAndLoadVolumes();
            } else {
                showNotification('Error', 'Failed to refresh cache: ' + data.error);
            }
        })
        .catch(error => {
            showNotification('Error', 'Error refreshing cache: ' + error.message);
        });
    }
}

function clearCache() {
    if (confirm('Are you sure you want to clear the volume cache? This will remove all cached volume data.')) {
        fetch('/api/cache/clear', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Success', 'Volume cache cleared successfully');
                // Hide cache info and reload volumes
                document.getElementById('cacheInfo').style.display = 'none';
                loadVolumes();
            } else {
                showNotification('Error', 'Failed to clear cache: ' + data.error);
            }
        })
        .catch(error => {
            showNotification('Error', 'Error clearing cache: ' + error.message);
        });
    }
}

function updateDatabasePaths() {
    if (confirm('This will update all volume paths in the database to use relative paths instead of absolute paths. Continue?')) {
        fetch('/api/cache/update-paths', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Success', 'Database paths updated successfully');
                // Reload volumes to show updated data
                loadVolumes();
            } else {
                showNotification('Error', 'Failed to update paths: ' + data.error);
            }
        })
        .catch(error => {
            showNotification('Error', 'Error updating paths: ' + error.message);
        });
    }
}

function migrateDatabaseSchema() {
    if (confirm('This will fix the database schema by adding missing columns. This may take a moment. Continue?')) {
        fetch('/api/cache/migrate-schema', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Success', 'Database schema fixed successfully');
                // Reload volumes to show updated data
                loadVolumes();
            } else {
                showNotification('Error', 'Failed to fix schema: ' + data.error);
            }
        })
        .catch(error => {
            showNotification('Error', 'Error fixing schema: ' + error.message);
        });
    }
}

function checkForNewVolumes() {
    updateStatus('Checking for new volumes...', 'info');
    
    fetch('/api/cache/check-new', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.new_volumes_found) {
                updateStatus(data.message, 'success');
                showNotification('New Volumes Found!', data.message);
                
                // Reload volumes to show the new ones
                refreshAndLoadVolumes();
                
                // Update cache info to show new stats
                getCacheInfo();
            } else {
                updateStatus(data.message, 'info');
                showNotification('No New Volumes', data.message);
            }
        } else {
            updateStatus(`Error: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error: ${error.message}`, 'error');
        showNotification('Error', 'Error checking for new volumes: ' + error.message);
    });
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
    // Search input event listener
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', applyFiltersAndDisplay);
    }
    
    // Folder filter event listener
    const folderFilter = document.getElementById('folderFilter');
    if (folderFilter) {
        folderFilter.addEventListener('change', applyFiltersAndDisplay);
    }
    
    // Sort order event listener
    const sortOrder = document.getElementById('sortOrder');
    if (sortOrder) {
        sortOrder.addEventListener('change', applyFiltersAndDisplay);
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Ctrl+A for select all
        if (event.ctrlKey && event.key === 'a') {
            event.preventDefault();
            if (filteredVolumes.length > 0) {
                selectAllVolumes();
                showNotification('Info', 'All volumes selected (Ctrl+A)');
            }
        }
        
        // Escape to deselect all
        if (event.key === 'Escape') {
            if (selectedVolumes.size > 0) {
                deselectAllVolumes();
                showNotification('Info', 'All selections cleared (Esc)');
            }
        }
    });
}

/**
 * Page Initialization
 */
function initializePage() {
    setupEventListeners();
    
    // Auto-load volumes on main page only if configured
    if (document.getElementById('volumesContainer') && window.IS_CONFIGURED) {
        setTimeout(() => {
            loadVolumes();
        }, 500);
    } else if (document.getElementById('volumesContainer') && !window.IS_CONFIGURED) {
        // Show message for unconfigured state
        const volumesContainer = document.getElementById('volumesContainer');
        if (volumesContainer) {
            volumesContainer.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-cog fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">Configuration Required</h5>
                    <p class="text-muted">Please configure your API keys in the Settings page to start using the app.</p>
                    <a href="/settings" class="btn btn-primary">
                        <i class="fas fa-cog me-1"></i>Go to Settings
                    </a>
                </div>
            `;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePage);

// Export functions for use in other scripts (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showNotification,
        updateStatus,
        loadVolumes,
        processMetadataAndInject,
        injectMetadataIntoComics,
        clearFilters,
        cleanupTempFiles,
        getCacheInfo,
        refreshCache,
        clearCache,
        updateDatabasePaths,
        migrateDatabaseSchema,
        checkForNewVolumes
    };
}
