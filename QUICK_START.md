# 🚀 Quick Start Guide - Add Your AI API Key

## Where to Paste Your API Key

### **File: `app.py`** (Lines 15-20)

Find this section in `app.py`:

```python
# AI API Configuration - PASTE YOUR API KEY HERE
# Method 1: Use environment variables (recommended)
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_API_TYPE = os.environ.get('AI_API_TYPE', 'openai').lower()
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4')

# Method 2: Direct configuration (alternative - paste your key here)
# Uncomment and paste your API key below:
# AI_API_KEY = "sk-your-api-key-here"
# AI_API_TYPE = "openai"
# AI_MODEL = "gpt-4"
```

### **Easiest Way (Recommended):**

Uncomment Method 2 and paste your key:

```python
AI_API_KEY = "sk-your-actual-api-key-here"  # ← PASTE YOUR KEY HERE
AI_API_TYPE = "openai"  # Keep as "openai" for OpenAI, or change to "anthropic", "lovable", "google"
AI_MODEL = "gpt-4"  # Model name
```

## Get Your API Key

### OpenAI (Easiest):
1. Go to https://platform.openai.com/api-keys
2. Sign up / Login
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Paste it in `app.py` as shown above

### Other Options:
- **Anthropic Claude**: https://console.anthropic.com/settings/keys
- **Google Gemini**: https://aistudio.google.com/app/apikey
- **Lovable**: From your Lovable dashboard

## Configuration Examples

### OpenAI (Default):
```python
AI_API_KEY = "sk-proj-xxxxxxxxxxxxxxxxxxxxx"
AI_API_TYPE = "openai"
AI_MODEL = "gpt-4"  # or "gpt-3.5-turbo" for cheaper option
```

### Anthropic Claude:
```python
AI_API_KEY = "sk-ant-api03-xxxxxxxxxxxxx"
AI_API_TYPE = "anthropic"
AI_MODEL = "claude-3-opus-20240229"
```

### Google Gemini:
```python
AI_API_KEY = "AIzaSyxxxxxxxxxxxxxxxxxxxxx"
AI_API_TYPE = "google"
AI_MODEL = "gemini-pro"
```

## Run the App

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run:
```bash
python app.py
```

3. Open browser: http://localhost:5000

4. Test the chat feature! 💬

## Notes

✅ **SQLite is already configured** - no database setup needed  
✅ **SECRET_KEY** - already has a default value (change for production)  
✅ **Database file** - `StudyVerse.db` will be created automatically  

## Troubleshooting

**"AI API key not configured" message?**
- Make sure you uncommented the lines in `app.py`
- Check that your key is between quotes: `"sk-..."`

**Chat not working?**
- Check your API key is correct
- Make sure you have credits/quota in your OpenAI/Anthropic account
- Check the console for error messages

## That's It!

The main file is **`app.py`** - that's where you paste your API key. The chat endpoint is at line 222 (function: `chat_message()`), and the AI API call function is at line 307 (function: `call_ai_api()`).

