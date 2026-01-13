const CONFIG = {
    API_BASE: 'http://localhost:8000/api',
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    MAX_MESSAGE_LENGTH: 500
};

let appState = {
    sessionId: null,
    isLoading: false,
    messageCount: 0
};

const elements = {
    messages: document.getElementById('messages'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn')
};

const utils = {
    sanitizeText: (text) => (text || '').toString().replace(/[<>]/g, '').trim(),
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms))
};

class ChatbotError extends Error {
    constructor(message, type = 'general') {
        super(message);
        this.type = type;
        this.name = 'ChatbotError';
    }
}

const api = {
    async request(endpoint, options = {}, retries = CONFIG.MAX_RETRIES) {
        try {
            const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, {
                headers: { 'Content-Type': 'application/json' },
                ...options
            });

            if (!response.ok) {
                throw new ChatbotError(`HTTP ${response.status}: ${response.statusText}`, 'network');
            }

            return await response.json();
        } catch (error) {
            if (retries > 0 && (error.type === 'network' || error.name === 'TypeError')) {
                await utils.sleep(CONFIG.RETRY_DELAY);
                return this.request(endpoint, options, retries - 1);
            }
            throw error;
        }
    },

    async startSession() {
        return this.request('/chatbot/start_session/', {
            method: 'POST',
            body: JSON.stringify({ email: '' })
        });
    },

    async sendMessage(sessionId, message) {
        return this.request('/chatbot/send_message/', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, message })
        });
    }
};

// Tracking simple des clics d’affiliation
const analytics = {
    async trackAffiliateClick(hotelId, affiliateUrl) {
        try {
            await fetch(`${CONFIG.API_BASE}/analytics/click/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    hotel_id: hotelId || null,
                    affiliate_url: affiliateUrl || null,
                    ts: new Date().toISOString()
                })
            });
        } catch (e) {
            console.warn('Analytics tracking error', e);
        }
    }
};

const ui = {
    displayMessage: (text, sender, isError = false) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        if (isError) bubble.classList.add('error');

        bubble.textContent = text;
        msgDiv.appendChild(bubble);

        if (sender === 'bot') {
            msgDiv.setAttribute('aria-label', `Message du bot: ${text}`);
        } else {
            msgDiv.setAttribute('aria-label', `Votre message: ${text}`);
        }

        elements.messages.appendChild(msgDiv);
        elements.messages.scrollTop = elements.messages.scrollHeight;
        appState.messageCount++;
    },

    displayRecommendations: (hotels) => {
        const container = document.createElement('div');
        container.className = 'message bot';
        container.setAttribute('role', 'region');
        container.setAttribute('aria-label', 'Recommandations d’hôtels Hotelix');

        const wrapper = document.createElement('div');

        hotels.forEach((hotel) => {
            const card = document.createElement('div');
            card.className = 'hotel-card';
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            card.setAttribute(
                'aria-label',
                `Hôtel: ${hotel.name}, Prix: ${hotel.price}€ par nuit, Note: ${hotel.rating || 'Non disponible'}`
            );

            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (hotel.affiliate_url) {
                        analytics.trackAffiliateClick(hotel.id || null, hotel.affiliate_url);
                        window.open(hotel.affiliate_url, '_blank');
                    }
                }
            });

            const img = document.createElement('img');
            if (hotel.image_url) {
                img.src = hotel.image_url;
            } else {
                img.src = 'https://via.placeholder.com/300x180?text=Hotel';
            }
            img.alt = `Photo de ${hotel.name}`;
            img.onerror = () => {
                img.src = 'https://via.placeholder.com/300x180?text=No+Image';
            };

            const main = document.createElement('div');
            main.className = 'hotel-main';

            const nameEl = document.createElement('div');
            nameEl.className = 'hotel-name';
            nameEl.textContent = utils.sanitizeText(hotel.name);

            const meta = document.createElement('div');
            meta.className = 'hotel-meta';

            const priceEl = document.createElement('span');
            priceEl.className = 'hotel-price';
            priceEl.textContent = `${hotel.price}€/nuit`;

            const ratingEl = document.createElement('span');
            ratingEl.className = 'hotel-rating';
            ratingEl.textContent = `⭐ ${hotel.rating || 'N/A'}`;

            meta.appendChild(priceEl);
            meta.appendChild(ratingEl);

            main.appendChild(nameEl);
            main.appendChild(meta);

            if (hotel.amenities && hotel.amenities.length > 0) {
                const amenitiesWrap = document.createElement('div');
                amenitiesWrap.className = 'hotel-amenities';
                hotel.amenities.slice(0, 3).forEach((amenity) => {
                    const a = document.createElement('span');
                    a.className = 'amenity';
                    a.textContent = utils.sanitizeText(amenity);
                    amenitiesWrap.appendChild(a);
                });
                main.appendChild(amenitiesWrap);
            }

            if (hotel.affiliate_url) {
                const link = document.createElement('a');
                link.href = hotel.affiliate_url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.className = 'book-btn';
                link.setAttribute('aria-label', `Réserver ${hotel.name}`);
                link.textContent = 'Voir et réserver →';

                link.addEventListener('click', () => {
                    analytics.trackAffiliateClick(hotel.id || null, hotel.affiliate_url);
                });

                main.appendChild(link);
            }

            card.appendChild(img);
            card.appendChild(main);
            wrapper.appendChild(card);
        });

        container.appendChild(wrapper);
        elements.messages.appendChild(container);
        elements.messages.scrollTop = elements.messages.scrollHeight;
    },

    showLoading: () => {
        if (appState.isLoading) return;
        appState.isLoading = true;

        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot';
        msgDiv.id = 'loading';
        msgDiv.setAttribute('aria-label', 'Chargement de la réponse');

        msgDiv.innerHTML = `
            <div class="loading" aria-hidden="true">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;

        elements.messages.appendChild(msgDiv);
        elements.messages.scrollTop = elements.messages.scrollHeight;
    },

    removeLoading: () => {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.remove();
        }
        appState.isLoading = false;
    },

    setLoadingState: (loading) => {
        elements.sendBtn.disabled = loading;
        elements.messageInput.disabled = loading;
        elements.sendBtn.setAttribute(
            'aria-label',
            loading ? 'Envoi du message...' : 'Envoyer le message'
        );
    },

    showError: (message) => {
        ui.displayMessage(`❌ ${message}`, 'bot', true);
    }
};

const handlers = {
    handleKeyPress: (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handlers.sendMessage();
        }
    },

    sendMessage: utils.debounce(async () => {
        const text = elements.messageInput.value.trim();
        if (!text || !appState.sessionId || appState.isLoading) return;

        if (text.length > CONFIG.MAX_MESSAGE_LENGTH) {
            ui.showError(`Message trop long. Maximum ${CONFIG.MAX_MESSAGE_LENGTH} caractères.`);
            return;
        }

        ui.displayMessage(text, 'user');
        elements.messageInput.value = '';
        ui.setLoadingState(true);
        ui.showLoading();

        try {
            const data = await api.sendMessage(appState.sessionId, text);
            ui.removeLoading();
            ui.displayMessage(data.bot_response, 'bot');

            if (data.recommendations && data.recommendations.length > 0) {
                ui.displayRecommendations(data.recommendations);
            }
        } catch (error) {
            console.error('Send message error:', error);
            ui.removeLoading();
            ui.showError('Erreur lors de la communication. Veuillez réessayer.');
        } finally {
            ui.setLoadingState(false);
            elements.messageInput.focus();
        }
    }, 300)
};

async function initApp() {
    try {
        const data = await api.startSession();
        appState.sessionId = data.session_id;
        ui.displayMessage(data.message, 'bot');
    } catch (error) {
        console.error('Init session error:', error);
        ui.showError('Impossible de démarrer la session. Vérifiez le backend puis rafraîchissez la page.');
    }
}

elements.messageInput.addEventListener('keypress', handlers.handleKeyPress);
elements.sendBtn.addEventListener('click', handlers.sendMessage);

elements.messageInput.addEventListener('focus', () => {
    elements.messageInput.setAttribute('aria-expanded', 'true');
});

elements.messageInput.addEventListener('blur', () => {
    elements.messageInput.setAttribute('aria-expanded', 'false');
});

initApp();

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    ui.showError('Une erreur inattendue s’est produite.');
});
