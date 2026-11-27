const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const imageInput = document.querySelector('#image-input');
const preview = document.querySelector('#image-preview');
const previewImage = document.querySelector('#preview-image');
const sendButton = document.querySelector('#send-button');
const thinking = document.querySelector('#thinking');
const errorBox = document.querySelector('#chat-error');
const conversation = document.querySelector('#conversation');
let conversationId = '';
let selectedImage = null;
let previewUrl = null;

document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => { input.value = button.dataset.prompt; input.focus(); }));
imageInput.addEventListener('change', () => selectImage(imageInput.files[0]));
document.querySelector('#remove-image').addEventListener('click', clearImage);
input.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });

function selectImage(file) {
  errorBox.hidden = true;
  if (!file) return;
  const allowed = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowed.includes(file.type)) return showError('This image type is not supported. Please upload a JPG, PNG, or WEBP image.');
  if (file.size > 8 * 1024 * 1024) return showError('This image exceeds the maximum supported size of 8 MB.');
  selectedImage = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  previewImage.src = previewUrl;
  preview.hidden = false;
}

function clearImage() { selectedImage = null; imageInput.value = ''; preview.hidden = true; previewImage.removeAttribute('src'); if (previewUrl) URL.revokeObjectURL(previewUrl); previewUrl = null; }
function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message && !selectedImage) return showError('Write a question or attach an image first.');
  errorBox.hidden = true; sendButton.disabled = true; thinking.hidden = false;
  const formData = new FormData(); formData.append('message', message); formData.append('conversationId', conversationId); if (selectedImage) formData.append('image', selectedImage, selectedImage.name);
  appendMessage('user', message || 'Image attached', selectedImage ? previewUrl : null);
  input.value = '';
  try {
    const response = await fetch('/api/vaidya-sathi/chat', { method: 'POST', body: formData });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error?.message || 'The assistant could not respond.');
    }
    if (response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.json();
      if (!data.success) throw new Error(data.error?.message || 'The assistant could not respond.');
      conversationId = data.conversationId; appendMessage('assistant', data.message.content); clearImage();
    } else {
      await readAssistantStream(response);
      clearImage();
    }
  } catch (error) { showError(error.message || 'The assistant is temporarily unavailable.'); }
  finally { sendButton.disabled = false; thinking.hidden = true; input.focus(); }
});

async function readAssistantStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let assistantMessage = null;
  let assistantContent = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      if (event.type === 'chunk') {
        if (!assistantMessage) {
          assistantMessage = document.createElement('div');
          assistantMessage.className = 'message assistant-message';
          const label = document.createElement('span');
          label.className = 'message-label';
          label.textContent = 'VAIDYASATHI';
          assistantContent = document.createElement('p');
          assistantMessage.append(label, assistantContent);
          conversation.append(assistantMessage);
        }
        assistantContent.textContent += event.content;
        conversation.scrollTop = conversation.scrollHeight;
      } else if (event.type === 'done') {
        conversationId = event.conversationId;
      } else if (event.type === 'error') {
        throw new Error(event.message || 'The assistant could not respond.');
      }
    }
    if (done) break;
  }
}

function appendMessage(role, content, imageUrl) {
  const item = document.createElement('div'); item.className = `message ${role}-message`;
  const label = document.createElement('span'); label.className = 'message-label'; label.textContent = role === 'assistant' ? 'VAIDYASATHI' : 'YOU'; item.append(label);
  if (imageUrl) { const image = document.createElement('img'); image.className = 'message-image'; image.src = imageUrl; image.alt = 'Attached health image'; item.append(image); }
  if (content) { const paragraph = document.createElement('p'); paragraph.textContent = content; item.append(paragraph); }
  conversation.append(item); conversation.scrollTop = conversation.scrollHeight;
}