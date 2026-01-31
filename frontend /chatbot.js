document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const mainCta = document.querySelector('.main-cta');
    const backLink = document.querySelector('.back-link');

    // Page enter animation
    document.body.classList.add('fade-in');

    let sessionId = null;
    let sending = false;

    async function createSession() {
        try {
            console.debug('Creating chat session...');
            const res = await fetch('/api/chatbot/start_session/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            });
            if (!res.ok) {
                console.warn('Failed to create session', res.status);
                return null;
            }
            const data = await res.json();
            if (data && data.session_id) {
                // show welcome message if provided
                if (data.message) addBubble(data.message, 'bot');
                return data.session_id;
            }
            return null;
        } catch (err) {
            console.error('Session creation failed', err);
            addBubble('Impossible de démarrer la session de chat. Le serveur est indisponible.', 'bot');
            return null;
        }
    }

    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    async function processChat() {
        if (!userInput) return;
        const text = userInput.value.trim();
        if (!text) return;
        if (sending) {
            console.debug('Ignored send: already sending');
            return;
        }

        addBubble(text, 'user');
        userInput.value = '';

        // ensure we have a session
        if (!sessionId) {
            sessionId = await createSession();
        }

        // show typing indicator
        const typing = document.createElement('div');
        typing.className = 'msg bot typing';
        typing.innerText = '…';
        chatContainer.appendChild(typing);
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });

        sending = true;
        try {
            console.debug('Sending message to API', { session_id: sessionId, text });
            const csrf = getCookie('csrftoken');
            const res = await fetch('/api/chatbot/send_message/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ session_id: sessionId, message: text })
            });

            // attempt to parse JSON only if returned content-type is JSON
            const ct = res.headers.get('content-type') || '';
            let json = null;
            try {
                if (ct.includes('application/json')) {
                    json = await res.json();
                } else {
                    // read text body for error messages
                    const txt = await res.text();
                    // remove typing and surface server text
                    typing.remove();
                    addBubble(`<div class="error">${txt}</div>`, 'bot');
                    console.error('Non-JSON response from API', txt);
                    return;
                }
            } catch (e) {
                typing.remove();
                addBubble('Réponse inattendue du serveur.', 'bot');
                console.error('Failed to parse API response', e);
                return;
            }

            // remove typing
            typing.remove();

            if (!res.ok) {
                // try to surface backend error message
                const errMsg = json && (json.error || json.message || json.detail) ? (json.error || json.message || json.detail) : 'Erreur du serveur.';
                addBubble(`<div class="error">${errMsg}</div>`, 'bot');
                console.error('API error', json);
                return;
            }

            const botText = json.bot_response || 'Désolé, je n\'ai pas compris.';
            addBubble(botText, 'bot');

            // render recommendations if present
            const recs = json.recommendations || [];
            if (recs.length) {
                const recHtml = recs.map(r => {
                    const priceStr = r.price_str || (r.price ? `€${Math.round(r.price)}` : 'N/A');
                    const rating = (r.rating !== null && r.rating !== undefined) ? `${parseFloat(r.rating).toFixed(1)}/5` : 'N/A';
                    const loc = r.location || '';
                    const url = r.affiliate_url || '';
                    return `<div class="rec"><strong>${r.name}</strong><div>${rating} · ${priceStr}</div><div>${loc}</div>${url ? `<div><a href="${url}" target="_blank">Réserver</a></div>` : ''}</div>`;
                }).join('\n');
                addBubble(recHtml, 'bot');
            }
        } catch (err) {
            typing.remove();
            addBubble('Impossible de joindre le serveur. Vérifiez votre connexion.', 'bot');
            console.error('processChat error', err);
        } finally {
            sending = false;
        }
    }

    function addBubble(text, type) {
        if (!chatContainer) return;
        const div = document.createElement('div');
        div.className = `msg ${type}`;
        div.innerHTML = text; // allow <br>
        chatContainer.appendChild(div);
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    }

    // legacy fallback removed to ensure server is used consistently

    if (userInput) {
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') processChat(); });
    }

    // create session immediately on page load to surface server welcome
    (async () => {
        try {
            sessionId = await createSession();
            console.debug('Session initialized', sessionId);
        } catch (e) {
            console.warn('Session init failed', e);
        }
    })();

    // expose to window so HTML buttons can call it
    window.processChat = processChat;

    // Smooth navigation with fade-out
    function navigateWithFade(url) {
        document.body.classList.remove('fade-in');
        document.body.classList.add('fade-out');
        setTimeout(() => { window.location.href = url; }, 300);
    }

    if (mainCta) {
        mainCta.addEventListener('click', (e) => {
            const href = mainCta.getAttribute('href') || 'coversation.html';
            e.preventDefault();
            navigateWithFade(href);
        });
    }

    if (backLink) {
        backLink.addEventListener('click', (e) => {
            const href = backLink.getAttribute('href') || 'chatbot.html';
            e.preventDefault();
            navigateWithFade(href);
        });
    }
});
