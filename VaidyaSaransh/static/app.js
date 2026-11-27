const form = document.querySelector('#upload-form');
const fileInput = document.querySelector('#report-file');
const dropZone = document.querySelector('#drop-zone');
const selectedFile = document.querySelector('#selected-file');
const fileName = document.querySelector('#file-name');
const removeFileButton = document.querySelector('#remove-file');
const submitButton = document.querySelector('#submit-button');
const uploadError = document.querySelector('#upload-error');
const processing = document.querySelector('#processing');
const processingMessage = document.querySelector('#processing-message');
const results = document.querySelector('#results');
const MAX_FILE_SIZE = 15 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(['pdf', 'png', 'jpg', 'jpeg']);
let previewUrl = null;

fileInput.addEventListener('change', () => selectFile(fileInput.files[0]));
removeFileButton.addEventListener('click', clearFile);
document.querySelector('#another-report').addEventListener('click', () => {
  results.hidden = true;
  clearFile();
  fileInput.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

for (const eventName of ['dragenter', 'dragover']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add('is-dragging');
  });
}
for (const eventName of ['dragleave', 'drop']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('is-dragging');
  });
}
dropZone.addEventListener('drop', (event) => {
  const files = event.dataTransfer.files;
  if (!files.length) return;
  fileInput.files = files;
  selectFile(files[0]);
});

function selectFile(file) {
  uploadError.hidden = true;
  if (!file) return;
  const extension = file.name.split('.').pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(extension)) {
    showError('This file type is not supported. Please upload a PDF, JPG, JPEG, or PNG.');
    clearFile();
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    showError('This report exceeds the maximum supported file size of 15 MB.');
    clearFile();
    return;
  }
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  fileName.textContent = `${file.name} · ${formatBytes(file.size)}`;
  selectedFile.hidden = false;
  document.querySelector('#report-preview').hidden = false;
  const imagePreview = document.querySelector('#image-preview');
  const pdfPreview = document.querySelector('#pdf-preview');
  imagePreview.hidden = extension === 'pdf';
  pdfPreview.hidden = extension !== 'pdf';
  if (extension === 'pdf') {
    pdfPreview.href = previewUrl;
  } else {
    imagePreview.src = previewUrl;
  }
  dropZone.hidden = true;
  submitButton.disabled = false;
}

function clearFile() {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  fileInput.value = '';
  selectedFile.hidden = true;
  document.querySelector('#report-preview').hidden = true;
  document.querySelector('#image-preview').removeAttribute('src');
  document.querySelector('#pdf-preview').removeAttribute('href');
  dropZone.hidden = false;
  submitButton.disabled = true;
}

window.addEventListener('pagehide', () => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});

function formatBytes(size) {
  return size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function showError(message) {
  uploadError.textContent = message;
  uploadError.hidden = false;
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) return showError('Choose a medical report to upload.');
  uploadError.hidden = true;
  results.hidden = true;
  processing.hidden = false;
  processing.setAttribute('aria-busy', 'true');
  processingMessage.textContent = 'Uploading your report…';
  submitButton.disabled = true;

  const body = new FormData();
  body.append('report', file, file.name);
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/vaidya-saransh/analyze');
  xhr.upload.addEventListener('load', () => {
    processingMessage.textContent = 'Reading the report and preparing its explanation…';
  });
  xhr.addEventListener('load', () => {
    let response;
    try {
      response = JSON.parse(xhr.responseText);
    } catch {
      showError('The report could not be processed. Please try again.');
      return finishProcessing();
    }
    if (xhr.status < 200 || xhr.status >= 300 || !response.success) {
      showError(response.error?.message || 'The report could not be processed. Please try again.');
      return finishProcessing();
    }
    renderResults(response.data);
    results.hidden = false;
    finishProcessing();
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  xhr.addEventListener('error', () => {
    showError('Report simplification is temporarily unavailable. Please check your connection and try again.');
    finishProcessing();
  });
  xhr.send(body);
});

function finishProcessing() {
  processing.hidden = true;
  processing.setAttribute('aria-busy', 'false');
  submitButton.disabled = false;
}

function addText(parent, tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text || 'Not provided in the report.';
  parent.append(element);
  return element;
}

function renderResults(data) {
  renderOverview(data.reportInfo);
  document.querySelector('#overall-summary').textContent = data.overallSummary || 'The report did not include an overall summary.';
  renderFindings(data.keyFindings);
  renderObservations(data.importantObservations);
  renderTerms(data.medicalTerms);
  renderList('#doctor-questions', data.questionsForDoctor, 'No report-specific questions were generated.');
  renderList('#limitations', data.limitations, 'No additional extraction limitations were reported.');
}

function renderOverview(info) {
  const overview = document.querySelector('#overview');
  overview.replaceChildren();
  for (const [label, value] of [
    ['Report type', info.reportType],
    ['Report date', info.date],
    ['Patient information', info.patientInfo],
  ]) {
    const item = document.createElement('div');
    item.className = 'overview-item';
    addText(item, 'span', 'overview-label', label);
    addText(item, 'span', 'overview-value', value);
    overview.append(item);
  }
}

function renderFindings(findings) {
  const container = document.querySelector('#key-findings');
  container.replaceChildren();
  if (!findings.length) return addText(container, 'p', 'empty-section', 'No individual parameters were identified in the report.');
  findings.forEach((finding) => {
    const card = document.createElement('article');
    card.className = 'finding-card';
    const heading = document.createElement('div');
    heading.className = 'finding-heading';
    addText(heading, 'h4', 'finding-name', finding.parameter);
    const status = addText(heading, 'span', 'finding-status', statusLabel(finding.status));
    status.dataset.status = finding.status;
    card.append(heading);
    addText(card, 'p', 'finding-value', [finding.value, finding.unit].filter(Boolean).join(' '));
    addText(card, 'p', 'finding-range', `Reference range: ${finding.referenceRange || 'Not provided'}`);
    addText(card, 'p', 'finding-explanation', finding.simpleExplanation);
    container.append(card);
  });
}

function statusLabel(status) {
  return ({ normal: 'Within range', high: 'High', low: 'Low', abnormal: 'Abnormal', unclear: 'Unclear' })[status] || 'Unclear';
}

function renderObservations(observations) {
  const container = document.querySelector('#observations');
  container.replaceChildren();
  if (!observations.length) return addText(container, 'p', 'empty-section', 'No additional observations were identified.');
  observations.forEach((observation) => {
    const card = document.createElement('article');
    card.className = 'observation-card';
    addText(card, 'h4', '', observation.title);
    addText(card, 'p', 'observation-text', `Original finding: ${observation.originalFinding || 'Not provided'}`);
    addText(card, 'p', 'observation-text', `Simple explanation: ${observation.simpleExplanation || 'Not available'}`);
    addText(card, 'p', 'observation-text', `General significance: ${observation.significance || 'Not stated'}`);
    container.append(card);
  });
}

function renderTerms(terms) {
  const container = document.querySelector('#medical-terms');
  container.replaceChildren();
  if (!terms.length) return addText(container, 'p', 'empty-section', 'No medical terms needed additional explanation.');
  terms.forEach((term) => {
    const card = document.createElement('article');
    card.className = 'term-card';
    addText(card, 'h4', '', term.term);
    addText(card, 'p', 'term-meaning', term.meaning);
    container.append(card);
  });
}

function renderList(selector, values, emptyMessage) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  if (!values.length) return addText(list, 'li', '', emptyMessage);
  values.forEach((value) => addText(list, 'li', '', value));
}