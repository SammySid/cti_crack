export function setSidebarOpen(ui, open) {
    const sidebar = document.getElementById('sidebarNav');
    const backdrop = document.getElementById('mobileSidebarBackdrop');
    const openBtn = document.getElementById('mobileSidebarOpen');
    if (!sidebar || !backdrop) return;

    const isMobile = window.matchMedia('(max-width: 1023px)').matches;
    ui.isSidebarOpen = isMobile ? open : false;

    if (!isMobile) {
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.add('lg:translate-x-0');
        backdrop.classList.add('hidden');
        sidebar.setAttribute('aria-hidden', 'false');
        document.body.classList.remove('overflow-hidden');
        if (openBtn) openBtn.setAttribute('aria-expanded', 'false');
        return;
    }

    sidebar.classList.toggle('-translate-x-full', !ui.isSidebarOpen);
    backdrop.classList.toggle('hidden', !ui.isSidebarOpen);
    sidebar.setAttribute('aria-hidden', String(!ui.isSidebarOpen));
    document.body.classList.toggle('overflow-hidden', ui.isSidebarOpen);
    if (openBtn) openBtn.setAttribute('aria-expanded', String(ui.isSidebarOpen));
}

export function initMobileNavigation(ui) {
    const openBtn = document.getElementById('mobileSidebarOpen');
    const closeBtn = document.getElementById('mobileSidebarClose');
    const backdrop = document.getElementById('mobileSidebarBackdrop');
    const closeIfOpen = () => ui.setSidebarOpen(false);

    openBtn?.addEventListener('click', () => ui.setSidebarOpen(true));
    closeBtn?.addEventListener('click', closeIfOpen);
    backdrop?.addEventListener('click', closeIfOpen);
    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeIfOpen();
        }
    });
    window.addEventListener('resize', ui.debounce(() => {
        ui.setSidebarOpen(false);
    }, 120));
    ui.setSidebarOpen(false);
}
