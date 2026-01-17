/**
 * Hotelix Dedicated AI Logic
 */

const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');

function processChat() {
    const text = userInput.value.trim();
    if (!text) return;

    // 1. Add User Bubble
    addBubble(text, 'user');
    userInput.value = '';

    // 2. Simulate AI thinking
    setTimeout(() => {
        const response = generateAIResponse(text);
        addBubble(response, 'bot');
    }, 1000);
}

function addBubble(text, type) {
    const div = document.createElement('div');
    div.className = `msg ${type}`;
    div.innerHTML = text; // innerHTML to allow <br> tags
    chatContainer.appendChild(div);
    
    // Smooth scroll to latest message
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

function generateAIResponse(input) {
    const prompt = input.toLowerCase();

    if (prompt.includes('paris')) {
        return "Paris is exquisite this time of year. I've highlighted three properties: The Ritz for classic luxury, or Hotel Costes for a more boutique, modern vibe. Would you like to see the private gallery for these?";
    } 
    
    if (prompt.includes('beach') || prompt.includes('ocean')) {
        return "Searching our coastal portfolio... I've found a private island villa with underwater suites. Is that the level of privacy you're looking for?";
    }

    return "Analyzing your request against our global luxury database... I am finding several matches that prioritize those specific amenities. May I ask what your preferred dates are?";
}

// Allow Enter key to send
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') processChat();
});
