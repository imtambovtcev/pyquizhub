/**
 * Common JavaScript utilities for PyQuizHub Admin Interface
 */

// Show message to user
function showMessage(text, type = 'info') {
    let container = document.getElementById('message-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'message-container';
        document.body.appendChild(container);
    }
    
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;
    
    container.appendChild(message);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        message.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => message.remove(), 300);
    }, 5000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format date
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Format relative time
function formatRelativeTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return formatDate(isoString);
}

// Copy to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showMessage('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showMessage('Copied to clipboard!', 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showMessage('Failed to copy to clipboard', 'error');
    }
    document.body.removeChild(textarea);
}

// Confirm action
function confirmAction(message) {
    return confirm(message);
}

// Format JSON for display
function formatJson(obj) {
    return JSON.stringify(obj, null, 2);
}

// Validate JSON string
function validateJson(jsonString) {
    try {
        JSON.parse(jsonString);
        return { valid: true };
    } catch (error) {
        return { valid: false, error: error.message };
    }
}

// Highlight active nav link
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath || 
            (currentPath.startsWith(linkPath) && linkPath !== '/')) {
            link.style.backgroundColor = 'var(--bg-color)';
            link.style.color = 'var(--primary-color)';
        }
    });
}

// Initialize common features
document.addEventListener('DOMContentLoaded', () => {
    highlightActiveNav();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + S to save (prevent default)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('[data-action="save"]');
            if (saveBtn) saveBtn.click();
        }
    });
});

// Export for use in other scripts
window.adminUtils = {
    showMessage,
    escapeHtml,
    formatDate,
    formatRelativeTime,
    copyToClipboard,
    confirmAction,
    formatJson,
    validateJson
};
