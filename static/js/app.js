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
    const batchViewBtn = document.getElementById('batchViewBtn');
    const batchXMLBtn = document.getElementById('batchXMLBtn');
    
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
    if (batchViewBtn) {
        batchViewBtn.disabled = selectedVolumes.size === 0;
    }
    if (batchXMLBtn) {
        batchXMLBtn.disabled = selectedVolumes.size === 0;
    }
    
    // Update individual volume checkboxes
    filteredVolumes.forEach(volume => {
        const checkbox = document.getElementById(`volume-checkbox-${volume.id}`);
        if (checkbox) {
            checkbox.checked = selectedVolumes.has(volume.id);
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
    showLoading();
    updateStatus('Loading volumes...', 'info');

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
    
    // Extract only the main folder names (first level, before any slashes)
    const mainFolders = [...new Set(volumes.map(v => {
        if (v.volume_folder) {
            // Split by slash and take only the first part
            const parts = v.volume_folder.split('/');
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
        const matchesSearch = !searchTerm || 
            volume.volume_folder?.toLowerCase().includes(searchTerm) ||
            volume.id.toString().includes(searchTerm);
        
        // Check if the volume's main folder matches the selected filter
        const matchesFolder = !folderFilterValue || 
            (volume.volume_folder && volume.volume_folder.split('/')[0] === folderFilterValue);
        
        return matchesSearch && matchesFolder;
    });
    
    // Apply sorting
    if (sortOrderValue === 'alphabetical') {
        filteredVolumes.sort((a, b) => {
            const folderA = a.volume_folder || `Volume ${a.id}`;
            const folderB = b.volume_folder || `Volume ${b.id}`;
            
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
                            <div class="position-absolute top-0 start-0 m-2">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" 
                                           id="volume-checkbox-${volume.id}" 
                                           onchange="toggleVolumeSelection(${volume.id})"
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
                                 alt="Cover for ${volume.volume_folder || `Volume ${volume.id}`}"
                                 onload="this.classList.add('loaded'); this.previousElementSibling.style.display='none';"
                                 onerror="this.style.display='none'; this.previousElementSibling.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="no-cover-placeholder" style="display: none;">
                                <i class="fas fa-book fa-3x text-muted"></i>
                                <p class="text-muted mt-2">No Cover</p>
                            </div>
                        </div>
                        <div class="flex-grow-1 p-3">
                            <h6 class="card-title">${volume.volume_folder || `Volume ${volume.id}`}</h6>
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
                updateStatus(`Metadata processing completed for volume ${volumeId}, now preparing XML for comic injection...`, 'success');
                showNotification('Success', 'Metadata completed, preparing XML for comic injection...');
                
                // Step 2: Prepare XML for comic injection
                generateXMLAfterMetadata(volumeId);
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

function generateXMLAfterMetadata(volumeId) {
    updateStatus(`Preparing XML metadata for comic injection for volume ${volumeId}...`, 'info');
    
    fetch(`/api/volume/${volumeId}/xml`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Complete! Metadata processed and XML prepared for comic injection for volume ${volumeId}`, 'success');
            showNotification('Success', 'Metadata and XML preparation completed! Now injecting metadata into comic files...');
            
            // Automatically proceed to metadata injection
            setTimeout(() => {
                injectMetadataIntoComics(volumeId);
            }, 1000);
        } else {
            updateStatus(`Error preparing XML: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error preparing XML: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function injectMetadataIntoComics(volumeId) {
    if (!volumeId) {
        updateStatus('Error: Could not determine volume ID', 'error');
        showNotification('Error', 'Could not determine volume ID');
        return;
    }
    
    updateStatus(`Starting metadata injection into comic files for volume ${volumeId}...`, 'info');
    showNotification('Info', 'Starting metadata injection...');
    
    fetch(`/api/volume/${volumeId}/inject`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Complete! Metadata injected into comic files for volume ${volumeId}`, 'success');
            showNotification('Success', data.message);
            
            // Show detailed results
            let resultsMessage = `Injected metadata into ${data.results.length} comic files:\n`;
            data.results.forEach(result => {
                const status = result.success ? '✅' : '❌';
                resultsMessage += `${status} ${result.file}: ${result.success ? result.message : result.error}\n`;
            });
            
            // Show results in a more detailed way
            showNotification('Results', resultsMessage);
            
            // Show final completion message
            setTimeout(() => {
                showNotification('Workflow Complete!', 'The entire metadata workflow has been completed successfully!');
                
                // Reload the page to show updated button states
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }, 2000);
        } else {
            updateStatus(`Error injecting metadata: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error injecting metadata: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

/**
 * Utility Functions
 */
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
    
    const hours = Math.floor(timeDiff.total_seconds() / 3600);
    const minutes = Math.floor((timeDiff.total_seconds() % 3600) / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ago`;
    } else {
        return `${minutes}m ago`;
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
                loadVolumes();
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
                loadVolumes();
                
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
    
    // Auto-load volumes on main page
    if (document.getElementById('volumesContainer')) {
        setTimeout(() => {
            loadVolumes();
        }, 500);
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
