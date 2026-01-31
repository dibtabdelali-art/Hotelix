# Hotel Chatbot

Django-based hotel search chatbot using GROQ AI and Makcorps hotel API.

## How It Works (Simple Explanation)

This is a smart chatbot that helps you find hotels. Here's what happens when you talk to it:

1. **You Type a Message** 
   - Example: "I want hotels in Marrakech from February 2 to February 6, 2026"
   - You write in French or English, naturally like talking to a person

2. **AI Understands Your Request**
   - The chatbot uses GROQ AI (a smart language model) to read your message
   - It figures out what you want: the city, check-in date, check-out date, number of guests
   - Think of it like a smart assistant that understands human language

3. **Searches for Hotels**
   - The chatbot contacts Makcorps (a hotel database) with your search details
   - It looks for available hotels that match your dates and location
   - This is like asking a travel agent to find hotels for you

4. **Shows You Results**
   - The chatbot displays the hotels it found
   - You see hotel names, prices, and details
   - All presented in a friendly chat interface

**Technologies Used:**
- **Django**: The web framework that runs the website (like the foundation of a house)
- **GROQ AI**: The brain that understands what you're asking for
- **Makcorps API**: The database where we get hotel information
- **Python**: The programming language everything is written in

**Simple Flow:**
```
Your Message → AI Brain (GROQ) → Understands Request → Searches Hotels (Makcorps) → Shows Results
```

## Features
- AI-powered intent parsing using GROQ (llama-3.1-8b-instant)
- Hotel search via Makcorps API
- French language support
- REST API backend with Django
