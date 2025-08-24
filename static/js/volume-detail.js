/**
 * Comic Metadata Manager - Volume Detail Page JavaScript
 * Specific functionality for the volume detail page
 */

function processMetadata() {
    updateStatus('Processing metadata from ComicVine...', 'info');
    
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

function pollTaskStatusAndGenerateXML(taskId) {
    const pollInterval = setInterval(() => {
        fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                updateStatus('Metadata processing completed, now generating XML files...', 'success');
                showNotification('Success', 'Metadata completed, generating XML...');
                
                // Step 2: Generate XML files - use the consolidated function from app.js
                generateXMLAfterMetadata();
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

function generateXMLAfterMetadata() {
    updateStatus('Generating XML files...', 'info');
    
    const volumeId = getVolumeIdFromPage();
    
    fetch(`/api/volume/${volumeId}/xml`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`Complete! Metadata processed and XML files generated successfully`, 'success');
            showNotification('Success', 'Metadata and XML generation completed!');
            
            // Offer download
            if (confirm('Process completed successfully! XML files are ready for download. Would you like to download them now?')) {
                const filename = data.zip_path.split('/').pop();
                window.location.href = `/download/${filename}`;
            }
        } else {
            updateStatus(`Error generating XML: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error generating XML: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function generateXML() {
    updateStatus('Generating XML files...', 'info');
    
    const volumeId = getVolumeIdFromPage();
    
    fetch(`/api/volume/${volumeId}/xml`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatus(`XML generation completed successfully`, 'success');
            showNotification('Success', data.message);
            
            // Offer download
            if (confirm('XML files generated successfully! Would you like to download them?')) {
                const filename = data.zip_path.split('/').pop();
                window.location.href = `/download/${filename}`;
            }
        } else {
            updateStatus(`Error: ${data.error}`, 'error');
            showNotification('Error', data.error);
        }
    })
    .catch(error => {
        updateStatus(`Error generating XML: ${error.message}`, 'error');
        showNotification('Error', error.message);
    });
}

function refreshVolume() {
    updateStatus('Refreshing volume data...', 'info');
    location.reload();
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
    // Set up any volume detail specific event listeners here
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
