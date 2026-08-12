const providerSelect = document.getElementById('provider');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('generate-form');
const submitButton = document.getElementById('submit-button');
const responseBox = document.getElementById('response-box');
const guardrailCard = document.getElementById('guardrail-card');
const guardrailStatus = document.getElementById('guardrail-status');
const guardrailDetail = document.getElementById('guardrail-detail');
const auditList = document.getElementById('audit-list');
const statusIndicator = document.getElementById('status-indicator');
const themeToggle = document.getElementById('theme-toggle');

let isDark = true;

function applyTheme(dark) {
  const body = document.body;
  if (dark) {
    body.classList.add('theme-dark');
    body.classList.remove('theme-light');
    themeToggle.textContent = '🌙 Dark';
    themeToggle.setAttribute('aria-pressed', 'true');
  } else {
    body.classList.add('theme-light');
    body.classList.remove('theme-dark');
    themeToggle.textContent = '☀️ Light';
    themeToggle.setAttribute('aria-pressed', 'false');
  }
}

function loadTheme() {
  const saved = localStorage.getItem('gr_theme');
  if (saved) {
    isDark = saved === 'dark';
  } else {
    isDark = true; // default to dark
  }
  applyTheme(isDark);
}

themeToggle?.addEventListener('click', () => {
  isDark = !isDark;
  localStorage.setItem('gr_theme', isDark ? 'dark' : 'light');
  applyTheme(isDark);
});

themeToggle?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    themeToggle.click();
  }
});

function setStatusState(status) {
  const normalized = (status || '').toLowerCase();
  guardrailCard.className = 'guardrail-card neutral';

  if (normalized === 'allow' || normalized === 'allowed') {
    guardrailCard.classList.add('allow');
    guardrailStatus.textContent = '✓ ALLOWED';
  } else if (normalized === 'redact' || normalized === 'redacted' || normalized === 'warning' || normalized === 'warn') {
    guardrailCard.classList.add('warn');
    guardrailStatus.textContent = '⚠ REDACTED';
  } else if (normalized === 'block' || normalized === 'blocked') {
    guardrailCard.classList.add('block');
    guardrailStatus.textContent = '✕ BLOCKED';
  } else {
    guardrailStatus.textContent = (status || 'UNKNOWN').toUpperCase();
  }
}

async function loadProviders() {
  try {
    const response = await fetch('/providers');
    if (!response.ok) throw new Error('Unable to load providers.');
    const providers = await response.json();
    providerSelect.innerHTML = providers
      .map((provider) => `<option value="${provider}">${provider.charAt(0).toUpperCase() + provider.slice(1)}</option>`)
      .join('');
    statusIndicator && (statusIndicator.textContent = 'Providers Connected');
  } catch (error) {
    providerSelect.innerHTML = '<option value="">Unavailable</option>';
    showError(error.message || 'Unable to load providers.');
    statusIndicator && (statusIndicator.textContent = 'Unavailable');
  }
}


function showError(message) {
  responseBox.textContent = message;
  responseBox.classList.add('error');
}

function clearError() {
  responseBox.classList.remove('error');
}

function renderAudit(data) {
  const items = [
    ['Request ID', data.request_id || '—'],
    ['Provider', data.provider || '—'],
    ['Model', data.model || '—'],
    ['Timestamp', data.timestamp || '—'],
    ['Rule', data.rule || '—'],
    ['Action', data.action || '—'],
  ];

  // Render as definition list for a compact audit panel
  auditList.innerHTML = items
    .map(([label, value]) => `<div class="detail-row"><dt>${label}</dt><dd>${value}</dd></div>`)
    .join('');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearError();

  const prompt = promptInput.value.trim();
  if (!prompt) {
    showError('Please enter a prompt.');
    return;
  }

  submitButton.disabled = true;
  submitButton.classList.add('loading');
  submitButton.setAttribute('aria-busy', 'true');
  responseBox.textContent = 'Generating...';
  guardrailStatus.textContent = 'Waiting for response.';
  guardrailDetail.textContent = 'No policy evaluation yet.';
  auditList.innerHTML = '';

  try {
    const response = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: providerSelect.value, prompt }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unable to contact the selected provider.' }));
      throw new Error(errorData.detail || 'Unable to contact the selected provider.');
    }

    const data = await response.json();
    responseBox.textContent = data.response || 'No response returned.';
    setStatusState(data.guardrail_status);
    guardrailDetail.textContent = data.rule ? `Rule: ${data.rule} | Action: ${data.action || 'allow'}` : 'No policy evaluation yet.';
    renderAudit(data);
  } catch (error) {
    showError(error.message || 'Unable to contact the selected provider. Please try again.');
  } finally {
    submitButton.disabled = false;
    submitButton.classList.remove('loading');
    submitButton.removeAttribute('aria-busy');
    submitButton.textContent = '🛡 Run Guardrail Test';
  }
});

loadTheme();
loadProviders();

// Simple SPA navigation
const sections = Array.from(document.querySelectorAll('.page-section'));
const navItems = Array.from(document.querySelectorAll('.nav-item'));

function showSection(name) {
  sections.forEach((el) => {
    if (el.id === `${name}-section`) {
      el.style.display = '';
    } else {
      el.style.display = 'none';
    }
  });
  navItems.forEach((btn) => {
    if (btn.dataset && btn.dataset.section === name) {
      btn.classList.add('active');
      btn.setAttribute('aria-current', 'true');
    } else {
      btn.classList.remove('active');
      btn.setAttribute('aria-current', 'false');
    }
  });
}

document.getElementById('nav-playground')?.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('playground');
});
document.getElementById('nav-dashboard')?.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('dashboard');
  loadDashboard();
});
document.getElementById('nav-policies')?.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('policies');
});
document.getElementById('nav-audit')?.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('audit');
  loadAuditLogs();
});
document.getElementById('nav-providers')?.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('providers');
  loadProvidersPage();
});

async function loadDashboard() {
  const metricsEl = document.getElementById('dashboard-metrics');
  const chartEl = document.getElementById('dashboard-chart');
  const violationsEl = document.getElementById('dashboard-violations');
  metricsEl.innerHTML = 'Loading...';
  chartEl.innerHTML = '';
  violationsEl.innerHTML = '';
  try {
    const [summaryRes, timelineRes] = await Promise.all([fetch('/analytics/summary'), fetch('/analytics/timeline')]);
    if (!summaryRes.ok) throw new Error('Unable to load summary');
    const summary = await summaryRes.json();
    const timeline = timelineRes.ok ? await timelineRes.json() : [];

    // Metrics
    metricsEl.innerHTML = `
      <div class="metrics-row">
        <div class="metric-card"><div class="metric-title">TOTAL REQUESTS</div><div class="metric-value">${summary.total}</div></div>
        <div class="metric-card"><div class="metric-title">ALLOWED</div><div class="metric-value allowed">${summary.allowed}</div></div>
        <div class="metric-card"><div class="metric-title">REDACTED</div><div class="metric-value warn">${summary.redacted}</div></div>
        <div class="metric-card"><div class="metric-title">BLOCKED</div><div class="metric-value block">${summary.blocked}</div></div>
      </div>
    `;

    // Violations by rule
    const byRule = summary.by_rule || {};
    violationsEl.innerHTML = `
      <h4>Violations by Rule</h4>
      <ul class="violations-list">
        <li>PII: ${byRule.pii || 0}</li>
        <li>Toxicity: ${byRule.toxicity || 0}</li>
        <li>Topic: ${byRule.topic || 0}</li>
      </ul>
    `;

    // Simple timeline chart (stacked bars per time)
    if (!timeline || timeline.length === 0) {
      chartEl.innerHTML = '<div class="muted">No timeline data yet.</div>';
    } else {
      chartEl.innerHTML = '<div class="timeline-chart"></div>';
      const container = chartEl.querySelector('.timeline-chart');
      // For each bucket, create a small stacked bar
      timeline.forEach((bucket) => {
        const bar = document.createElement('div');
        bar.className = 'timeline-bar';
        const total = (bucket.allowed || 0) + (bucket.redacted || 0) + (bucket.blocked || 0);
        if (total === 0) {
          bar.style.width = '24px';
          bar.innerHTML = `<div class="bar-seg empty"></div><div class="bucket-label">${bucket.time}</div>`;
        } else {
          const a = Math.round(((bucket.allowed || 0) / total) * 100);
          const r = Math.round(((bucket.redacted || 0) / total) * 100);
          const b = 100 - a - r;
          bar.innerHTML = `
            <div class="bar-seg allowed" style="height:${a}%"></div>
            <div class="bar-seg warn" style="height:${r}%"></div>
            <div class="bar-seg block" style="height:${b}%"></div>
            <div class="bucket-label">${bucket.time}</div>
          `;
        }
        container.appendChild(bar);
      });
    }
  } catch (err) {
    metricsEl.innerHTML = `<div class="error">Unable to load dashboard: ${err.message}</div>`;
  }
}

async function loadAuditLogs() {
  const tableEl = document.getElementById('audit-table');
  tableEl.innerHTML = 'Loading...';
  try {
    const res = await fetch('/audit');
    if (!res.ok) throw new Error('Unable to load audit logs');
    const data = await res.json();
    if (!data || data.length === 0) {
      tableEl.innerHTML = '<div class="muted">No audit events yet.</div>';
      return;
    }

    const rows = data
      .map((row) => `
        <tr>
          <td>${row.timestamp || '—'}</td>
          <td>${row.provider || '—'}</td>
          <td>${row.model || '—'}</td>
          <td>${row.rule || '—'}</td>
          <td>${row.action || '—'}</td>
          <td>${row.status || '—'}</td>
          <td>${row.request_id || '—'}</td>
        </tr>
      `)
      .join('');

    tableEl.innerHTML = `<table class="audit-table"><thead><tr><th>Timestamp</th><th>Provider</th><th>Model</th><th>Rule</th><th>Action</th><th>Status</th><th>Request ID</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (err) {
    tableEl.innerHTML = `<div class="error">Unable to load audit logs: ${err.message}</div>`;
  }
}

async function loadProvidersPage() {
  const el = document.getElementById('providers-list');
  el.innerHTML = 'Loading...';
  try {
    const res = await fetch('/providers');
    if (!res.ok) throw new Error('Unable to load providers');
    const list = await res.json();
    el.innerHTML = `<ul class="providers-list">${list.map((p) => `<li>${p}</li>`).join('')}</ul>`;
  } catch (err) {
    el.innerHTML = `<div class="error">Unable to load providers: ${err.message}</div>`;
  }
}

// Start on playground
showSection('playground');
