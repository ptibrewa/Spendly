// main.js — students will add JavaScript here as features are built

(function initVideoModal() {
    const modal = document.getElementById('videoModal');
    if (!modal) return;

    const iframe = document.getElementById('videoModalIframe');
    const openButtons = document.querySelectorAll('[data-open-video]');
    const closeTargets = modal.querySelectorAll('[data-close-video]');

    function openModal() {
        iframe.src = iframe.dataset.src;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        iframe.src = '';
        document.body.style.overflow = '';
    }

    openButtons.forEach((btn) => btn.addEventListener('click', openModal));
    closeTargets.forEach((el) => el.addEventListener('click', closeModal));

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('is-open')) {
            closeModal();
        }
    });
})();

(function initRangeToggle() {
    const form = document.querySelector('[data-range-toggle]');
    if (!form) return;

    const select = form.querySelector('[data-range-select]');
    const custom = form.querySelector('[data-range-custom]');
    if (!select || !custom) return;

    function sync() {
        if (select.value === 'custom') {
            custom.removeAttribute('hidden');
        } else {
            custom.setAttribute('hidden', '');
        }
    }

    select.addEventListener('change', sync);
    sync();
})();
