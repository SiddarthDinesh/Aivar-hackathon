const providerSelect = document.getElementById('provider');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('generate-form');
const submitButton = document.getElementById('submit-button');
const responseBox = document.getElementById('response-box');
const guardrailCard = document.getElementById('guardrail-card');
const guardrailStatus = document.getElementById('guardrail-status');
const guardrailDetail = document.getElementById('guardrail-detail');
const auditList = document.getElementById('audit-list');

function setStatusState(status) {
  const normalized = (status || '').toLowerCase();
  guardrailCard.className = 'guardrail-card neutral';

  if (normalized === 'allow' || normalized === 'allowed') {
    guardrailCard.classList.add('allow');
  } else if (normalized === 'redact' || normalized === 'warning' || normalized === 'warn') {
    guardrailCard.classList.add('warn');
  } else if (normalized === 'block' || normalized === 'blocked') {
    guardrailCard.classList.add('block');
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
  } catch (error) {
    providerSelect.innerHTML = '<option value="">Unavailable</option>';
    showError(error.message || 'Unable to load providers.');
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

  auditList.innerHTML = items
    .map(([label, value]) => `<li><strong>${label}:</strong> ${value}</li>`)
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
  submitButton.textContent = 'Generating...';
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
    guardrailStatus.textContent = `${(data.guardrail_status || 'allow').toUpperCase()}`;
    guardrailDetail.textContent = data.rule ? `Rule: ${data.rule} | Action: ${data.action || 'allow'}` : 'No policy evaluation yet.';
    renderAudit(data);
  } catch (error) {
    showError(error.message || 'Unable to contact the selected provider. Please try again.');
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Generate';
  }
});

loadProviders();
