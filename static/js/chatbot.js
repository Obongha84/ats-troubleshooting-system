/* ============================================
   ATS CHATBOT LOGIC
   ============================================ */

(function() {
    'use strict';
    
    // ========== STATE ==========
    let chatOpen = false;
    let isTyping = false;
    let recognition = null;
    let isRecording = false;
    let chatHistory = []; // Store for PDF export
    
    // ========== DOM ELEMENTS ==========
    const chatToggle = document.getElementById('chatToggleBtn');
    const chatPanel = document.getElementById('chatPanel');
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const chatSend = document.getElementById('chatSendBtn');
    const chatClose = document.getElementById('chatCloseBtn');
    const chatClear = document.getElementById('chatClearBtn');
    const chatExport = document.getElementById('chatExportBtn');
    const voiceBtn = document.getElementById('voiceInputBtn');
    
    if (!chatToggle || !chatPanel) return;
    
    // ========== TOGGLE CHAT ==========
    function toggleChat() {
        chatOpen = !chatOpen;
        chatPanel.classList.toggle('open', chatOpen);
        
        if (chatOpen) {
            chatInput.focus();
            scrollToBottom();
        }
    }
    
    chatToggle.addEventListener('click', toggleChat);
    chatClose.addEventListener('click', toggleChat);
    
    // ========== SEND MESSAGE ==========
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message || isTyping) return;
        
        // Add user message
        addMessage('user', message);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        
        // Send to backend
        getBotResponse(message);
    }
    
    chatSend.addEventListener('click', sendMessage);
    
    // Enter to send, Shift+Enter for newline
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize input
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 100) + 'px';
    });
    
    // ========== ADD MESSAGE ==========
    function addMessage(role, text, quickReplies = []) {
        // Store in history
        chatHistory.push({
            role: role,
            text: text,
            timestamp: new Date().toISOString()
        });
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}`;
        
        const avatarIcon = role === 'user' ? 'fa-user' : 'fa-robot';
        
        msgDiv.innerHTML = `
            <div class="msg-avatar">
                <i class="fas ${avatarIcon}"></i>
            </div>
            <div class="msg-bubble">${formatMessage(text)}</div>
        `;
        
        chatMessages.appendChild(msgDiv);
        
        // Add quick replies if provided
        if (quickReplies && quickReplies.length > 0) {
            const qrDiv = document.createElement('div');
            qrDiv.className = 'quick-replies';
            
            quickReplies.forEach(reply => {
                const btn = document.createElement('button');
                btn.className = 'quick-reply-btn';
                btn.textContent = reply;
                btn.onclick = function() {
                    chatInput.value = reply;
                    sendMessage();
                };
                qrDiv.appendChild(btn);
            });
            
            chatMessages.appendChild(qrDiv);
        }
        
        scrollToBottom();
    }
    
    // ========== FORMAT MESSAGE ==========
    function formatMessage(text) {
        // Escape HTML
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Bold: **text**
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Code: `text`
        formatted = formatted.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    // ========== SHOW TYPING ==========
    function showTyping() {
        isTyping = true;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message bot';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="msg-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }
    
    function hideTyping() {
        isTyping = false;
        const typing = document.getElementById('typingIndicator');
        if (typing) typing.remove();
    }
    
    // ========== GET BOT RESPONSE ==========
    function getBotResponse(message) {
        showTyping();
        
        fetch('/api/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        })
        .then(r => r.json())
        .then(data => {
            // Artificial delay for realism
            setTimeout(() => {
                hideTyping();
                
                if (data.success) {
                    addMessage('bot', data.response, data.quick_replies || []);
                } else {
                    addMessage('bot', 'Sorry, I encountered an error. Please try again.');
                }
            }, 600);
        })
        .catch(err => {
            hideTyping();
            addMessage('bot', 'Sorry, I could not connect. Please check your internet.');
            console.error('Chatbot error:', err);
        });
    }
    
    // ========== SCROLL TO BOTTOM ==========
    function scrollToBottom() {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 50);
    }
    
    // ========== CLEAR CHAT ==========
    if (chatClear) {
        chatClear.addEventListener('click', function() {
            if (!confirm('Clear chat history?')) return;
            
            chatMessages.innerHTML = '';
            chatHistory = [];
            
            // Re-show welcome
            showWelcome();
            
            showToast('Chat cleared', 'info', 2000);
        });
    }
    
    // ========== WELCOME MESSAGE ==========
    function showWelcome() {
        const welcome = document.createElement('div');
        welcome.className = 'chat-welcome';
        welcome.innerHTML = `
            <h3>Hi! I'm your ATS Assistant</h3>
            <p>I can help with disk health, performance issues, and system diagnostics.</p>
            <div class="welcome-suggestions">
                <div class="welcome-suggestion" onclick="quickAsk('Why is my disk showing warning?')">
                    <i class="fas fa-hdd"></i>
                    <span>Why is my disk showing warning?</span>
                </div>
                <div class="welcome-suggestion" onclick="quickAsk('How do I fix high CPU usage?')">
                    <i class="fas fa-microchip"></i>
                    <span>How do I fix high CPU usage?</span>
                </div>
                <div class="welcome-suggestion" onclick="quickAsk('What is S.M.A.R.T.?')">
                    <i class="fas fa-info-circle"></i>
                    <span>What is S.M.A.R.T.?</span>
                </div>
                <div class="welcome-suggestion" onclick="quickAsk('Show me my latest diagnosis')">
                    <i class="fas fa-chart-line"></i>
                    <span>Show me my latest diagnosis</span>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(welcome);
    }
    
    // Global function for welcome suggestions
    window.quickAsk = function(message) {
        chatInput.value = message;
        sendMessage();
    };
    
    // ========== VOICE INPUT ==========
    function initVoiceInput() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            voiceBtn.style.display = 'none';
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onstart = function() {
            isRecording = true;
            voiceBtn.classList.add('recording');
            chatInput.placeholder = 'Listening...';
        };
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            chatInput.focus();
        };
        
        recognition.onerror = function(event) {
            console.error('Voice error:', event.error);
            showToast('Voice input failed. Please try again.', 'error', 2000);
        };
        
        recognition.onend = function() {
            isRecording = false;
            voiceBtn.classList.remove('recording');
            chatInput.placeholder = 'Type your message...';
        };
        
        voiceBtn.addEventListener('click', function() {
            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
    }
    
    // ========== EXPORT CHAT AS PDF ==========
    if (chatExport) {
        chatExport.addEventListener('click', function() {
            if (chatHistory.length === 0) {
                showToast('No chat to export', 'warning');
                return;
            }
            
            // Send to backend to generate PDF
            fetch('/api/chatbot/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ history: chatHistory })
            })
            .then(r => {
                if (r.ok) return r.blob();
                throw new Error('Export failed');
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `ats_chat_${new Date().toISOString().slice(0, 10)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showToast('Chat exported!', 'success');
            })
            .catch(err => {
                showToast('Export failed', 'error');
                console.error(err);
            });
        });
    }
    
    // ========== INITIALIZE ==========
    function init() {
        showWelcome();
        initVoiceInput();
        
        // Auto-open chat after 30 seconds if user hasn't opened it
        setTimeout(() => {
            if (!chatOpen && chatHistory.length === 0) {
                chatToggle.classList.add('pulse');
            }
        }, 30000);
    }
    
    // ========== KEYBOARD SHORTCUT ==========
    document.addEventListener('keydown', function(e) {
        // Ctrl+K opens chat
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            if (!chatOpen) toggleChat();
            chatInput.focus();
        }
        // Escape closes chat
        if (e.key === 'Escape' && chatOpen) {
            toggleChat();
        }
    });
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();