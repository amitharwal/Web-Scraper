/*
 * Page Auditor Pro - Main JavaScript
 *
 * This script handles all 5 features:
 * 1. Modal interactions ("New Project").
 * 2. Tab switching on the report page.
 * 3. Rendering the "Score Over Time" chart.
 * 4. Project card dropdown menus.
 * 5. Real-time dashboard updates via WebSockets.
 */

document.addEventListener("DOMContentLoaded", () => {

    // Modal Logic
    const openModalBtn = document.getElementById("openProjectModal");
    const modalBackdrop = document.getElementById("projectModal");
    const closeModalBtns = document.querySelectorAll(".close-modal");

    function openModal() {
        if (modalBackdrop) modalBackdrop.classList.add("is-visible");
    }
    function closeModal() {
        if (modalBackdrop) modalBackdrop.classList.remove("is-visible");
    }
    if (openModalBtn) {
        openModalBtn.addEventListener("click", (e) => {
            e.preventDefault();
            openModal();
        });
    }
    closeModalBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            closeModal();
        });
    });
    if (modalBackdrop) {
        modalBackdrop.addEventListener("click", (e) => {
            if (e.target === modalBackdrop) closeModal();
        });
    }

    // Tab Switching Logic
    const tabNav = document.querySelector('.tab-nav');
    if (tabNav) {
        const tabLinks = tabNav.querySelectorAll('.tab-link');
        tabLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabId = link.getAttribute('data-tab');

                // Deactivate all links and content
                tabLinks.forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });

                // Activate the clicked link and its content
                link.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    // Chart.js Logic
    const chartCanvas = document.getElementById('historyChart');
    if (chartCanvas && typeof Chart !== 'undefined') {
        const chartData = JSON.parse(chartCanvas.dataset.history);

        new Chart(chartCanvas, {
            type: 'line',
            data: {
                labels: chartData.labels, // e.g., ["Nov 10", "Nov 11", "Nov 12"]
                datasets: [
                    {
                        label: 'Overall Score',
                        data: chartData.overall, // e.g., [80, 85, 69]
                        borderColor: '#5252E0',
                        backgroundColor: 'rgba(82, 82, 224, 0.1)',
                        fill: true,
                        tension: 0.1
                    },
                    {
                        label: 'Performance',
                        data: chartData.performance,
                        borderColor: '#0D6EFD',
                        hidden: true, // Hide by default
                        tension: 0.1
                    },
                    {
                        label: 'Accessibility',
                        data: chartData.accessibility,
                        borderColor: '#198754',
                        hidden: true,
                        tension: 0.1
                    },
                    {
                        label: 'SEO',
                        data: chartData.seo,
                        borderColor: '#E65100',
                        hidden: true,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }

    // Project Menu Dropdown Logic
    const menuButtons = document.querySelectorAll('.project-card-menu-btn');
    menuButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Stop click from bubbling up to document
            const menuId = btn.getAttribute('data-menu-id');
            const menu = document.getElementById(menuId);

            // Close all other open menus before opening a new one
            closeAllDropdowns(menu); // Pass current menu to exclude it

            // Toggle the clicked menu
            menu.classList.toggle('is-visible');
        });
    });

    // Close all dropdowns if clicking anywhere else on the page
    document.addEventListener('click', () => {
        closeAllDropdowns();
    });

    /**
     * Helper function to close all open dropdowns
     * @param {HTMLElement} [excludeMenu] - A menu to exclude from closing
     */
    function closeAllDropdowns(excludeMenu = null) {
        document.querySelectorAll('.dropdown-menu.is-visible').forEach(menu => {
            if (menu !== excludeMenu) {
                menu.classList.remove('is-visible');
            }
        });
    }

    // REAL-TIME WEBSOCKET LOGIC
    const projectList = document.querySelector('.project-list');

    // Check that the `io` object exists from base.html
    if (projectList && typeof io !== 'undefined') {

        // This 'socket' variable is defined in dashboard.html
        // We just add listeners to it here.
        if (typeof socket !== 'undefined') {
            socket.on('connect', () => {
                console.log('Socket.IO connected and room joined!');
            });

            socket.on('connect_error', (err) => {
                console.error('Socket.IO connection error:', err);
            });

            // This is the main event listener
            socket.on('audit_complete', (data) => {
                console.log('Received audit_complete event:', data);

                // Find the project card on the page
                const projectCard = document.querySelector(`.project-card[data-project-id="${data.project_id}"]`);

                if (projectCard) {
                    // Find the status element
                    const statusEl = projectCard.querySelector('.project-card-status');
                    if (statusEl) {
                        statusEl.textContent = data.new_status;
                    }

                    // Re-enable the "Run Audit" button
                    const auditBtn = projectCard.querySelector('.audit-run-btn');
                    if (auditBtn) {
                        auditBtn.classList.remove('is-loading');
                        auditBtn.disabled = false;
                        auditBtn.textContent = 'Run Audit'; // Restore text
                    }
                }
            });

            // This is the event for when the audit *starts*
            socket.on('audit_started', (data) => {
                console.log('Received audit_started event:', data);

                const projectCard = document.querySelector(`.project-card[data-project-id="${data.project_id}"]`);

                if (projectCard) {
                    const statusEl = projectCard.querySelector('.project-card-status');
                    if (statusEl) {
                        statusEl.textContent = 'Audit running...';
                    }

                    // Disable the "Run Audit" button
                    const auditBtn = projectCard.querySelector('.audit-run-btn');
                    if (auditBtn) {
                        auditBtn.classList.add('is-loading');
                        auditBtn.disabled = true;
                        auditBtn.textContent = 'Running...'; // Change text
                    }
                }
            });
        }
    }
});