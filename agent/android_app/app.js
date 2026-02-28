// --- Конфигурация и Состояние ---
let apiUrl = localStorage.getItem('jarvis_api_url') || 'http://localhost:8080';
let chatId = localStorage.getItem('jarvis_chat_id') || 'android_user';

let isGenerating = false;
let currentEventSource = null;
let currentStreamDiv = null;

let selectedFile = null;

// Аудио запись
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingStartTime = 0;
let isRecording = false;

// --- Элементы UI ---
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');
const voiceBtn = document.getElementById('voice-btn');
const attachBtn = document.getElementById('attach-btn');
const fileInput = document.getElementById('file-input');
const attachmentPreview = document.getElementById('attachment-preview');
const attachmentName = document.getElementById('attachment-name');
const removeAttachmentBtn = document.getElementById('remove-attachment');

// Настройки
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('close-settings');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const clearMemoryBtn = document.getElementById('clear-memory-btn');
const apiUrlInput = document.getElementById('api-url');
const chatIdInput = document.getElementById('chat-id');

// Запись голоса
const recordingOverlay = document.getElementById('recording-overlay');
const recordingTime = document.getElementById('recording-time');

// Инициализация
apiUrlInput.value = apiUrl;
chatIdInput.value = chatId;
messageInput.addEventListener('input', autoResizeInput);

// Вибрация (Haptic Feedback)
function vibrate(pattern = 50) {
    if (navigator.vibrate) {
        navigator.vibrate(pattern);
    }
}

// --- Обработчики Настроек ---
settingsBtn.onclick = () => {
    vibrate(10);
    settingsModal.classList.remove('hidden');
};
closeSettingsBtn.onclick = () => {
    vibrate(10);
    settingsModal.classList.add('hidden');
};
saveSettingsBtn.onclick = () => {
    apiUrl = apiUrlInput.value.trim().replace(/\/$/, ""); // убираем слэш на конце
    chatId = chatIdInput.value.trim();
    localStorage.setItem('jarvis_api_url', apiUrl);
    localStorage.setItem('jarvis_chat_id', chatId);
    settingsModal.classList.add('hidden');
    vibrate([20, 50, 20]);
};
clearMemoryBtn.onclick = async () => {
    vibrate(50);
    try {
        const res = await fetch(`${apiUrl}/clear`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });
        if (res.ok) {
            chatContainer.innerHTML = '';
            vibrate([50, 50, 50]);
            addSystemMessage("Память успешно очищена.");
            settingsModal.classList.add('hidden');
        }
    } catch (e) {
        alert("Ошибка при очистке памяти: " + e.message);
    }
};

// --- Ввод текста и Файлов ---
function autoResizeInput() {
    messageInput.style.height = 'auto';
    messageInput.style.height = (messageInput.scrollHeight) + 'px';

    if (messageInput.value.trim() !== '' || selectedFile) {
        sendBtn.classList.remove('hidden');
        voiceBtn.classList.add('hidden');
    } else {
        sendBtn.classList.add('hidden');
        voiceBtn.classList.remove('hidden');
    }
}

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

attachBtn.onclick = () => {
    vibrate(10);
    fileInput.click();
};

fileInput.onchange = (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        attachmentName.textContent = selectedFile.name;
        attachmentPreview.classList.remove('hidden');
        autoResizeInput();
        vibrate(20);
    }
};

removeAttachmentBtn.onclick = () => {
    selectedFile = null;
    fileInput.value = '';
    attachmentPreview.classList.add('hidden');
    autoResizeInput();
    vibrate(10);
};


// --- Работа с API (Отправка и SSE) ---

function setGeneratingState(generating) {
    isGenerating = generating;
    if (generating) {
        sendBtn.classList.add('hidden');
        voiceBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
    } else {
        stopBtn.classList.add('hidden');
        autoResizeInput();
    }
}

async function sendMessage(fileOverride = null, messageOverride = null) {
    if (isGenerating) return;

    const text = messageOverride !== null ? messageOverride : messageInput.value.trim();
    const file = fileOverride || selectedFile;

    if (!text && !file) return;

    vibrate(20);

    // Добавляем сообщение пользователя в UI
    if (text) addUserMessage(text);
    if (file && !fileOverride) { // если не голос
        addUserMessage(`[Прикреплен файл: ${file.name}]`);
    } else if (fileOverride) {
        addUserMessage(`[Голосовое сообщение]`);
    }

    messageInput.value = '';
    messageInput.style.height = 'auto';
    removeAttachmentBtn.click(); // очистить файл

    setGeneratingState(true);

    // Подготовка тела запроса
    let fetchOptions = {
        method: 'POST'
    };

    if (file) {
        const formData = new FormData();
        formData.append('chat_id', chatId);
        formData.append('file', file);
        if (text) formData.append('caption', text);
        fetchOptions.body = formData;
    } else {
        fetchOptions.headers = { 'Content-Type': 'application/json' };
        fetchOptions.body = JSON.stringify({ chat_id: chatId, message: text });
    }

    // Обработка SSE через Fetch Reader
    try {
        const response = await fetch(`${apiUrl}/chat`, fetchOptions);

        if (!response.ok) {
            throw new Error(`Ошибка сети: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        let agentMessageDiv = createAgentMessageContainer();
        let planContainer = null;
        let markdownContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Обработка строк SSE (разделитель \n\n)
            let parts = buffer.split('\n\n');
            buffer = parts.pop(); // Последняя часть может быть неполной

            for (let part of parts) {
                if (part.startsWith('data: ')) {
                    let jsonStr = part.substring(6);
                    try {
                        let data = JSON.parse(jsonStr);
                        handleAgentEvent(data, agentMessageDiv);
                    } catch (e) {
                        console.error("Ошибка парсинга SSE", e, jsonStr);
                    }
                }
            }
        }
    } catch (error) {
        console.error("Fetch Error:", error);
        addSystemMessage("Ошибка подключения к серверу: " + error.message, true);
    } finally {
        setGeneratingState(false);
        vibrate([20, 20]);
    }
}

stopBtn.onclick = async () => {
    vibrate(30);
    try {
        await fetch(`${apiUrl}/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });
    } catch (e) {
        console.error("Ошибка при остановке", e);
    }
    setGeneratingState(false);
};


// --- Отрисовка UI сообщений ---

function addUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
        <div class="content">${escapeHtml(text)}</div>
    `;
    chatContainer.appendChild(div);
    scrollToBottom();
}

function addSystemMessage(text, isError = false) {
    const div = document.createElement('div');
    div.className = 'message system-message';
    div.innerHTML = `
        <div class="avatar"><span class="material-icons-round">smart_toy</span></div>
        <div class="content" ${isError ? 'style="color: var(--error-color)"' : ''}>${escapeHtml(text)}</div>
    `;
    chatContainer.appendChild(div);
    scrollToBottom();
}

function createAgentMessageContainer() {
    const div = document.createElement('div');
    div.className = 'message system-message agent-response';
    div.innerHTML = `
        <div class="avatar"><span class="material-icons-round">smart_toy</span></div>
        <div class="content">
            <div class="status-zone"></div>
            <div class="plan-zone"></div>
            <div class="markdown-zone"></div>
        </div>
    `;
    chatContainer.appendChild(div);
    scrollToBottom();
    return div;
}

function handleAgentEvent(data, container) {
    const statusZone = container.querySelector('.status-zone');
    const planZone = container.querySelector('.plan-zone');
    const mdZone = container.querySelector('.markdown-zone');

    let v = data.status;

    if (v === 'thinking') {
        statusZone.innerHTML = `<div class="status-update"><span class="status-icon">🧠</span> ${escapeHtml(data.content || data.message)}</div>`;
    }
    else if (v === 'plan_ready') {
        let html = '<div class="plan-container"><strong>План действий:</strong><br>';
        data.plan_steps.forEach(step => {
            html += `<div class="plan-item pending" id="plan-${step.id}">
                        <span class="material-icons-round" style="font-size:16px">radio_button_unchecked</span>
                        ${escapeHtml(step.text)}
                     </div>`;
        });
        html += '</div>';
        planZone.innerHTML = html;
        statusZone.innerHTML = '';
        vibrate(10);
    }
    else if (v === 'plan_step_start') {
        const item = document.getElementById(`plan-${data.step_id}`);
        if (item) {
            // Сброс предыдущих running
            document.querySelectorAll('.plan-item.running').forEach(el => {
                el.classList.remove('running');
                el.classList.add('done');
                el.querySelector('.material-icons-round').textContent = 'check_circle';
            });
            item.classList.remove('pending');
            item.classList.add('running');
            item.querySelector('.material-icons-round').textContent = 'sync';
            item.querySelector('.material-icons-round').style.animation = 'pulseAnim 2s infinite';
        }
        statusZone.innerHTML = '';
    }
    else if (v === 'tool_use') {
        statusZone.innerHTML = `<div class="status-update"><span class="status-icon">⚙️</span> Запуск: ${escapeHtml(data.tool || data.content.tool)}</div>`;
        vibrate(10);
    }
    else if (v === 'observation') {
        statusZone.innerHTML = `<div class="status-update"><span class="status-icon">✅</span> Инструмент завершил работу</div>`;
    }
    else if (v === 'final_stream') {
        statusZone.innerHTML = ''; // Убираем статусы при начале финального ответа
        if (!container._mdText) container._mdText = '';
        container._mdText += data.content;
        mdZone.innerHTML = marked.parse(container._mdText);

        // Автоскролл если мы близко к низу
        if (chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 150) {
            scrollToBottom();
        }
    }
    else if (v === 'final') {
        statusZone.innerHTML = '';
        if (data.content) {
            mdZone.innerHTML = marked.parse(data.content);
        }

        // Все шаги помечаем выполненными
        document.querySelectorAll('.plan-item').forEach(el => {
            el.classList.remove('running', 'pending');
            el.classList.add('done');
            el.querySelector('.material-icons-round').textContent = 'check_circle';
            el.querySelector('.material-icons-round').style.animation = 'none';
        });
    }
    else if (v === 'error') {
        statusZone.innerHTML = `<div class="status-update error"><span class="status-icon">⚠️</span> Ошибка: ${escapeHtml(data.message || data.content)}</div>`;
    }

    scrollToBottom();
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}


// --- Запись Голоса ---

// Инициализация MediaRecorder при долгом нажатии
let voiceTouchTimer;

voiceBtn.addEventListener('touchstart', startVoiceInteraction, {passive: false});
voiceBtn.addEventListener('mousedown', startVoiceInteraction);

voiceBtn.addEventListener('touchend', endVoiceInteraction);
voiceBtn.addEventListener('mouseup', endVoiceInteraction);
voiceBtn.addEventListener('touchcancel', cancelVoiceInteraction);
voiceBtn.addEventListener('mouseleave', endVoiceInteraction); // если мышь ушла

async function startVoiceInteraction(e) {
    e.preventDefault();
    if (isGenerating) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            stream.getTracks().forEach(track => track.stop());
            if (isRecording) { // если не отменено
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                // конвертируем в File object
                const audioFile = new File([audioBlob], "voice_record.webm", { type: 'audio/webm' });
                sendMessage(audioFile, "");
            }
            isRecording = false;
        };

        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();

        // Показ UI
        recordingOverlay.classList.remove('hidden');
        vibrate([50, 50]);

        recordingInterval = setInterval(() => {
            const diff = Math.floor((Date.now() - recordingStartTime) / 1000);
            const mins = Math.floor(diff / 60);
            const secs = (diff % 60).toString().padStart(2, '0');
            recordingTime.textContent = `${mins}:${secs}`;
        }, 1000);

    } catch (err) {
        console.error("Ошибка доступа к микрофону", err);
        alert("Нет доступа к микрофону. Проверьте разрешения браузера.");
    }
}

function endVoiceInteraction(e) {
    if (e && e.cancelable) e.preventDefault();
    if (!isRecording || !mediaRecorder) return;

    // Остановка
    clearInterval(recordingInterval);
    recordingOverlay.classList.add('hidden');

    // Проверка, что запись длилась хотя бы 1 секунду
    if (Date.now() - recordingStartTime < 1000) {
        isRecording = false; // отмена
        mediaRecorder.stop();
        vibrate(50);
        return;
    }

    mediaRecorder.stop();
    vibrate(30);
}

function cancelVoiceInteraction() {
    if (!isRecording) return;
    isRecording = false;
    clearInterval(recordingInterval);
    recordingOverlay.classList.add('hidden');
    if (mediaRecorder) mediaRecorder.stop();
    vibrate([50, 100, 50]);
}

// Отмена записи при свайпе влево (простая реализация)
let startX = 0;
recordingOverlay.addEventListener('touchstart', e => {
    startX = e.touches[0].clientX;
});
recordingOverlay.addEventListener('touchmove', e => {
    let currentX = e.touches[0].clientX;
    if (startX - currentX > 100) {
        cancelVoiceInteraction();
    }
});
