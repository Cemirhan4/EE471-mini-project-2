# EE471 — Mini Project #2: Voice-Activated Library App

An intelligent, voice-operated library management system powered by **Flask** and **Azure Cognitive Speech Services**. Users can add, checkout, return, query, and delete library items (Books and DVDs) hands-free using spoken natural language commands, and receive audio feedback spoken by an AI librarian.

---

## 🚀 Features

- **Hands-Free Voice Activation:** Speak naturally to the AI librarian to manage your inventory.
- **Azure Cognitive Speech Services Integration:**
  - Real-time Speech-to-Text (STT) for processing spoken library commands.
  - Neural Text-to-Speech (TTS) delivering spoken audio confirmations for every action.
- **Full RESTful Library API:**
  - `POST /api/items`: Create Book or DVD (201 Created).
  - `GET /api/items`: List items with query filters (`?available=true`, `?type=book`).
  - `GET /api/items/<id>`: Retrieve item details.
  - `PUT /api/items/<id>`: Full update of editable fields.
  - `PATCH /api/items/<id>`: Partial update of editable fields.
  - `DELETE /api/items/<id>`: Remove an item (with safety checks against checked-out items).
  - `POST /api/items/<id>/checkout`: Check out an available item (409 Conflict if already checked out).
  - `POST /api/items/<id>/return`: Return a checked out item (409 Conflict if not checked out).
- **Graceful Audio & Text Fallback:** Automatic fallback to browser Web Speech API / gTTS ensuring uninterrupted demo performance.
- **Security-First Architecture:** Azure subscription keys are strictly stored in `.env` and kept out of Git version control.

---

## 🎙️ Spoken Voice Commands & Librarian Responses

| Action | Example User Spoken Input | Backend Endpoint | Librarian Audio Response |
|---|---|---|---|
| **Create Book** | *"Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"* | `POST /api/items` | *"Successfully created book 'The Catcher in the Rye' with ID 3."* |
| **Create DVD** | *"Create item, type dvd, title Inception, author Christopher Nolan, duration 148"* | `POST /api/items` | *"Successfully created DVD 'Inception' with ID 4."* |
| **Checkout Item** | *"Check out item 3"* | `POST /api/items/3/checkout` | *"Item 3, 'The Catcher in the Rye', has been checked out."* |
| **Checkout Error (409)** | *"Check out item 3"* *(when already checked out)* | `POST /api/items/3/checkout` | *"Sorry, item 3 is already checked out."* |
| **Return Item** | *"Return item 3"* | `POST /api/items/3/return` | *"Item 3, 'The Catcher in the Rye', has been returned."* |
| **Return Error (409)** | *"Return item 3"* *(when not checked out)* | `POST /api/items/3/return` | *"Sorry, item 3 is not currently checked out."* |
| **Get Details** | *"Get item 1"* | `GET /api/items/1` | *"Item 1 is a Book titled 'The Great Gatsby' by F. Scott Fitzgerald, currently available..."* |
| **Filter Books** | *"Show available books"* | `GET /api/items?available=true&type=book` | *"Found 3 available books in the library."* |
| **Filter DVDs** | *"Show DVDs"* | `GET /api/items?type=dvd` | *"Found 2 DVDs in the library."* |
| **Delete Item** | *"Delete item 3"* | `DELETE /api/items/3` | *"Item 3, 'The Catcher in the Rye', has been removed from the library."* |

---

## 🛠️ Installation & Setup

### 1. Clone & Navigate
```bash
git clone https://github.com/Cemirhan4/EE471-mini-project-2.git
cd EE471-mini-project-2
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Azure Speech credentials:
```bash
cp .env.example .env
```
Inside `.env`:
```env
SPEECH_KEY=your_azure_speech_key_here
SPEECH_REGION=germanywestcentral
```

### 4. Run the Application
```bash
python library_app.py
```
Open your browser and navigate to:
```
http://localhost:5003
```

---

## 📂 Project Directory Structure

```
EE471-mini-project-2/
├── .env                  # Protected credentials (Azure API keys)
├── .env.example          # Environment template
├── .gitignore            # Ignores .env, audio caches, __pycache__, recordings
├── custom_classes.py     # OOP domain model: MediaItem, Book, DVD, LibraryCollection
├── library_app.py        # Flask app, RESTful endpoints & Azure Speech controller
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Glassmorphic Library UI with voice activation hub
├── static/
│   ├── style.css         # Responsive styling matching assignment design
│   ├── script.js         # Voice recognition & dynamic card grid controller
│   └── audio/            # Auto-generated synthesized librarian responses
├── PROMPTS.md            # AI interaction and vibe-coding transcripts
└── README.md             # Project documentation
```

---

## 📹 Deliverables Checklist

- [x] Clean, functional GitHub repository
- [x] Environment variables protected by `.gitignore`
- [x] All 8 assignment REST endpoints fully functional
- [x] Voice activation and TTS responses working for all endpoints
- [ ] `video-demo.avi`: Screen recording of testing each endpoint with voice inputs
- [ ] `video-explanation.avi`: Screen recording explaining the code architecture
- [x] `PROMPTS.md`: Complete vibe coding records
