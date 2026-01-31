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

## Setup Instructions for Teacher

### Prerequisites
- Python 3.11 or higher installed on your computer
- Internet connection for downloading packages

### Step-by-Step Installation

### 1. Download the Project
Download and extract the project folder, or clone it using:
```bash
git clone https://github.com/dibtabdelali-art/Hotelix.git
cd Hotelix
```

### 2. Create Virtual Environment (.venv)
A virtual environment keeps all project packages isolated. Create it with:
```bash
python -m venv .venv
```
This creates a `.venv` folder with Python packages.

### 3. Activate the Virtual Environment

**On Windows CMD:**
```cmd
.venv\Scripts\activate
```

**On Windows PowerShell:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

**On Mac/Linux:**
```bash
source .venv/bin/activate
```

You'll see `(.venv)` at the beginning of your command line when activated.

### 4. Install All Required Packages
This installs Django, GROQ SDK, and all dependencies automatically:
```bash
pip install -r requirements.txt
```
Wait for all packages to download and install (may take 2-3 minutes).

### 5. Verify Installation
Check if everything installed correctly:
```bash
python -m django --version
```
You should see: `5.2.10`

### 5. Verify Installation
Check if everything installed correctly:
```bash
python -m django --version
```
You should see: `5.2.10`

### 6. Set Up Environment Variables (API Keys)

**Important:** The chatbot needs two API keys to work.

**On Windows PowerShell (recommended):**
```powershell
$env:GROQ_API_KEY="your_groq_api_key_here"
$env:MAKCORPS_API_KEY="your_makcorps_api_key_here"
$env:MAKCORPS_BASE_URL="https://api.makcorps.com"
```

**On Windows CMD:**
```cmd
set GROQ_API_KEY=your_groq_api_key_here
set MAKCORPS_API_KEY=your_makcorps_api_key_here
set MAKCORPS_BASE_URL=https://api.makcorps.com
```

**Note:** Contact the student for the actual API keys.

### 7. Initialize Database
Run migrations to set up the database:
```bash
python manage.py migrate
```
You'll see several "Applying..." messages. This is normal.

### 8. Start the Development Server
```bash
python manage.py runserver
```
You should see:
```
Starting development server at http://127.0.0.1:8000/
```

### 9. Open the Chatbot
Open your web browser and go to:
```
http://127.0.0.1:8000/coversation.html
```

You should see the chatbot interface ready to use!

### Troubleshooting

**Problem:** `python` command not found
- **Solution:** Install Python 3.11+ from python.org

**Problem:** Permission error when activating virtual environment
- **Solution:** Run PowerShell as Administrator, then use the bypass command

**Problem:** "No module named django"
- **Solution:** Make sure virtual environment is activated (you see `.venv` in terminal), then run `pip install -r requirements.txt` again

**Problem:** Chatbot says "error" or no results
- **Solution:** Check that API keys are set correctly using the PowerShell/CMD commands in step 6

## API Keys Required
- **GROQ API**: For natural language processing and intent parsing
- **Makcorps API**: For hotel search data

## Project Structure
- `chatbot/` - Main chatbot application with AI logic
- `hotels/` - Hotel booking API integration
- `frontend/` - Static files and templates
- `config/` - Django settings and configuration
