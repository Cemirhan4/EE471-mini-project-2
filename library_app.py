import os
import re
import time
import tempfile
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

from custom_classes import (
    Book, DVD, LibraryCollection,
    ItemNotFoundError, ItemStateError
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)

SPEECH_KEY = os.getenv('SPEECH_KEY', '').strip()
SPEECH_REGION = os.getenv('SPEECH_REGION', 'germanywestcentral').strip()

# Audio storage directory for synthesized responses
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'static', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Shared Library Collection instance seeded with starter items
library = LibraryCollection()
library.add_item(Book("The Great Gatsby", "F. Scott Fitzgerald", page_count=180))
library.add_item(DVD("Inception", "Christopher Nolan", duration=148))
library.add_item(Book("1984", "George Orwell", page_count=328))
library.add_item(DVD("Arrival", "Denis Villeneuve", duration=116))
library.add_item(Book("The Hobbit", "J.R.R. Tolkien", page_count=310))


# ============================================================================
# AZURE SPEECH SERVICES (TTS & STT)
# ============================================================================

def synthesize_speech(text):
    """Synthesizes text to speech using Azure Speech Services (fallback to gTTS)."""
    filename = f"response_{int(time.time() * 1000)}.wav"
    output_path = os.path.join(AUDIO_DIR, filename)

    # 1. Try Azure Speech SDK
    if SPEECH_KEY and SPEECH_KEY != 'your_azure_speech_key_here':
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return f"/static/audio/{filename}"
        except Exception as e:
            print(f"[AZURE TTS ERROR] {e}")

    # 2. Fallback to gTTS if Azure is unreachable
    try:
        from gtts import gTTS
        mp3_filename = f"response_{int(time.time() * 1000)}.mp3"
        mp3_path = os.path.join(AUDIO_DIR, mp3_filename)
        tts = gTTS(text=text, lang='en')
        tts.save(mp3_path)
        return f"/static/audio/{mp3_filename}"
    except Exception as e:
        print(f"[FALLBACK TTS ERROR] {e}")
        return None


def transcribe_audio_azure(audio_path):
    """Transcribes audio using Azure Speech Services SDK."""
    if SPEECH_KEY and SPEECH_KEY != 'your_azure_speech_key_here':
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
            audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            result = recognizer.recognize_once_async().get()
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return True, result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return False, "No speech recognized."
        except Exception as e:
            return False, str(e)

    # Fallback to SpeechRecognition (Google Free Recognizer)
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
            return True, text
    except Exception as e:
        return False, str(e)


# ============================================================================
# NATURAL LANGUAGE COMMAND PARSER
# ============================================================================

WORD_TO_NUM = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
    'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
    'eighteen': '18', 'nineteen': '19', 'twenty': '20',
    'thirty': '30', 'forty': '40', 'fifty': '50',
    'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5',
    'sixth': '6', 'seventh': '7', 'eighth': '8', 'ninth': '9', 'tenth': '10'
}

def normalize_spoken_text(text):
    """Converts written number words (e.g. 'three') to digits ('3') and trims punctuation."""
    t = text.lower()
    t = re.sub(r'[\.\,\!\?]+', ' ', t)
    for word, digit in WORD_TO_NUM.items():
        t = re.sub(rf'\b{word}\b', digit, t)
    return ' '.join(t.split())

def parse_and_execute_voice_command(spoken_text):
    """
    Parses spoken voice command into library API actions as per Mini Project #2 specs.
    Returns: (spoken_response, http_status, extra_data)
    """
    raw = spoken_text.strip()
    text = normalize_spoken_text(raw)
    print(f"[VOICE INGEST] Raw: '{raw}' -> Normalized: '{text}'")

    # -------------------------------------------------------------
    # 1. CHECKOUT ITEM: e.g. "Check out item 3" / "Checkout three" / "Borrow 3"
    # -------------------------------------------------------------
    match_checkout = re.search(r'(?:check\s*out|borrow)\s*(?:item|book|dvd|number|no\.?|#)?\s*#?(\d+)', text)
    if match_checkout:
        item_id = int(match_checkout.group(1))
        try:
            item = library.get_item(item_id)
            item.checkout()
            response_msg = f"Item {item_id}, '{item.title}', has been checked out."
            return response_msg, 200, {"action": "checkout", "item": item.to_dict()}
        except ItemNotFoundError:
            return f"Sorry, item {item_id} was not found.", 404, {"error": "Not Found"}
        except ItemStateError:
            return f"Sorry, item {item_id} is already checked out.", 409, {"error": "Already Checked Out"}

    # -------------------------------------------------------------
    # 2. RETURN ITEM: e.g. "Return item 3" / "Give back 3"
    # -------------------------------------------------------------
    match_return = re.search(r'(?:return|give\s*back)\s*(?:item|book|dvd|number|no\.?|#)?\s*#?(\d+)', text)
    if match_return:
        item_id = int(match_return.group(1))
        try:
            item = library.get_item(item_id)
            item.return_item()
            response_msg = f"Item {item_id}, '{item.title}', has been returned."
            return response_msg, 200, {"action": "return", "item": item.to_dict()}
        except ItemNotFoundError:
            return f"Sorry, item {item_id} was not found.", 404, {"error": "Not Found"}
        except ItemStateError:
            return f"Sorry, item {item_id} is not currently checked out.", 409, {"error": "Not Checked Out"}

    # -------------------------------------------------------------
    # 3. DELETE ITEM: e.g. "Delete item 3" / "Remove 3"
    # -------------------------------------------------------------
    match_delete = re.search(r'(?:delete|remove)\s*(?:item|book|dvd|number|no\.?|#)?\s*#?(\d+)', text)
    if match_delete:
        item_id = int(match_delete.group(1))
        try:
            item = library.get_item(item_id)
            title = item.title
            library.remove_item(item_id)
            return f"Item {item_id}, '{title}', has been removed from the library.", 200, {"action": "delete", "id": item_id}
        except ItemNotFoundError:
            return f"Sorry, item {item_id} was not found.", 404, {"error": "Not Found"}
        except ItemStateError:
            return f"Sorry, cannot remove item {item_id} because it is currently checked out.", 409, {"error": "Item Checked Out"}

    # -------------------------------------------------------------
    # 4. CREATE ITEM:
    # "Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"
    # -------------------------------------------------------------
    if any(k in text for k in ['create item', 'add item', 'new item', 'add book', 'add dvd', 'create book', 'create dvd']):
        # Extract Type
        item_type = 'book'
        if 'dvd' in text:
            item_type = 'dvd'
        elif 'book' in text:
            item_type = 'book'

        # Extract Title
        title = None
        match_title = re.search(r'title\s+([A-Za-z0-9\s\.\,\'\-]+?)(?=,\s*author|author|\s+by|\s+pages|\s+duration|$)', raw, re.IGNORECASE)
        if match_title:
            title = match_title.group(1).strip().strip(',').strip()
        else:
            # Fallback for "add book The Hobbit by Tolkien"
            match_title_alt = re.search(r'(?:add|create)\s+(?:item|book|dvd)?\s+([A-Za-z0-9\s\.\,\'\-]+?)(?:\s+by|\s+author|\s+pages|\s+duration)', raw, re.IGNORECASE)
            if match_title_alt:
                title = match_title_alt.group(1).strip().strip(',')

        # Extract Author / Director
        author = None
        match_author = re.search(r'(?:author|director|by)\s+([A-Za-z0-9\s\.\,\'\-]+?)(?=,\s*pages|pages|duration|$)', raw, re.IGNORECASE)
        if match_author:
            author = match_author.group(1).strip().strip(',').strip()

        # Extract Count (Pages or Duration)
        count_val = None
        match_count = re.search(r'(?:pages?|duration|length|mins?|minutes?)\s*#?(\d+)', text)
        if match_count:
            count_val = int(match_count.group(1))
        else:
            # Check trailing number
            match_num = re.search(r'(\d+)\s*(?:pages?|mins?|minutes?)?', text)
            if match_num:
                count_val = int(match_num.group(1))

        # Defaults if speech missed optional details
        title = title or "Untitled Work"
        author = author or "Unknown Author"

        if item_type == 'book':
            page_count = count_val or 200
            new_item = Book(title, author, page_count=page_count)
            assigned_id = library.add_item(new_item)
            response_msg = f"Successfully created book '{title}' with ID {assigned_id}."
            return response_msg, 201, {"action": "create", "item": new_item.to_dict()}
        else:
            duration = count_val or 120
            new_item = DVD(title, author, duration=duration)
            assigned_id = library.add_item(new_item)
            response_msg = f"Successfully created DVD '{title}' with ID {assigned_id}."
            return response_msg, 201, {"action": "create", "item": new_item.to_dict()}

    # -------------------------------------------------------------
    # 5. GET ITEM DETAILS: e.g. "Get item 1" / "Show item 1" / "Get 3"
    # -------------------------------------------------------------
    match_get = re.search(r'(?:get|show|details\s+for|what\s+is|info\s+on)\s*(?:item|book|dvd|number|no\.?|#)?\s*#?(\d+)', text)
    if match_get:
        item_id = int(match_get.group(1))
        try:
            item = library.get_item(item_id)
            status_word = "available" if item.is_available else "checked out"
            type_name = "Book" if isinstance(item, Book) else "DVD"
            extra_info = f"{item.page_count} pages" if isinstance(item, Book) else f"{item.duration} minutes"
            response_msg = f"Item {item_id} is a {type_name} titled '{item.title}' by {item.author}, currently {status_word}, length {extra_info}."
            return response_msg, 200, {"action": "get", "item": item.to_dict()}
        except ItemNotFoundError:
            return f"Sorry, item {item_id} was not found.", 404, {"error": "Not Found"}

    # -------------------------------------------------------------
    # 6. LIST / FILTER ITEMS: e.g. "Show available books" / "Show DVDs" / "List all items"
    # -------------------------------------------------------------
    if any(k in text for k in ['list', 'show', 'filter', 'display']):
        available = None
        if 'available' in text:
            available = True
        elif 'checked out' in text or 'borrowed' in text:
            available = False

        item_type = None
        if 'book' in text:
            item_type = Book
        elif 'dvd' in text or 'movie' in text:
            item_type = DVD

        items = library.list_items(available=available, item_type=item_type)
        type_str = "items"
        if item_type == Book:
            type_str = "books"
        elif item_type == DVD:
            type_str = "DVDs"

        avail_str = "available " if available is True else ("checked out " if available is False else "")
        response_msg = f"Found {len(items)} {avail_str}{type_str} in the library."
        return response_msg, 200, {
            "action": "list",
            "filter": {"available": available, "type": "book" if item_type == Book else ("dvd" if item_type == DVD else None)},
            "count": len(items),
            "items": [i.to_dict() for i in items]
        }

    # Default fallback
    return f"I heard '{raw}', but could not match a library command. Try saying 'Create item...', 'Check out item 3', or 'Show available books'.", 400, {"error": "Unrecognized Command"}


# ============================================================================
# STANDARD REST API ENDPOINTS (Week 4 Specification)
# ============================================================================

def error(message, status=400):
    return jsonify({"error": message}), status

@app.route('/')
def index():
    return render_template('index.html')

# POST /api/items — Create a Book or DVD (201, 400)
@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    if not data:
        return error("Invalid JSON input.")

    item_type = data.get('type', '').lower()
    title = data.get('title')
    author = data.get('author')

    if not title or not author or not item_type:
        return error("Fields 'type', 'title', and 'author' are required.")

    if item_type == 'book':
        page_count = data.get('page_count')
        if page_count is None:
            return error("Field 'page_count' is required for books.")
        try:
            page_count = int(page_count)
        except (ValueError, TypeError):
            return error("'page_count' must be an integer.")
        item = Book(title, author, page_count)

    elif item_type == 'dvd':
        duration = data.get('duration')
        if duration is None:
            return error("Field 'duration' is required for DVDs.")
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            return error("'duration' must be an integer.")
        item = DVD(title, author, duration)
    else:
        return error("'type' must be 'book' or 'dvd'.")

    assigned_id = library.add_item(item)
    return jsonify(library.get_item(assigned_id).to_dict()), 201


# GET /api/items — List items; supports ?available=true and ?type=book (200, 400)
@app.route('/api/items', methods=['GET'])
def list_items():
    available_param = request.args.get('available')
    type_param = request.args.get('type')

    available = None
    if available_param is not None:
        if available_param.lower() == 'true':
            available = True
        elif available_param.lower() == 'false':
            available = False
        else:
            return error("'available' filter must be 'true' or 'false'.")

    item_type = None
    if type_param is not None:
        if type_param.lower() == 'book':
            item_type = Book
        elif type_param.lower() == 'dvd':
            item_type = DVD
        else:
            return error("'type' filter must be 'book' or 'dvd'.")

    items = library.list_items(available=available, item_type=item_type)
    return jsonify([item.to_dict() for item in items]), 200


# GET /api/items/<id> — Get one item (200, 404)
@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    try:
        item = library.get_item(item_id)
        return jsonify(item.to_dict()), 200
    except ItemNotFoundError as e:
        return error(str(e), 404)


# PUT /api/items/<id> — Replace all editable fields (200, 400, 404)
@app.route('/api/items/<int:item_id>', methods=['PUT'])
def replace_item(item_id):
    data = request.get_json()
    if not data:
        return error("Invalid JSON input.")

    try:
        item = library.get_item(item_id)
    except ItemNotFoundError as e:
        return error(str(e), 404)

    title = data.get('title')
    author = data.get('author')
    if not title or not author:
        return error("Fields 'title' and 'author' are required.")

    fields = {"title": title, "author": author}
    if isinstance(item, Book):
        page_count = data.get('page_count')
        if page_count is None:
            return error("Field 'page_count' is required for books.")
        try:
            fields['page_count'] = int(page_count)
        except (ValueError, TypeError):
            return error("'page_count' must be an integer.")
    elif isinstance(item, DVD):
        duration = data.get('duration')
        if duration is None:
            return error("Field 'duration' is required for DVDs.")
        try:
            fields['duration'] = int(duration)
        except (ValueError, TypeError):
            return error("'duration' must be an integer.")

    library.update_item(item_id, **fields)
    return jsonify(library.get_item(item_id).to_dict()), 200


# PATCH /api/items/<id> — Change some editable fields (200, 400, 404)
@app.route('/api/items/<int:item_id>', methods=['PATCH'])
def update_item(item_id):
    data = request.get_json()
    if not data:
        return error("Invalid JSON input.")

    try:
        library.get_item(item_id)
    except ItemNotFoundError as e:
        return error(str(e), 404)

    if 'page_count' in data:
        try:
            data['page_count'] = int(data['page_count'])
        except (ValueError, TypeError):
            return error("'page_count' must be an integer.")

    if 'duration' in data:
        try:
            data['duration'] = int(data['duration'])
        except (ValueError, TypeError):
            return error("'duration' must be an integer.")

    library.update_item(item_id, **data)
    return jsonify(library.get_item(item_id).to_dict()), 200


# DELETE /api/items/<id> — Remove an item (204, 404, 409 if checked out)
@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    try:
        library.remove_item(item_id)
        return '', 204
    except ItemNotFoundError as e:
        return error(str(e), 404)
    except ItemStateError as e:
        return error(str(e), 409)


# POST /api/items/<id>/checkout — Check an item out (200, 404, 409 already checked out)
@app.route('/api/items/<int:item_id>/checkout', methods=['POST'])
def checkout_item(item_id):
    try:
        item = library.get_item(item_id)
        message = item.checkout()
        return jsonify({"message": message, "item": item.to_dict()}), 200
    except ItemNotFoundError as e:
        return error(str(e), 404)
    except ItemStateError as e:
        return error(str(e), 409)


# POST /api/items/<id>/return — Return an item (200, 404, 409 not checked out)
@app.route('/api/items/<int:item_id>/return', methods=['POST'])
def return_item(item_id):
    try:
        item = library.get_item(item_id)
        item.return_item()
        return jsonify({"message": "Item returned successfully.", "item": item.to_dict()}), 200
    except ItemNotFoundError as e:
        return error(str(e), 404)
    except ItemStateError as e:
        return error(str(e), 409)


# ============================================================================
# VOICE ACTIVATION API ENDPOINTS (Mini Project #2 Core Feature)
# ============================================================================

@app.route('/api/voice/command', methods=['POST'])
def handle_voice_command():
    """
    Receives recognized text, executes corresponding library API action,
    synthesizes spoken audio response via Azure Speech, and returns result.
    """
    data = request.get_json()
    if not data or not data.get('text', '').strip():
        return error("No voice command text provided.")

    spoken_text = data.get('text').strip()
    response_msg, status_code, extra = parse_and_execute_voice_command(spoken_text)

    # Synthesize audio with Azure TTS
    audio_url = synthesize_speech(response_msg)

    return jsonify({
        "success": (status_code in [200, 201]),
        "status_code": status_code,
        "recognized_text": spoken_text,
        "librarian_response": response_msg,
        "audio_url": audio_url,
        "details": extra
    }), status_code


@app.route('/api/voice/audio-upload', methods=['POST'])
def handle_voice_audio_upload():
    """Receives recorded audio file from browser and runs Azure Speech STT."""
    if 'audio' not in request.files:
        return error("No audio file provided.")

    audio_file = request.files['audio']
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', dir=AUDIO_DIR)
    audio_file.save(temp_wav.name)
    temp_wav.close()

    try:
        success, transcribed_text = transcribe_audio_azure(temp_wav.name)
        if not success:
            return error(f"Speech recognition error: {transcribed_text}")

        # Now execute the parsed voice command
        response_msg, status_code, extra = parse_and_execute_voice_command(transcribed_text)
        audio_url = synthesize_speech(response_msg)

        return jsonify({
            "success": (status_code in [200, 201]),
            "status_code": status_code,
            "recognized_text": transcribed_text,
            "librarian_response": response_msg,
            "audio_url": audio_url,
            "details": extra
        }), status_code
    finally:
        if os.path.exists(temp_wav.name):
            try:
                os.remove(temp_wav.name)
            except Exception:
                pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
