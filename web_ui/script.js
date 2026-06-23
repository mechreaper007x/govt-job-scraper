document.addEventListener('DOMContentLoaded', () => {
    const watchModeCheckbox = document.getElementById('watch-mode');
    const intervalGroup = document.getElementById('interval-group');
    const runCoreBtn = document.getElementById('run-core-btn');
    const runScaleBtn = document.getElementById('run-scale-btn');
    const terminalOutput = document.getElementById('terminal-output');
    const clearConsoleBtn = document.getElementById('clear-console');

    let logInterval = null;
    let lastLogs = "";

    // Toggle interval input based on watch mode
    watchModeCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            intervalGroup.style.display = 'flex';
        } else {
            intervalGroup.style.display = 'none';
        }
    });

    // Helper to append a single log entry dynamically
    const appendLog = (message, type = 'info') => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        entry.textContent = `[${timestamp}] ${message}`;
        
        terminalOutput.appendChild(entry);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    };

    // Helper to start polling logs
    const startLogPolling = () => {
        if (logInterval) clearInterval(logInterval);
        
        logInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                
                if (data.logs && data.logs !== lastLogs) {
                    lastLogs = data.logs;
                    // Update terminal output with plain text block
                    terminalOutput.innerHTML = `<pre style="margin:0; white-space: pre-wrap;">${data.logs}</pre>`;
                    terminalOutput.scrollTop = terminalOutput.scrollHeight;
                }
            } catch (err) {
                console.error("Error polling logs:", err);
            }
        }, 1500);
    };

    clearConsoleBtn.addEventListener('click', () => {
        terminalOutput.innerHTML = '<div class="log-entry system">Console cleared.</div>';
    });

    const copyConsoleBtn = document.getElementById('copy-console');
    if (copyConsoleBtn) {
        copyConsoleBtn.addEventListener('click', async () => {
            try {
                const textToCopy = terminalOutput.innerText || terminalOutput.textContent;
                
                // Modern API (Requires HTTPS or localhost)
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(textToCopy);
                } else {
                    // Fallback for older browsers or insecure contexts
                    const textArea = document.createElement("textarea");
                    textArea.value = textToCopy;
                    textArea.style.position = "absolute";
                    textArea.style.left = "-999999px";
                    document.body.prepend(textArea);
                    textArea.select();
                    
                    const successful = document.execCommand('copy');
                    textArea.remove();
                    
                    if (!successful) {
                        throw new Error("execCommand('copy') failed");
                    }
                }
                
                appendLog('Console output copied to clipboard!', 'system');
            } catch (err) {
                console.error('Failed to copy: ', err);
                appendLog('Failed to copy console output. Your browser might be blocking it.', 'error');
            }
        });
    }

    // Run Core Scraper
    runCoreBtn.addEventListener('click', async () => {
        const orgTarget = document.getElementById('org-target').value.trim();
        const isWatchMode = watchModeCheckbox.checked;
        const interval = document.getElementById('watch-interval').value;

        appendLog(`Sending request to start Core Scraper...`, 'command');
        
        try {
            const res = await fetch('/api/run_core', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    org: orgTarget || null,
                    watch_mode: isWatchMode,
                    interval: parseInt(interval, 10)
                })
            });
            const data = await res.json();
            appendLog(`Success: ${data.message} (${data.command})`, 'system');
            startLogPolling();
        } catch (err) {
            appendLog(`Error: ${err.message}`, 'error');
        }
    });

    // Run Scale Scraper
    runScaleBtn.addEventListener('click', async () => {
        const limit = document.getElementById('scale-limit').value;
        const offset = document.getElementById('scale-offset').value;

        appendLog(`Sending request to start Scale Scraper...`, 'command');

        try {
            const res = await fetch('/api/run_scale', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    limit: parseInt(limit, 10),
                    offset: parseInt(offset, 10)
                })
            });
            const data = await res.json();
            appendLog(`Success: ${data.message} (${data.command})`, 'system');
            startLogPolling();
        } catch (err) {
            appendLog(`Error: ${err.message}`, 'error');
        }
    });

    // Download PDF Report
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', () => {
            appendLog('Generating and downloading PDF report...', 'info');
            // Setting window.location directly triggers the file download
            window.location.href = '/api/download_pdf';
        });
    }
});
