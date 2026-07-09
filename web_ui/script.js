// web_ui/script.js
// Static dashboard: reads scraped_jobs.json (produced by the scraper on
// GitHub Actions) and renders the job listings, filters, sort and portal
// health monitor. No backend required — deployable to GitHub Pages.

document.addEventListener('DOMContentLoaded', () => {
    let allJobs = [];
    let allOrgs = {};
    let selectedTier = 'relevant';
    let searchQuery = '';
    let selectedOrg = 'all';
    let selectedCategory = 'all';
    let healthSearchQuery = '';
    let sortMode = 'newest';   // 'newest' | 'oldest' | 'org'

    // ── Date helpers ─────────────────────────────────────────────
    // The scraper emits an ISO `date_iso` field for every posting. Parse it
    // UTC-safe and reason about recency from that, instead of feeding
    // ambiguous DD-MM-YYYY strings to `new Date()` (which breaks sorting).
    const DAY_MS = 86400000;

    function jobTime(job) {
        const iso = job && job.date_iso;
        if (iso && /^\d{4}-\d{2}-\d{2}$/.test(iso)) {
            const t = Date.parse(iso + 'T00:00:00Z');
            if (!isNaN(t)) return t;
        }
        return -Infinity;   // undated sinks to the bottom
    }

    function daysFromToday(job) {
        const t = jobTime(job);
        if (t === -Infinity) return null;
        return Math.round((t - Date.now()) / DAY_MS);
    }

    const jobsContainer = document.getElementById('jobs-list-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const displayedCountEl = document.getElementById('displayed-count');
    const totalCountEl = document.getElementById('total-count');
    const orgSelectEl = document.getElementById('org-filter-select');
    const categorySelectEl = document.getElementById('category-filter-select');
    const searchInput = document.getElementById('job-search-input');
    const tabButtons = document.querySelectorAll('#relevancy-tabs .tab-btn');

    // Stats elements
    const statTotalEl = document.getElementById('stat-total-jobs');
    const statRelevantEl = document.getElementById('stat-relevant-jobs');
    const statUncertainEl = document.getElementById('stat-uncertain-jobs');
    const statOrgsEl = document.getElementById('stat-monitored-orgs');
    const genTimeEl = document.getElementById('generated-time-text');

    // Health panel elements
    const healthContainer = document.getElementById('health-list-container');
    const healthSearchInput = document.getElementById('health-search-input');

    // Initialize fetch from scraped_jobs.json
    async function init() {
        try {
            const response = await fetch('scraped_jobs.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            processData(data);
        } catch (error) {
            console.error("Failed to load job listings:", error);
            showErrorState(error.message);
        }
    }

    // Parse raw JSON into list structures
    function processData(data) {
        // Time formatting
        if (data.generated_at) {
            const date = new Date(data.generated_at);
            const formattedDate = date.toLocaleDateString(undefined, {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
            });
            const formattedTime = date.toLocaleTimeString(undefined, {
                hour: '2-digit', minute: '2-digit'
            });
            genTimeEl.textContent = `Last Checked: ${formattedDate} at ${formattedTime}`;
        }

        // Summary metrics
        if (data.summary) {
            statTotalEl.textContent = data.summary.total ?? 0;
            statRelevantEl.textContent = data.summary.relevant ?? 0;
            statUncertainEl.textContent = data.summary.uncertain ?? 0;
            statOrgsEl.textContent = `${data.summary.orgs_scraped ?? 0}/${(data.summary.orgs_scraped ?? 0) + (data.summary.orgs_failed ?? 0)}`;
        }

        // Org parsing and flat jobs list
        if (data.orgs) {
            allOrgs = data.orgs;
            for (const [orgKey, orgInfo] of Object.entries(data.orgs)) {
                const orgName = orgInfo.name || orgKey.toUpperCase();
                const orgCategory = orgInfo.category || 'main';

                if (orgInfo.jobs && Array.isArray(orgInfo.jobs)) {
                    orgInfo.jobs.forEach(job => {
                        allJobs.push({ ...job, orgKey, orgName, category: orgCategory });
                    });
                }
            }

            // Default order: newest dates first (see sortJobs()).
            sortJobs();
        }

        populateOrgSelect();

        loadingIndicator.style.display = 'none';
        jobsContainer.style.display = 'flex';

        renderJobs();
        renderHealthList();
    }

    // Populate filter dropdown with organizations that have active listings
    function populateOrgSelect() {
        const orgsWithJobs = new Set();
        allJobs.forEach(job => orgsWithJobs.add(JSON.stringify({ key: job.orgKey, name: job.orgName })));

        Array.from(orgsWithJobs)
            .map(o => JSON.parse(o))
            .sort((a, b) => a.name.localeCompare(b.name))
            .forEach(org => {
                const option = document.createElement('option');
                option.value = org.key;
                option.textContent = org.name;
                orgSelectEl.appendChild(option);
            });
    }

    // Filter jobs based on search query, category, org select and tab tier
    function getFilteredJobs() {
        return allJobs.filter(job => {
            if (selectedTier !== 'all' && job.tier !== selectedTier) return false;
            if (selectedCategory !== 'all' && job.category !== selectedCategory) return false;
            if (selectedOrg !== 'all' && job.orgKey !== selectedOrg) return false;
            if (searchQuery) {
                const q = searchQuery.toLowerCase();
                return job.title.toLowerCase().includes(q) || job.orgName.toLowerCase().includes(q);
            }
            return true;
        });
    }

    // Sort the master job list per the active sort mode.
    // Undated postings always sink to the bottom, regardless of direction.
    function sortJobs() {
        if (sortMode === 'org') {
            allJobs.sort((a, b) =>
                a.orgName.localeCompare(b.orgName) || jobTime(b) - jobTime(a));
            return;
        }
        const dir = sortMode === 'oldest' ? -1 : 1;
        allJobs.sort((a, b) => {
            const ta = jobTime(a), tb = jobTime(b);
            const da = ta === -Infinity, db = tb === -Infinity;
            if (da && db) return 0;
            if (da) return 1;
            if (db) return -1;
            return dir * (tb - ta);
        });
    }

    // Render matching jobs list
    function renderJobs() {
        const filtered = getFilteredJobs();
        displayedCountEl.textContent = filtered.length;
        totalCountEl.textContent = allJobs.length;

        jobsContainer.innerHTML = '';

        if (filtered.length === 0) {
            jobsContainer.innerHTML = `
                <div class="glass-panel empty-state">
                    <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path>
                    </svg>
                    <h3>No job postings match your filters</h3>
                    <p style="font-size: 0.9rem; margin-top: 4px; color: var(--text-muted);">Try adjusting your search criteria or switching filter tabs.</p>
                </div>`;
            return;
        }

        filtered.forEach(job => {
            const card = document.createElement('article');
            card.className = 'glass-panel job-card';

            let badgeLabel = job.tier;
            if (job.tier === 'relevant') badgeLabel = 'Relevant CS/IT';

            // Date from the normalized ISO field when present.
            let dateDisplay = 'Active';
            const t = jobTime(job);
            if (t !== -Infinity) {
                dateDisplay = new Date(t).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC'
                });
            } else if (job.date && job.date !== '-') {
                dateDisplay = job.date;
            }

            const dft = daysFromToday(job);
            const isNew = dft !== null && dft <= 0 && dft >= -14;
            const newBadge = isNew ? '<span class="new-badge">NEW</span>' : '';

            let linksHtml = '';
            if (job.apply_link) {
                linksHtml += `
                    <a href="${escapeHtml(job.apply_link)}" target="_blank" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;" rel="noopener noreferrer">
                        <span>Apply Online</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                    </a>`;
            }
            if (job.pdf_link) {
                linksHtml += `
                    <a href="${escapeHtml(job.pdf_link)}" target="_blank" class="btn btn-primary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;" rel="noopener noreferrer">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        <span>Notification (PDF)</span>
                    </a>`;
            }
            if (!linksHtml) {
                linksHtml = `
                    <a href="${escapeHtml(job.link || '#')}" target="_blank" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;" rel="noopener noreferrer">
                        <span>View Link</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                    </a>`;
            }

            card.innerHTML = `
                <div class="job-card-header">
                    <div>
                        <span class="org-badge">${escapeHtml(job.orgName)}</span>
                        <h3 style="margin-top: 8px;">
                            <a href="${escapeHtml(job.link || '#')}" target="_blank" class="job-title" rel="noopener noreferrer">${escapeHtml(job.title)}</a>
                        </h3>
                    </div>
                    <span class="tier-badge ${job.tier}">${escapeHtml(badgeLabel)}</span>
                </div>
                <div class="job-meta">
                    <div class="meta-item">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                        <span>${escapeHtml(dateDisplay)}</span>
                        ${newBadge}
                    </div>
                    <div class="meta-item" style="margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
                        ${linksHtml}
                    </div>
                </div>`;
            jobsContainer.appendChild(card);
        });
    }

    // Render health panel monitor in the sidebar
    function renderHealthList() {
        healthContainer.innerHTML = '';

        const orgsArray = Object.entries(allOrgs).map(([key, info]) => ({
            key,
            name: info.name || key.toUpperCase(),
            status: info.status || 'ok'
        })).sort((a, b) => a.name.localeCompare(b.name));

        const filteredOrgs = orgsArray.filter(org =>
            !healthSearchQuery || org.name.toLowerCase().includes(healthSearchQuery.toLowerCase()));

        if (filteredOrgs.length === 0) {
            healthContainer.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">No matching portals</div>';
            return;
        }

        filteredOrgs.forEach(org => {
            const item = document.createElement('div');
            item.className = 'health-item';
            item.innerHTML = `
                <span class="health-name" title="${escapeHtml(org.name)}">${escapeHtml(org.name)}</span>
                <span class="health-status ${org.status === 'ok' ? 'ok' : 'failed'}">${escapeHtml(org.status)}</span>`;
            healthContainer.appendChild(item);
        });
    }

    // Show error message if fetch fails
    function showErrorState(message) {
        loadingIndicator.style.display = 'none';
        jobsContainer.style.display = 'block';
        jobsContainer.innerHTML = `
            <div class="glass-panel empty-state" style="border-color: var(--danger-border); background: var(--danger-bg);">
                <svg fill="none" stroke="var(--danger-color)" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376C1.83 15.002 2.006 13.622 3 12.5L10.5 5c1-1 2.5-1 3.5 0L21 12.5c1 1.122 1.17 2.502.103 3.626l-1.5 1.5C18.67 18.5 17.5 19 16 19H8c-1.5 0-2.67-.5-3.603-1.374l-1.397-1.25z"></path>
                </svg>
                <h3 style="color: var(--danger-color);">Failed to load job scraper data</h3>
                <p style="font-size: 0.9rem; margin-top: 4px; color: var(--text-secondary);">Reason: ${escapeHtml(message)}</p>
                <p style="font-size: 0.85rem; margin-top: 12px; color: var(--text-muted);">Make sure the daily GitHub Actions check run has executed successfully and 'scraped_jobs.json' is present next to this page.</p>
            </div>`;
    }

    // Simple HTML escape helper
    function escapeHtml(unsafe) {
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Listeners
    searchInput.addEventListener('input', (e) => { searchQuery = e.target.value; renderJobs(); });
    orgSelectEl.addEventListener('change', (e) => { selectedOrg = e.target.value; renderJobs(); });
    categorySelectEl.addEventListener('change', (e) => { selectedCategory = e.target.value; renderJobs(); });

    document.getElementById('sort-select').addEventListener('change', (e) => {
        sortMode = e.target.value;
        sortJobs();
        renderJobs();
    });

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedTier = btn.getAttribute('data-tier');
            renderJobs();
        });
    });

    healthSearchInput.addEventListener('input', (e) => {
        healthSearchQuery = e.target.value;
        renderHealthList();
    });

    init();
});
