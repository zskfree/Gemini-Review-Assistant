function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // icon based on type
    const icon = type === 'error' ? '⚠️' : '✅';

    const toast = document.createElement('div');
    toast.className = `acid-toast ${type === 'error' ? 'error' : ''}`;
    toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;">
            <span>${icon}</span>
            <span>${message}</span>
        </div>
        <button onclick="this.parentElement.parentElement.remove()" style="background:none;border:none;color:white;font-weight:bold;cursor:pointer;margin-left:15px;">[X]</button>
    `;

    container.appendChild(toast);

    // Auto remove after 3s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Global error handler for fetch
async function fetchWithHandler(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        showToast(e.message, 'error');
        throw e;
    }
}
