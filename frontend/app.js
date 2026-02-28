document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');

    // Command buttons
    const btnStart = document.getElementById('btn-start');
    const btnRestart = document.getElementById('btn-restart');
    const btnStop = document.getElementById('btn-stop');
    const btnClear = document.getElementById('btn-clear');

    // API Configuration
    const API_URL = 'http://127.0.0.1:8080/chat';
    const CHAT_ID = 'web_client_' + Math.floor(Math.random() * 100000); // Generate a session id

    // Store references to the current bot message elements
    let currentMessageContainer = null;
    let currentThinkingSpan = null;
    let currentFinalSpan = null;

    function addMessage(text, className) {
        const div = document.createElement('div');
        div.className = `message ${className}`;
        div.textContent = text;
        chatMessages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Handles the actual API call and SSE stream reading
    async function sendMessage(message) {
        if (!message.trim()) return;

        // Display user message
        addMessage(message, 'user-message');
        chatInput.value = '';

        // Prepare new bot message container
        currentMessageContainer = document.createElement('div');
        currentMessageContainer.className = 'message bot-message';

        currentThinkingSpan = document.createElement('span');
        currentThinkingSpan.className = 'thinking';
        currentMessageContainer.appendChild(currentThinkingSpan);

        currentFinalSpan = document.createElement('span');
        currentFinalSpan.className = 'final-content';
        currentMessageContainer.appendChild(currentFinalSpan);

        chatMessages.appendChild(currentMessageContainer);
        scrollToBottom();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: CHAT_ID, message: message })
            });

            if (!response.ok) {
                addMessage(`Server Error: ${response.status} - ${response.statusText}`, 'error-message');
                return;
            }

            // Standard Fetch API streams handling for SSE
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process SSE "data: ..." format
                let boundary = buffer.indexOf('\n\n');
                while (boundary !== -1) {
                    const chunk = buffer.slice(0, boundary).trim();
                    buffer = buffer.slice(boundary + 2);

                    if (chunk.startsWith('data: ')) {
                        const jsonStr = chunk.substring(6); // remove 'data: '
                        try {
                            const data = JSON.parse(jsonStr);
                            handleStreamEvent(data);
                        } catch (e) {
                            console.warn("Failed to parse SSE JSON chunk:", jsonStr, e);
                        }
                    }
                    boundary = buffer.indexOf('\n\n');
                }
            }
        } catch (error) {
            console.error('Fetch error:', error);
            addMessage(`Connection Error: ${error.message}`, 'error-message');
        }
    }

    // Handles the status updates from the backend
    function handleStreamEvent(data) {
        if (!data || !data.status) return;

        switch (data.status) {
            case 'thinking':
            case 'thinking_stream':
            case 'tool_use':
            case 'observation':
                // Update thinking text if available, or just clear if streaming final
                if (data.message) {
                    currentThinkingSpan.textContent = `[${data.status}] ${data.message}\n`;
                } else if (data.content) {
                    currentThinkingSpan.textContent += data.content;
                }
                break;
            case 'plan_ready':
            case 'plan_step_start':
                currentThinkingSpan.textContent += `\n[Plan Update]...\n`;
                break;
            case 'final_stream':
                // Clear thinking, append to final
                currentThinkingSpan.textContent = '';
                if (data.content) {
                    currentFinalSpan.textContent += data.content;
                }
                break;
            case 'final':
                currentThinkingSpan.textContent = '';
                // The final text usually overrides or completes the stream
                if (data.content) {
                    // Sometimes final is the full response, sometimes we already built it
                    if (!currentFinalSpan.textContent.includes(data.content.substring(0, 10))) {
                       currentFinalSpan.textContent = data.content;
                    }
                }
                break;
            case 'error':
                currentThinkingSpan.textContent = '';
                addMessage(`Error: ${data.message || 'Unknown error'}`, 'error-message');
                break;
            default:
                console.log('Unhandled status:', data);
        }
        scrollToBottom();
    }

    // Event Listeners
    btnSend.addEventListener('click', () => sendMessage(chatInput.value));
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage(chatInput.value);
    });

    // Button interactions simulating telegram commands
    btnStart.addEventListener('click', () => sendMessage('/start'));
    btnClear.addEventListener('click', () => {
        sendMessage('/clear');
        setTimeout(() => {
            chatMessages.innerHTML = '<div class="message system-message">Chat memory cleared.</div>';
        }, 500);
    });
    btnStop.addEventListener('click', () => sendMessage('/stop'));
    btnRestart.addEventListener('click', () => {
        chatMessages.innerHTML = '<div class="message system-message">Restarting interface...</div>';
    });

    // Focus input on load
    chatInput.focus();
});