/**
 * Comic Metadata Manager - Volume Detail Page JavaScript
 * Specific functionality for the volume detail page
 */

function processMetadataAndInject() {
    updateStatus('Starting complete metadata workflow...', 'info');
    
    const volumeId = getVolumeIdFromPage();
    
    fetch(`/api/volume/${volumeId}/metadata`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Metadata processing started successfully`, 'success');
            showNotification('Success', data.message);
            
            // Poll for completion
            pollTaskStatusAndGenerateXML(data.task_id);
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

function processMetadata() {
    updateStatus('Processing metadata from ComicVine for comic file injection...', 'info');
    
    const volumeId = getVolumeIdFromPage();
    
    fetch(`/api/volume/${volumeId}/metadata`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Metadata processing started successfully`, 'success');
            showNotification('Success', data.message);
            
            // Poll for completion
            pollTaskStatus(data.task_id);
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

function processIssueMetadata(volumeId, issueIndex, issueNumber) {
    // Update the specific issue's status
    const issueStatusElement = document.getElementById(`issue-status-${issueIndex}`);
    if (issueStatusElement) {
        issueStatusElement.textContent = 'Processing metadata...';
        issueStatusElement.className = 'text-info';
    }
    
    // Disable the button for this issue
    const issueButton = document.querySelector(`[data-issue-index="${issueIndex}"]`);
    if (issueButton) {
        issueButton.disabled = true;
        issueButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
    }
    
    updateStatus(`Processing metadata for issue ${issueNumber}...`, 'info');
    
    fetch(`/api/volume/${volumeId}/issue/${issueIndex}/metadata`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Metadata processing started for issue ${issueNumber}`, 'success');
            showNotification('Success', data.message);
            
            // Poll for completion
            pollIssueTaskStatus(data.task_id, issueIndex, issueNumber);
        } else {
            updateStatus(`Error processing issue ${issueNumber}: ${data.error}`, 'error');
            showNotification('Error', data.error);
            
            // Reset issue status on error
            if (issueStatusElement) {
                issueStatusElement.textContent = 'Error occurred';
                issueStatusElement.className = 'text-danger';
            }
            if (issueButton) {
                issueButton.disabled = false;
                issueButton.innerHTML = '<i class="fas fa-download me-1"></i>Get Metadata';
            }
        }
    })
    .catch(error => {
        updateStatus(`Error processing issue ${issueNumber}: ${error.message}`, 'error');
        showNotification('Error', error.message);
        
        // Reset issue status on error
        if (issueStatusElement) {
            issueStatusElement.textContent = 'Error occurred';
            issueStatusElement.className = 'text-danger';
        }
        if (issueButton) {
            issueButton.disabled = false;
            issueButton.innerHTML = '<i class="fas fa-download me-1"></i>Get Metadata';
        }
    });
}

function pollIssueTaskStatus(taskId, issueIndex, issueNumber) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                updateStatus(`Metadata processing and injection completed for issue ${issueNumber}`, 'success');
                showNotification('Success', data.message);
                
                // Show detailed results if available
                if (data.result && data.result.injection_results) {
                    let resultsMessage = `Injected metadata into ${data.result.injection_results.length} comic files:\n`;
                    data.result.injection_results.forEach(result => {
                        const status = result.success ? '✅' : '❌';
                        resultsMessage += `${status} ${result.file}: ${result.success ? result.message : result.error}\n`;
                    });
                    showNotification('Injection Results', resultsMessage);
                }
                
                // Update issue status
                const issueStatusElement = document.getElementById(`issue-status-${issueIndex}`);
                if (issueStatusElement) {
                    issueStatusElement.textContent = 'Metadata injected successfully';
                    issueStatusElement.className = 'text-success';
                }
                
                // Show metadata info
                const metadataInfoElement = document.getElementById(`metadata-info-${issueIndex}`);
                if (metadataInfoElement) {
                    metadataInfoElement.style.display = 'block';
                    // Update the text to show injection was successful
                    const summaryElement = metadataInfoElement.querySelector('.metadata-summary');
                    if (summaryElement) {
                        summaryElement.textContent = 'Metadata injected into comic files';
                    }
                }
                
                // Re-enable button and update text
                const issueButton = document.querySelector(`[data-issue-index="${issueIndex}"]`);
                if (issueButton) {
                    issueButton.disabled = false;
                    issueButton.innerHTML = '<i class="fas fa-check me-1"></i>Metadata Injected';
                    issueButton.className = 'btn btn-sm btn-success w-100';
                }
                
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                updateStatus(`Error processing issue ${issueNumber}: ${data.error}`, 'error');
                showNotification('Error', data.error);
                
                // Update issue status
                const issueStatusElement = document.getElementById(`issue-status-${issueIndex}`);
                if (issueStatusElement) {
                    issueStatusElement.textContent = 'Error occurred';
                    issueStatusElement.className = 'text-danger';
                }
                
                // Re-enable button
                const issueButton = document.querySelector(`[data-issue-index="${issueIndex}"]`);
                if (issueButton) {
                    issueButton.disabled = false;
                    issueButton.innerHTML = '<i class="fas fa-download me-1"></i>Get Metadata';
                }
            }
        })
        .catch(error => {
            clearInterval(pollInterval);
            updateStatus(`Error checking task status for issue ${issueNumber}: ${error.message}`, 'error');
            
            // Reset issue status on error
            const issueStatusElement = document.getElementById(`issue-status-${issueIndex}`);
            if (issueStatusElement) {
                issueStatusElement.textContent = 'Error occurred';
                issueStatusElement.className = 'text-danger';
            }
            
            const issueButton = document.querySelector(`[data-issue-index="${issueIndex}"]`);
            if (issueButton) {
                issueButton.disabled = false;
                issueButton.innerHTML = '<i class="fas fa-download me-1"></i>Get Metadata';
            }
        });
    }, 2000);
}

function pollTaskStatusAndGenerateXML(taskId) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                updateStatus('Metadata processing and injection completed successfully!', 'success');
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

function pollTaskStatus(taskId) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                updateStatus(`Metadata processing completed: ${data.message}`, 'success');
                showNotification('Success', data.message);
                
                // Refresh the page to show updated data
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
// function generateXMLAfterMetadata() {
//     // Removed - new workflow processes everything in one step
// }

// This function is no longer needed - the new workflow handles everything in one step
// function injectMetadataIntoComics() {
//     // Removed - new workflow processes everything in one step
// }

// This function is no longer needed - the new workflow handles everything in one step
// function generateXML() {
//     // Removed - new workflow processes everything in one step
// }

function refreshVolume() {
    updateStatus('Refreshing volume data...', 'info');
    location.reload();
}

function cleanupTempDirectories() {
    updateStatus('Cleaning up temporary directories...', 'info');
    
    fetch('/api/cleanup/temp', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Cleanup completed: ${data.message}`, 'success');
            showNotification('Success', data.message);
            
            if (data.cleaned_dirs && data.cleaned_dirs.length > 0) {
                let detailsMessage = `Cleaned up ${data.total_cleaned} directories:\n`;
                data.cleaned_dirs.forEach(dir => {
                    detailsMessage += `• ${dir}\n`;
                });
                showNotification('Cleanup Details', detailsMessage);
            }
        } else {
            updateStatus(`Cleanup failed: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Cleanup error: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function cleanupTempDirectoriesAggressive() {
    if (!confirm('This will clean up ALL temporary directories immediately. Continue?')) {
        return;
    }
    
    updateStatus('Cleaning up ALL temporary directories...', 'info');
    
    fetch('/api/cleanup/temp/aggressive', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Aggressive cleanup completed: ${data.cleaned_count} cleaned, ${data.failed_count} failed`, 'success');
            showNotification('Success', `Cleaned ${data.cleaned_count} directories, ${data.failed_count} failed`);
            
            if (data.total_found > 0) {
                let detailsMessage = `Found ${data.total_found} temporary directories:\n`;
                detailsMessage += `• Cleaned: ${data.cleaned_count}\n`;
                detailsMessage += `• Failed: ${data.failed_count}`;
                showNotification('Cleanup Details', detailsMessage);
            }
        } else {
            updateStatus(`Aggressive cleanup failed: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Aggressive cleanup error: ${error.message}`, 'error');
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
    
    // Last resort: try to parse from the page title
    const titleMatch = document.title.match(/Volume (\d+)/);
    if (titleMatch) {
        return titleMatch[1];
    }
    
    console.error('Could not determine volume ID from page');
    return null;
}

/**
 * Page Initialization for Volume Detail
 */
function initializeVolumeDetailPage() {
    // Set up event delegation for issue processing buttons
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('process-issue-btn')) {
            const volumeId = e.target.getAttribute('data-volume-id');
            const issueIndex = e.target.getAttribute('data-issue-index');
            const issueNumber = e.target.getAttribute('data-issue-number');
            processIssueMetadata(volumeId, issueIndex, issueNumber);
        }
    });
    
    console.log('Volume detail page initialized');
}

// Initialize when DOM is loaded (only on volume detail page)
if (document.querySelector('.cover-image-container-large')) {
    document.addEventListener('DOMContentLoaded', initializeVolumeDetailPage);
}

// Export functions for use in other scripts (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        processMetadataAndGenerateXML,
        processMetadata,
        generateXML,
        refreshVolume,
        getVolumeIdFromPage
    };
}
