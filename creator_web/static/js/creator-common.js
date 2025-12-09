/**
 * PyQuizHub Creator Interface - Common JavaScript
 */

// API helper functions
const CreatorAPI = {
    baseUrl: '',

    async get(endpoint) {
        try {
            const response = await fetch(`/api/${endpoint}`);
            return await response.json();
        } catch (error) {
            console.error(`GET ${endpoint} failed:`, error);
            throw error;
        }
    },

    async post(endpoint, data) {
        try {
            const response = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error(`POST ${endpoint} failed:`, error);
            throw error;
        }
    }
};

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
}

function truncate(str, length = 50) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a proper toast library
    alert(message);
}

// Copy to clipboard helper
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!');
        return true;
    } catch (error) {
        console.error('Copy failed:', error);
        return false;
    }
}

// Form validation helper
function validateQuizJSON(jsonString) {
    try {
        const data = JSON.parse(jsonString);

        const errors = [];

        if (!data.metadata) {
            errors.push('Missing "metadata" section');
        } else if (!data.metadata.title) {
            errors.push('Missing "metadata.title"');
        }

        if (!data.questions || !Array.isArray(data.questions)) {
            errors.push('Missing or invalid "questions" array');
        }

        if (!data.transitions || typeof data.transitions !== 'object') {
            errors.push('Missing or invalid "transitions" object');
        }

        if (!data.variables || typeof data.variables !== 'object') {
            errors.push('Missing or invalid "variables" object');
        }

        return {
            valid: errors.length === 0,
            errors: errors,
            data: data
        };
    } catch (e) {
        return {
            valid: false,
            errors: [`Invalid JSON: ${e.message}`],
            data: null
        };
    }
}

// Export for use in templates
window.CreatorAPI = CreatorAPI;
window.formatDate = formatDate;
window.truncate = truncate;
window.showNotification = showNotification;
window.copyToClipboard = copyToClipboard;
window.validateQuizJSON = validateQuizJSON;
