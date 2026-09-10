(function scanOverlay() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has('scanning')) return;

    const overlay = document.getElementById('scan-overlay');
    const countEl = document.getElementById('scan-countdown');
    const urlEl = document.getElementById('scan-target-url');
    if (!overlay || !countEl) return;

    const targetUrl = params.get('url') || 'your site';
    if (urlEl) urlEl.textContent = targetUrl;

    overlay.classList.add('is-visible');
    document.body.style.overflow = 'hidden';

    const START_SECONDS = 5;
    let secondsLeft = START_SECONDS;
    countEl.textContent = secondsLeft;

    const timer = setInterval(() => {
        secondsLeft -= 1;

        if (secondsLeft <= 0) {
            clearInterval(timer);
            window.location.replace(window.location.pathname);
            return;
        }

        countEl.textContent = secondsLeft;
    }, 1000);
    document.addEventListener('turbo:before-cache', () => clearInterval(timer), {once: true});
})();

(function siteDetailCharts() {
    window.SitePulse = window.SitePulse || {};

    function cssVar(name, fallback) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    let uptimeChart = null;
    let durationChart = null;
    let modalChart = null;

    function baseScales(gridColor) {
        return {
            x: {grid: {color: gridColor}, ticks: {maxTicksLimit: 6}},
        };
    }

    document.addEventListener('turbo:before-cache', () => {
        if (uptimeChart) {
            uptimeChart.destroy();
            uptimeChart = null;
        }
        if (durationChart) {
            durationChart.destroy();
            durationChart = null;
        }
        if (modalChart) {
            modalChart.destroy();
            modalChart = null;
        }
    });


    function uptimeConfig(data, colors) {
        return {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.uptime,
                    stepped: true,
                    borderColor: colors.green,
                    backgroundColor: colors.greenDim,
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: (ctx) =>
                        ctx.raw === 1 ? colors.green : colors.red,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {duration: 500, easing: 'easeOutQuart'},
                plugins: {legend: {display: false}},
                scales: {
                    ...baseScales(colors.grid),
                    y: {
                        min: -0.15,
                        max: 1.15,
                        grid: {color: colors.grid},

                        afterBuildTicks: (axis) => {
                            axis.ticks = [{value: 0}, {value: 1}];
                        },
                        ticks: {
                            callback: (value) => (value === 1 ? 'Up' : value === 0 ? 'Down' : ''),
                        },
                    },
                },
            },
        };
    }

    function durationConfig(data, colors) {
        return {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.duration,
                    borderColor: colors.azure,
                    backgroundColor: colors.azureDim,
                    fill: true,
                    tension: 0.25,
                    borderWidth: 2,
                    pointRadius: 2,
                    pointBackgroundColor: colors.azure,
                    spanGaps: true,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {duration: 500, easing: 'easeOutQuart'},
                plugins: {legend: {display: false}},
                scales: {
                    ...baseScales(colors.grid),
                    y: {
                        grid: {color: colors.grid},
                        ticks: {callback: (v) => `${v}ms`},
                    },
                },
            },
        };
    }

    function destroyChart(ref) {
        if (ref) ref.destroy();
        return null;
    }

    window.SitePulse.initDetailCharts = function initDetailCharts(data) {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                const uptimeCanvas = document.getElementById('uptime-chart');
                const durationCanvas = document.getElementById('duration-chart');
                if (!uptimeCanvas || !durationCanvas || typeof Chart === 'undefined') return;

                const colors = {
                    grid: cssVar('--border', '#262629'),
                    text: cssVar('--text-dim', '#a6a6ad'),
                    green: cssVar('--green', '#6fe3a8'),
                    greenDim: cssVar('--green-dim', 'rgba(111, 227, 168, 0.14)'),
                    azure: cssVar('--azure', '#4fa3ff'),
                    azureDim: cssVar('--azure-dim', 'rgba(79, 163, 255, 0.14)'),
                    red: cssVar('--red-bright', '#ff9086'),
                };

                Chart.defaults.color = colors.text;
                Chart.defaults.font.family = "'JetBrains Mono', ui-monospace, monospace";
                Chart.defaults.font.size = 11;

                uptimeChart = destroyChart(uptimeChart);
                durationChart = destroyChart(durationChart);


                uptimeChart = new Chart(uptimeCanvas, uptimeConfig(data, colors));
                durationChart = new Chart(durationCanvas, durationConfig(data, colors));

                const modal = document.getElementById('chart-modal');
                const modalTitle = document.getElementById('chart-modal-title');
                const modalCanvas = document.getElementById('chart-modal-canvas');
                const modalClose = document.getElementById('chart-modal-close');
                if (!modal || !modalCanvas) return;

                function openChartModal(kind) {
                    modalChart = destroyChart(modalChart);
                    const config = kind === 'uptime' ? uptimeConfig(data, colors) : durationConfig(data, colors);
                    modalTitle.textContent = kind === 'uptime' ? 'Uptime' : 'Response time';
                    modal.classList.add('is-visible');
                    modal.setAttribute('aria-hidden', 'false');
                    document.body.style.overflow = 'hidden';
                    modalChart = new Chart(modalCanvas, config);
                }

                function closeChartModal() {
                    modal.classList.remove('is-visible');
                    modal.setAttribute('aria-hidden', 'true');
                    document.body.style.overflow = '';
                    modalChart = destroyChart(modalChart);
                }

                document.querySelectorAll('[data-chart-expand]').forEach((btn) => {
                    btn.onclick = () => openChartModal(btn.getAttribute('data-chart-expand'));
                });

                if (modalClose) modalClose.onclick = closeChartModal;
                modal.onclick = (e) => {
                    if (e.target === modal) closeChartModal();
                };

                if (!window.__modalKeydownAttached) {
                    document.addEventListener('keydown', (e) => {
                        const activeModal = document.getElementById('chart-modal');
                        if (e.key === 'Escape' && activeModal && activeModal.classList.contains('is-visible')) {
                            closeChartModal();
                        }
                    });
                    window.__modalKeydownAttached = true;
                }
            });
        });
    };
})();

function showToastError(message) {
    let toast = document.querySelector('.toast-error');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast-error';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.remove('is-visible');
    void toast.offsetWidth;
    toast.classList.add('is-visible');

    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => {
        toast.classList.remove('is-visible');
    }, 4000);
}

(function setupToggleForms() {
    if (window.__toggleSetupDone) return;
    window.__toggleSetupDone = true;
    document.addEventListener('submit', async (e) => {
        const form = e.target;
        if (!form.classList.contains('toggle-form')) return;
        e.preventDefault();


        const btn = form.querySelector('.toggle-switch');
        if (!btn) return;

        btn.classList.toggle('is-on');
        const isOn = btn.classList.contains('is-on');

        btn.setAttribute('aria-checked', isOn);
        const newLabel = isOn ? 'Pause monitoring' : 'Resume monitoring';
        btn.setAttribute('aria-label', newLabel);
        btn.setAttribute('title', newLabel);

        const currentCard = form.closest('.site-card');
        const statusBadge = currentCard.querySelector('.status-badge');
        if (statusBadge) {
            if (isOn) {
                statusBadge.textContent = "Active";
                statusBadge.className = "status-badge status-badge--ok";
            } else {
                statusBadge.textContent = "Paused";
                statusBadge.className = "status-badge status-badge--paused";
            }
        }


        try {
            const response = await fetch(form.action, {
                method: form.method || 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Server Error');
            }

            const html = await response.text();
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const FreshError = doc.querySelector('.error-banner');
            if (FreshError) {
                throw new Error(FreshError.textContent.trim());
            }

            const freshSidebar = doc.querySelector('.sidebar');
            const currentSidebar = document.querySelector('.sidebar');


            const siteId = form.closest('.site-card')?.dataset.siteId;
            const freshCard = doc.querySelector(`.site-card[data-site-id="${siteId}"]`);

            const applyUpdate = () => {
                if (freshSidebar && currentSidebar) {
                    currentSidebar.innerHTML = freshSidebar.innerHTML;
                }
                if (freshCard && currentCard) {
                    currentCard.innerHTML = freshCard.innerHTML;
                }
            };


            if (document.startViewTransition) {
                document.startViewTransition(applyUpdate);
            } else {
                applyUpdate();
            }


        } catch (error) {
            console.error('Error for changing status:', error);

            btn.classList.toggle('is-on');
            btn.setAttribute('aria-checked', !isOn);
            btn.setAttribute('aria-label', !isOn ? 'Pause monitoring' : 'Resume monitoring');
            btn.setAttribute('title', !isOn ? 'Pause monitoring' : 'Resume monitoring');
            if (statusBadge) {
                statusBadge.textContent = !isOn ? "Active" : "Paused";
                statusBadge.className = !isOn ? "status-badge status-badge--ok" : "status-badge status-badge--paused";
            }

            showToastError(error.message || 'Error occurred. Please try again later.');

        }
    });
})();
document.getElementById("add-site-form").addEventListener("submit", function(event) {
    const urlInput = document.getElementById("url");
    let value = urlInput.value.trim();

    if (value && !/^https?:\/\//i.test(value)) {
        value = "https://" + value;
        urlInput.value = value;
    }
});
