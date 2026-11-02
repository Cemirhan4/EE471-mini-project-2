# PROMPTS.md — Vibe Coding Transcripts

This document records the prompts, architectural decisions, and iterative refinement used to develop **EE471 Mini Project #2: Voice-Activated Library App**.

---

## 1. Initial Prompt & Project Ingestion

**Prompt:**
> "Here is Mini Project #2 for EE471. We need to take our Library App from Week 4 and improve it with voice activation using Azure Speech Services.
> All API keys (Azure Speech key, region) must be kept inside a local `.env` file and ignored in `.gitignore`.
> Each endpoint must allow taking different voice inputs to run:
> - Create Item: 'Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220' -> calls POST /api/items -> speaks 'Successfully created book The Catcher in the Rye with ID 3.'
> - Checkout Item: 'Check out item 3' -> calls POST /api/items/3/checkout -> speaks 'Item 3, The Catcher in the Rye, has been checked out.'
> - Error handling (409/404): speaks 'Sorry, item 3 is already checked out.'
> At the end of each run, the app should speak out the completed job using Azure Speech Services.
> Let's set up the new repository, configure `.env`, integrate Azure Speech SDK, and implement the voice command parser and UI."

**Agent Response & Architecture Plan:**
1. Established clean repository structure under `EE471-mini-project-2`.
2. Created `.env`, `.env.example`, and `.gitignore` to safeguard Azure API keys.
3. Migrated existing OOP domain classes (`Book`, `DVD`, `LibraryCollection`) from Week 4 into `custom_classes.py`.
4. Extended `library_app.py` with:
   - Azure Speech SDK (`azure.cognitiveservices.speech`) Text-to-Speech (TTS) synthesizer with fallback to `gTTS`.
   - Speech-to-Text (STT) endpoint accepting audio uploads or client-side transcripts.
   - Comprehensive regex-based natural language command parser covering all 8 endpoints (create, checkout, return, delete, get, list/filter).
5. Enhanced the web interface (`index.html`, `style.css`, `script.js`):
   - Added interactive glowing microphone button with visual state indicators (listening/ready).
   - Real-time conversation bubbles showing user spoken text and AI Librarian response.
   - One-click sample command chips for immediate interactive testing and video demonstration.

---

## 2. Refinement: Natural Language Parsing

**Prompt:**
> "Ensure the voice command parser handles both formal commands (e.g. 'Create item, type book, title X, author Y, pages Z') and conversational variations (e.g. 'Check out item 1', 'Return item 1', 'Show available books', 'Delete item 2'). Also handle 409 conflict and 404 not found states with clear spoken librarian feedback."

**Agent Action:**
Implemented `parse_and_execute_voice_command(spoken_text)` with regex patterns:
- Checkout pattern: `r'(?:check\s*out|borrow)\s+(?:item|book|dvd)?\s*#?(\d+)'`
- Return pattern: `r'return\s+(?:item|book|dvd)?\s*#?(\d+)'`
- Delete pattern: `r'(?:delete|remove)\s+(?:item|book|dvd)?\s*#?(\d+)'`
- Create pattern: structured extraction of `type`, `title`, `author`, and numeric `pages`/`duration`.
- List/Filter pattern: parses `available` (`True`/`False`) and item type (`Book`/`DVD`), dynamically adjusting UI filter states.
- Handled `ItemNotFoundError` and `ItemStateError` returning appropriate 404/409 codes and synthesized error messages.

---

## 3. Azure Speech SDK Synthesis & Web Audio Synchronization

**Prompt:**
> "Ensure the librarian's synthesized audio response plays automatically in the browser after each voice command is completed, and the card inventory grid refreshes live without reloading the page."

**Agent Action:**
- Configured Azure Speech Synthesizer with `en-US-JennyNeural` voice saving to `static/audio/response_<timestamp>.wav`.
- Configured client `script.js` to auto-play the audio element upon receiving `data.audio_url` with cache-busting timestamps.
- Added browser Web Speech API fallback (`window.speechSynthesis`) to guarantee spoken responses in offline or restricted environments.
- Wired live inventory refresh (`loadItems()`) into every successful voice command execution.
