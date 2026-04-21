const API = '';

function app() {
  return {
    API,
    page: 'dashboard',
    statusMsg: '',
    statusType: 'info',
    _statusTimer: null,

    // Nav
    nav: [
      { id: 'dashboard', label: 'Dashboard',  icon: 'fa-solid fa-house' },
      { id: 'setup',     label: 'Brand Setup', icon: 'fa-solid fa-building' },
      { id: 'prompts',   label: 'Prompts',     icon: 'fa-solid fa-list-check' },
      { id: 'runs',      label: 'Runs',        icon: 'fa-solid fa-play' },
      { id: 'results',   label: 'Results',     icon: 'fa-solid fa-chart-bar' },
      { id: 'settings',  label: 'Settings',    icon: 'fa-solid fa-gear' },
    ],
    get navLabel() {
      return { dashboard:'Dashboard', setup:'Brand Setup', prompts:'Prompts', runs:'Tracking Runs', results:'Results', settings:'Settings' }[this.page] || '';
    },
    get navSub() {
      return {
        dashboard: 'Overview of your tracking activity',
        setup: 'Configure your brand and up to 4 competitors',
        prompts: 'Upload and manage your tracking prompts',
        runs: 'Start new runs and monitor progress',
        results: 'Analyze mentions, citations, and sentiment',
        settings: 'API keys and mode configuration',
      }[this.page] || '';
    },

    // Dashboard
    dashboardData: null,
    dashStats: [],
    recentRuns: [],
    activeRunCount: 0,

    // Setup
    primaryBrand: { name: '', url: '' },
    competitors: [{ name: '', url: '' }],
    savingBrands: false,

    // Prompts
    prompts: [],
    uploading: false,

    // Runs
    runs: [],
    newRun: { name: '', platforms: [] },
    startingRun: false,
    _pollTimer: null,
    platformOptions: [
      { id: 'chatgpt',    label: 'ChatGPT',          icon: 'fa-brands fa-openai',  color: '#10a37f', note: '' },
      { id: 'gemini',     label: 'Gemini',            icon: 'fa-solid fa-g',        color: '#4285f4', note: '' },
      { id: 'perplexity', label: 'Perplexity',        icon: 'fa-solid fa-bolt',     color: '#7c3aed', note: '' },
      { id: 'google_aio', label: 'Google AI Overview',icon: 'fa-brands fa-google',  color: '#ea4335', note: 'Local only' },
      { id: 'google_aim', label: 'Google AI Mode',    icon: 'fa-brands fa-google',  color: '#34a853', note: 'Local only' },
    ],

    // Results
    activeRunId: null,
    activeRunName: '',
    activeRunDate: '',
    activePlatforms: [],
    resultTab: 'overview',
    resultTabs: [
      { id: 'overview',  label: 'Overview',    icon: 'fa-solid fa-chart-pie' },
      { id: 'by-prompt', label: 'By Prompt',   icon: 'fa-solid fa-table' },
      { id: 'citations', label: 'Citations',   icon: 'fa-solid fa-link' },
      { id: 'sentiment', label: 'Sentiment',   icon: 'fa-solid fa-face-smile' },
    ],
    loadingTab: false,
    overviewData: null,
    byPromptData: null,
    byPromptBrands: [],
    byPromptRows: [],
    promptFilter: '',
    citationsData: null,
    expandedCitations: [],
    sentimentData: null,
    sentimentBrands: [],
    _charts: {},

    // Settings
    settings: { api_mode: 'byok', openai_key: '', gemini_key: '', perplexity_key: '', platform_keys_configured: false },
    savingSettings: false,

    // ── Init ─────────────────────────────────────────────────────────────────
    async init() {
      await this.loadDashboard();
      this.$watch('promptFilter', () => this.buildByPromptRows());
    },

    // ── Helpers ───────────────────────────────────────────────────────────────
    notify(msg, type = 'info', ms = 3500) {
      this.statusMsg = msg; this.statusType = type;
      clearTimeout(this._statusTimer);
      this._statusTimer = setTimeout(() => this.statusMsg = '', ms);
    },
    async api(path, opts = {}) {
      const url = API + path;
      const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || res.statusText); }
      return res.json();
    },
    formatDate(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
    },
    platformLabel(p) {
      return { chatgpt:'ChatGPT', gemini:'Gemini', perplexity:'Perplexity', google_aio:'AI Overview', google_aim:'AI Mode' }[p] || p;
    },
    platformBadge(p) {
      return {
        chatgpt:    'bg-emerald-100 text-emerald-700',
        gemini:     'bg-blue-100 text-blue-700',
        perplexity: 'bg-purple-100 text-purple-700',
        google_aio: 'bg-red-100 text-red-700',
        google_aim: 'bg-green-100 text-green-700',
      }[p] || 'bg-gray-100 text-gray-600';
    },
    statusBadge(s) {
      return { pending:'bg-gray-100 text-gray-600', running:'bg-yellow-100 text-yellow-700', completed:'bg-green-100 text-green-700', failed:'bg-red-100 text-red-700' }[s] || 'bg-gray-100 text-gray-600';
    },
    sentimentScoreColor(score) {
      if (score === undefined || score === null) return 'text-gray-600';
      return score > 0.05 ? 'text-green-600' : score < -0.05 ? 'text-red-600' : 'text-gray-600';
    },
    destroyChart(id) {
      if (this._charts[id]) { this._charts[id].destroy(); delete this._charts[id]; }
    },

    // ── Dashboard ─────────────────────────────────────────────────────────────
    async loadDashboard() {
      try {
        const [runsRes, brandsRes, promptsRes] = await Promise.all([
          this.api('/runs'),
          this.api('/brands'),
          this.api('/prompts'),
        ]);
        this.recentRuns = runsRes.slice(0, 5);
        this.activeRunCount = runsRes.filter(r => r.status === 'running').length;
        const completed = runsRes.filter(r => r.status === 'completed').length;
        this.dashStats = [
          { label: 'Brands Tracked', value: brandsRes.length, icon: 'fa-building', color: 'bg-blue-100 text-blue-600' },
          { label: 'Prompts',         value: promptsRes.length, icon: 'fa-list-check', color: 'bg-purple-100 text-purple-600' },
          { label: 'Total Runs',      value: runsRes.length,   icon: 'fa-play',       color: 'bg-amber-100 text-amber-600' },
          { label: 'Completed',       value: completed,         icon: 'fa-circle-check', color: 'bg-green-100 text-green-600' },
        ];
        this.dashboardData = brandsRes.length > 0 || runsRes.length > 0;
      } catch (e) {
        this.notify('Cannot connect to backend. Is the server running?', 'error', 8000);
      }
    },

    // ── Setup ─────────────────────────────────────────────────────────────────
    async loadBrands() {
      try {
        const brands = await this.api('/brands');
        const primary = brands.find(b => b.is_primary);
        if (primary) this.primaryBrand = { name: primary.name, url: primary.url };
        this.competitors = brands.filter(b => !b.is_primary).map(b => ({ name: b.name, url: b.url }));
        if (this.competitors.length === 0) this.competitors = [{ name: '', url: '' }];
      } catch (e) { /* silent */ }
    },
    async saveBrands() {
      if (!this.primaryBrand.name || !this.primaryBrand.url) {
        this.notify('Primary brand name and URL are required.', 'error'); return;
      }
      this.savingBrands = true;
      try {
        const payload = [
          { name: this.primaryBrand.name, url: this.primaryBrand.url, is_primary: true },
          ...this.competitors.filter(c => c.name && c.url).map(c => ({ name: c.name, url: c.url, is_primary: false })),
        ];
        await this.api('/brands', { method: 'POST', body: JSON.stringify(payload) });
        this.notify(`${payload.length} brand(s) saved.`, 'success');
      } catch (e) { this.notify(e.message, 'error'); }
      finally { this.savingBrands = false; }
    },

    // ── Prompts ────────────────────────────────────────────────────────────────
    async loadPrompts() {
      try { this.prompts = await this.api('/prompts'); } catch (e) { /* silent */ }
    },
    async uploadCSV(event) {
      const file = event.target.files[0]; if (!file) return;
      await this._uploadFile(file);
      event.target.value = '';
    },
    async handleDrop(event) {
      const file = event.dataTransfer.files[0]; if (!file) return;
      await this._uploadFile(file);
    },
    async _uploadFile(file) {
      this.uploading = true;
      try {
        const fd = new FormData(); fd.append('file', file);
        const res = await fetch(API + '/prompts/upload', { method: 'POST', body: fd });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Upload failed'); }
        const data = await res.json();
        this.notify(`${data.saved} prompts loaded.`, 'success');
        await this.loadPrompts();
      } catch (e) { this.notify(e.message, 'error'); }
      finally { this.uploading = false; }
    },
    async clearPrompts() {
      if (!confirm('Clear all prompts?')) return;
      await this.api('/prompts', { method: 'DELETE' });
      this.prompts = [];
      this.notify('Prompts cleared.', 'success');
    },

    // ── Runs ──────────────────────────────────────────────────────────────────
    async loadRuns() {
      try { this.runs = await this.api('/runs'); } catch (e) { /* silent */ }
    },

    async startRun() {
      if (this.newRun.platforms.length === 0) return;
      this.startingRun = true;
      try {
        const name = this.newRun.name || `Run ${new Date().toLocaleString('en-IN', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })}`;

        // Step 1: Create run document (fast — returns run_id immediately)
        const res = await this.api('/runs', { method: 'POST', body: JSON.stringify({ name, platforms: this.newRun.platforms }) });
        this.newRun.name = '';
        await this.loadRuns();

        // Step 2: Start polling for progress
        this._startPolling(res.run_id);
        this.notify(`Run started — tracking in progress…`, 'info', 120000);

        // Step 3: Fire-and-forget the execute call (long-running, up to 5 min on Vercel Pro)
        this.api(`/runs/${res.run_id}/execute`, { method: 'POST' })
          .then(() => this.notify('Run completed!', 'success'))
          .catch(e  => this.notify(`Run error: ${e.message}`, 'error'));

      } catch (e) { this.notify(e.message, 'error'); }
      finally { this.startingRun = false; }
    },

    _startPolling(runId) {
      clearInterval(this._pollTimer);
      this._pollTimer = setInterval(async () => {
        try {
          const run = await this.api(`/runs/${runId}`);
          const idx = this.runs.findIndex(r => r.id === runId);
          if (idx >= 0) this.runs[idx] = run;
          else this.runs.unshift(run);
          this.activeRunCount = this.runs.filter(r => r.status === 'running').length;
          if (run.status === 'completed' || run.status === 'failed') {
            clearInterval(this._pollTimer);
          }
        } catch (e) { clearInterval(this._pollTimer); }
      }, 4000);
    },

    async deleteRun(id) {
      if (!confirm('Delete this run and all its results?')) return;
      await this.api(`/runs/${id}`, { method: 'DELETE' });
      this.runs = this.runs.filter(r => r.id !== id);
      this.notify('Run deleted.', 'success');
    },
    openRun(runId) {
      const run = this.runs.find(r => r.id === runId) || this.recentRuns.find(r => r.id === runId);
      this.activeRunId = runId;
      this.activeRunName = run?.name || `Run #${runId}`;
      this.activeRunDate = run ? this.formatDate(run.created_at) : '';
      this.activePlatforms = run?.platforms || [];
      this.resultTab = 'overview';
      this.overviewData = null;
      this.byPromptData = null;
      this.citationsData = null;
      this.sentimentData = null;
      this.page = 'results';
      setTimeout(() => this.loadTabData('overview'), 100);
    },

    // ── Results ───────────────────────────────────────────────────────────────
    async loadTabData(tab) {
      if (!this.activeRunId) return;
      this.loadingTab = true;
      try {
        if (tab === 'overview') await this._loadOverview();
        else if (tab === 'by-prompt') await this._loadByPrompt();
        else if (tab === 'citations') await this._loadCitations();
        else if (tab === 'sentiment') await this._loadSentiment();
      } catch (e) { this.notify(e.message, 'error'); }
      finally { this.loadingTab = false; }
    },

    async _loadOverview() {
      this.overviewData = await this.api(`/analytics/${this.activeRunId}/overview`);
      await this.$nextTick();
      this._renderOverviewCharts();
    },
    _renderOverviewCharts() {
      const brands = this.overviewData.brands.map(b => b.name);
      const mentions = brands.map(b => this.overviewData.totals[b]?.mentions ?? 0);
      const citations = brands.map(b => this.overviewData.totals[b]?.citations ?? 0);
      const colors = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444'];

      const chartOpts = { responsive: true, animation: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } };

      this.destroyChart('mentionsChart');
      const mc = document.getElementById('mentionsChart');
      if (mc) this._charts['mentionsChart'] = new Chart(mc, {
        type: 'bar',
        data: { labels: brands, datasets: [{ label: 'Mentions', data: mentions, backgroundColor: colors.slice(0, brands.length), borderRadius: 6, borderSkipped: false }] },
        options: chartOpts
      });

      this.destroyChart('citationsChart');
      const cc = document.getElementById('citationsChart');
      if (cc) this._charts['citationsChart'] = new Chart(cc, {
        type: 'bar',
        data: { labels: brands, datasets: [{ label: 'Citations', data: citations, backgroundColor: colors.slice(0, brands.length), borderRadius: 6, borderSkipped: false }] },
        options: chartOpts
      });
    },

    async _loadByPrompt() {
      this.byPromptData = await this.api(`/analytics/${this.activeRunId}/by-prompt`);
      const brandSet = new Set();
      for (const item of this.byPromptData.prompts) {
        for (const plat of Object.values(item.platforms)) {
          for (const b of Object.keys(plat)) brandSet.add(b);
        }
      }
      this.byPromptBrands = [...brandSet];
      this.buildByPromptRows();
    },
    buildByPromptRows() {
      if (!this.byPromptData) return;
      const rows = [];
      let idx = 1;
      for (const item of this.byPromptData.prompts) {
        const platforms = this.promptFilter ? { [this.promptFilter]: item.platforms[this.promptFilter] || {} } : item.platforms;
        for (const [platform, brandMentions] of Object.entries(platforms)) {
          rows.push({ idx, prompt: item.text, platform, mentions: brandMentions || {} });
        }
        idx++;
      }
      this.byPromptRows = rows;
    },

    async _loadCitations() {
      this.citationsData = await this.api(`/analytics/${this.activeRunId}/citations`);
      this.expandedCitations = [];
    },
    toggleCitation(id) {
      const i = this.expandedCitations.indexOf(id);
      if (i >= 0) this.expandedCitations.splice(i, 1);
      else this.expandedCitations.push(id);
    },

    async _loadSentiment() {
      this.sentimentData = await this.api(`/analytics/${this.activeRunId}/sentiment`);
      this.sentimentBrands = Object.keys(this.sentimentData.counts);
      await this.$nextTick();
      this._renderSentimentChart();
    },
    _renderSentimentChart() {
      const brands = this.sentimentBrands;
      const pos = brands.map(b => this.sentimentData.counts[b]?.positive ?? 0);
      const neu = brands.map(b => this.sentimentData.counts[b]?.neutral ?? 0);
      const neg = brands.map(b => this.sentimentData.counts[b]?.negative ?? 0);

      this.destroyChart('sentimentChart');
      const sc = document.getElementById('sentimentChart');
      if (sc) this._charts['sentimentChart'] = new Chart(sc, {
        type: 'bar',
        data: {
          labels: brands,
          datasets: [
            { label: 'Positive', data: pos, backgroundColor: '#10b981', borderRadius: 4, borderSkipped: false },
            { label: 'Neutral',  data: neu, backgroundColor: '#9ca3af', borderRadius: 4, borderSkipped: false },
            { label: 'Negative', data: neg, backgroundColor: '#ef4444', borderRadius: 4, borderSkipped: false },
          ]
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'top' } },
          scales: { x: { stacked: false }, y: { beginAtZero: true, stacked: false, ticks: { stepSize: 1 } } }
        }
      });
    },

    // ── Settings ──────────────────────────────────────────────────────────────
    async loadSettings() {
      try { this.settings = { ...this.settings, ...await this.api('/settings') }; } catch (e) { /* silent */ }
    },
    async saveSettings() {
      this.savingSettings = true;
      try {
        await this.api('/settings', { method: 'POST', body: JSON.stringify(this.settings) });
        this.notify('Settings saved.', 'success');
      } catch (e) { this.notify(e.message, 'error'); }
      finally { this.savingSettings = false; }
    },
  };
}
