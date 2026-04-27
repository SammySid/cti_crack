export function switchTab(ui, tabId) {
    ui.activeTab = tabId;
    const thermalTab    = document.getElementById('tabThermal');
    const psychroTab    = document.getElementById('tabPsychro');
    const predictionTab = document.getElementById('tabPrediction');
    const filterTab     = document.getElementById('tabFilter');
    const reportTab     = document.getElementById('tabReport');
    const thermalPanel     = document.getElementById('thermalTabPanel');
    const psychroPanel     = document.getElementById('psychroTabPanel');
    const filterPanel      = document.getElementById('filterTabPanel');
    const predictionPanel  = document.getElementById('predictionTabPanel');
    const reportPanel      = document.getElementById('reportTabPanel');

    const setTabActive = (tabEl, active) => {
        if (!tabEl) return;
        tabEl.classList.toggle('bg-cyan-500/20',   active);
        tabEl.classList.toggle('text-cyan-300',    active);
        tabEl.classList.toggle('border-cyan-500/30', active);
        tabEl.classList.toggle('text-slate-300',   !active);
        tabEl.classList.toggle('border-white/10',  !active);
        tabEl.classList.toggle('hover:bg-white/5', !active);
    };

    setTabActive(thermalTab,    tabId === 'thermal');
    setTabActive(predictionTab, tabId === 'prediction');
    setTabActive(psychroTab,    tabId === 'psychro');
    setTabActive(filterTab,     tabId === 'filter');
    setTabActive(reportTab,     tabId === 'report');

    thermalPanel?.classList.toggle('hidden',    tabId !== 'thermal');
    psychroPanel?.classList.toggle('hidden',    tabId !== 'psychro');
    filterPanel?.classList.toggle('hidden',     tabId !== 'filter');
    predictionPanel?.classList.toggle('hidden', tabId !== 'prediction');
    reportPanel?.classList.toggle('hidden',     tabId !== 'report');

    if (tabId === 'psychro') ui.calculatePsychrometrics();
}
