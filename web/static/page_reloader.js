(function () {
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

    const start_seconds = 5;
    let secondsLeft = start_seconds;
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
})();