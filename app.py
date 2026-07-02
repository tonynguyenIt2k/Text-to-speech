import os
import time
import random
import uuid
import json
import logging
import shutil
import tempfile
import re
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from urllib.parse import urlencode

# Import key parameters and functions from capcut_common_task_client
from capcut_common_task_client import (
    DEFAULT_DEVICE, tts_new_body, stt_new_body, common_query, base_headers,
    make_sign_header, compact_json, query_body, checked_json_response,
    upload_audio_file, BASE
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("capcut-api-server")

app = FastAPI(
    title="CapCut TTS & STT API Server",
    description="A modern API wrapper around CapCut's internal TTS and STT engine.",
    version="1.1.0"
)

# Enable CORS for cross-origin requests (GitHub Pages → HF Spaces)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for storing merged audio files
AUDIO_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "audio_output")
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Load voices configuration
VOICES_FILE = os.path.join(os.path.dirname(__file__), "Voice.json")
voices_list = []
voice_map = {}

if os.path.exists(VOICES_FILE):
    try:
        with open(VOICES_FILE, "r", encoding="utf-8") as f:
            voices_list = json.load(f)
            for v in voices_list:
                voice_map[v["voice_type"]] = {
                    "resource_id": v["resource_id"],
                    "lang": v["lang"],
                    "display_name": v["display_name"]
                }
        logger.info(f"Loaded {len(voices_list)} voices from Voice.json")
    except Exception as e:
        logger.error(f"Error loading Voice.json: {e}")
else:
    logger.warning("Voice.json not found in workspace!")

# Helper to generate fresh, unregistered ByteDance device parameters
def generate_fresh_device() -> dict:
    device = DEFAULT_DEVICE.copy()
    dev_id = str(random.randint(10**18, 10**19 - 1))
    device["device_id"] = dev_id
    device["iid"] = str(random.randint(10**18, 10**19 - 1))
    device["tdid"] = dev_id
    return device

# ─── English to Vietnamese Phonetic mapping for mixed language ───────────────
ENGLISH_TO_VI_PHONETIC = {
    # Brand/Tech Names
    "facebook": "phây-búc",
    "google": "gu-gồ",
    "youtube": "u-túp",
    "youtube channel": "kênh u-túp",
    "tiktok": "tíc-tốc",
    "github": "gít-hắp",
    "huggingface": "hắc-ghinh phây-xơ",
    "hugging face": "hắc-ghinh phây-xơ",
    "chatgpt": "chát-gi-pi-ti",
    "gpt": "gi-pi-ti",
    "openai": "ô-pen-ai",
    "microsoft": "mai-crô-sóp",
    "apple": "áp-pồ",
    "iphone": "ai-phôn",
    "ipad": "ai-pát",
    "macbook": "mác-búc",
    "android": "an-droi",
    "samsung": "sam-sung",
    "capcut": "cáp-cắt",
    
    # Common tech words
    "ai": "ai",
    "api": "a-pi-ai",
    "server": "sơ-vơ",
    "client": "clai-ân",
    "web": "quép",
    "website": "quép-sai",
    "app": "áp",
    "application": "áp-li-kê-sơn",
    "code": "cốt",
    "coder": "cố-đơ",
    "developer": "đê-ve-lơ-pơ",
    "dev": "đép",
    "designer": "đi-zai-nơ",
    "test": "tét",
    "tester": "tét-tơ",
    "user": "u-sơ",
    "admin": "át-min",
    "file": "phai",
    "folder": "phôn-đơ",
    "data": "đa-ta",
    "database": "đa-ta-bây",
    "internet": "in-tơ-nét",
    "network": "nét-uốc",
    "online": "on-lai",
    "offline": "off-lai",
    "link": "linh",
    "url": "u-rờ-lờ",
    "click": "clích",
    "check": "chếch",
    "update": "úp-đét",
    "upgrade": "úp-grết",
    "download": "đao-loát",
    "upload": "úp-loát",
    "setup": "sét-úp",
    "install": "in-sto",
    "run": "răn",
    "start": "stát",
    "stop": "stóp",
    "cancel": "can-xơ",
    "error": "e-rơ",
    "bug": "bắc",
    "debug": "đi-bắc",
    "log": "lốc",
    "login": "lăng-in",
    "logout": "lăng-ao",
    "register": "re-gít-tơ",
    "password": "pát-uốc",
    "username": "u-sơ-nêm",
    "email": "i-meo",
    
    # Audio/Video words
    "voice": "voi-xơ",
    "studio": "su-ti-đi-ô",
    "text to speech": "tếch tu spít",
    "speech to text": "spít tu tếch",
    "tts": "tê-tê-ét",
    "stt": "ét-tê-tê",
    "audio": "ao-đi-ô",
    "video": "vi-đê-ô",
    "clip": "clíp",
    "stream": "sờ-trim",
    "livestream": "lai-sờ-trim",
    "live": "lai",
    "play": "plây",
    "pause": "po",
    "mute": "miu",
    "volume": "vô-lum",
    "sound": "sao-đơ",
    "karaoke": "ca-ra-ô-kê",
    
    # Common conversational English words in Vietnamese
    "like": "lai",
    "love": "lớp",
    "share": "se",
    "subscribe": "súp-sờ-crai",
    "comment": "com-mèn",
    "post": "pốt",
    "blog": "blốc",
    "hot": "hót",
    "cool": "cu",
    "ok": "ô-kê",
    "okay": "ô-kê",
    "yes": "dét",
    "no": "nô",
    "hi": "hai",
    "hello": "hê-lô",
    "bye": "bai",
    "goodbye": "gút-bai",
    "thanks": "thenh-kiu",
    "thank you": "thenh-kiu",
    "sorry": "so-ri",
    "please": "pli",
    "team": "tim",
    "project": "prô-jếch",
    "task": "tát",
    "deadline": "đét-lai",
    "meeting": "mit-tinh",
    "group": "grúp",
    "zoom": "zum",
    "call": "con",
    "chat": "chát",
    "free": "phờ-ri",
    "sale": "seo",
    "shop": "sóp",
    "store": "sto",
    "brand": "bờ-ren",
    "marketing": "mác-két-tinh",
    "pr": "pi-a",
    "event": "i-ven",
    "view": "viu",
    "follow": "phô-lô",
    "game": "ghêm",
    "gamer": "ghê-mơ",
    "live game": "lai ghêm",
    "music": "miu-zích",
    "song": "soong",
    "singer": "sinh-ơ",
    "fan": "phan",
    "idol": "ai-đồ",
    "show": "sô",
    "review": "ri-viu",
    "vlog": "vờ-lốc",
    "vlogger": "vờ-lốc-gơ",
    "camera": "ca-me-ra",
    "smartwatch": "sờ-mát-uốc",
    "laptop": "láp-tóp",
    "pc": "pi-xi",
    "wifi": "quai-phai",
    "bluetooth": "blu-tút",
    "sim": "sim",
    "card": "cát",
    "key": "ki",
}

def convert_english_to_vi_phonetic(text: str) -> str:
    # Sort keys by length descending to match longer phrases first
    sorted_words = sorted(ENGLISH_TO_VI_PHONETIC.keys(), key=len, reverse=True)
    
    for eng_word in sorted_words:
        vi_equivalent = ENGLISH_TO_VI_PHONETIC[eng_word]
        # Match complete word boundaries case-insensitively
        pattern = re.compile(r'\b' + re.escape(eng_word) + r'\b', re.IGNORECASE)
        text = pattern.sub(vi_equivalent, text)
    return text

# ─── Text Chunking for Long TTS ──────────────────────────────────────────────
# CapCut TTS has a ~280 character limit per request.
# Split long texts at sentence boundaries to stay within the limit.
TTS_CHAR_LIMIT = 280

def split_text_into_chunks(text: str, max_chars: int = TTS_CHAR_LIMIT) -> List[str]:
    """
    Split long text into chunks that fit within CapCut's character limit.
    Splits at sentence boundaries (., !, ?, newlines) first, then falls back
    to splitting at commas/semicolons, and finally at word boundaries.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    # Split into sentences first
    # This regex splits after sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?。！？\n])\s*', text)
    # Filter out empty strings
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence would exceed the limit
        if len(current_chunk) + len(sentence) + 1 > max_chars:
            # Save what we have so far
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # If a single sentence exceeds the limit, split it further
            if len(sentence) > max_chars:
                sub_parts = _split_long_sentence(sentence, max_chars)
                # Add all but the last sub-part as complete chunks
                for part in sub_parts[:-1]:
                    chunks.append(part.strip())
                # Start new chunk with the last sub-part
                current_chunk = sub_parts[-1]
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    """Split a single long sentence at commas/semicolons, then word boundaries, then character boundaries."""
    # Try splitting at commas and semicolons first
    parts = re.split(r'(?<=[,;，；])\s*', sentence)
    
    result = []
    current = ""

    for part in parts:
        if len(current) + len(part) + 1 > max_chars:
            if current:
                result.append(current.strip())
                current = ""
            # If still too long, split at word boundaries
            if len(part) > max_chars:
                words = part.split()
                word_chunk = ""
                for word in words:
                    if len(word) > max_chars:
                        # Word itself is too long — split at character boundaries
                        if word_chunk:
                            result.append(word_chunk.strip())
                            word_chunk = ""
                        while len(word) > max_chars:
                            result.append(word[:max_chars])
                            word = word[max_chars:]
                        current = word
                    elif len(word_chunk) + len(word) + 1 > max_chars:
                        if word_chunk:
                            result.append(word_chunk.strip())
                        word_chunk = word
                    else:
                        word_chunk = (word_chunk + " " + word).strip()
                if word_chunk:
                    current = word_chunk
            else:
                current = part
        else:
            current = (current + " " + part).strip() if current else part

    if current.strip():
        result.append(current.strip())

    return result


def _synthesize_single_chunk(text: str, voice: str, resource_id: str, rate: str, device: dict) -> str:
    """
    Synthesize a single text chunk via CapCut TTS.
    Returns the speech_url on success, raises HTTPException on failure.
    """
    babi, body = tts_new_body([text], voice, resource_id, rate, device)
    body_text = compact_json(body)

    query = common_query(device, babi, include_region=True)
    url = BASE + "/lv/v1/common_task/new?" + urlencode(query)

    headers = base_headers(device, body_text, appid=True)
    headers["sign"] = make_sign_header(url, device["appvr"], headers["device-time"], device["tdid"])

    resp = requests.post(url, headers=headers, data=body_text.encode("utf-8"), timeout=30)
    data = checked_json_response(resp, "tts_new")

    tasks = data.get("data", {}).get("tasks", [])
    if not tasks:
        raise HTTPException(status_code=502, detail=f"CapCut task creation failed: {data}")

    task_id = tasks[0]["id"]
    token = tasks[0]["token"]

    # Poll the status of the task
    max_attempts = 15
    for attempt in range(1, max_attempts + 1):
        time.sleep(1.5)

        q_body = query_body(task_id, token, "sami_text_to_speech")
        q_body_text = compact_json(q_body)

        q_query = common_query(device, None, include_region=False)
        q_url = BASE + "/lv/v1/common_task/query?" + urlencode(q_query)

        q_headers = base_headers(device, q_body_text, appid=True)
        q_headers["sign"] = make_sign_header(q_url, device["appvr"], q_headers["device-time"], device["tdid"])

        q_resp = requests.post(q_url, headers=q_headers, data=q_body_text.encode("utf-8"), timeout=30)
        q_data = checked_json_response(q_resp, "tts_query")

        q_tasks = q_data.get("data", {}).get("tasks", [])
        if not q_tasks:
            continue

        status = q_tasks[0].get("status")
        logger.info(f"Polling TTS chunk task {task_id} (attempt {attempt}): status={status}")

        if status in ["success", "succeed"]:
            payload_str = q_tasks[0].get("payload", "{}")
            task_payload = json.loads(payload_str)
            audio_subtitles = task_payload.get("audio_subtitles", [])
            if audio_subtitles:
                return audio_subtitles[0].get("speech_url")
            else:
                raise HTTPException(status_code=502, detail="No audio URL in CapCut success payload")

        elif status in ["failed", "error"]:
            raise HTTPException(status_code=502, detail=f"CapCut engine failed to synthesize audio chunk: {q_tasks[0]}")

    raise HTTPException(status_code=504, detail="Polling CapCut TTS task timed out")


def _cleanup_old_audio_files():
    """Remove audio output files older than 1 hour."""
    try:
        now = time.time()
        for fname in os.listdir(AUDIO_OUTPUT_DIR):
            fpath = os.path.join(AUDIO_OUTPUT_DIR, fname)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 3600:
                os.remove(fpath)
    except Exception as e:
        logger.warning(f"Cleanup old audio files error: {e}")

# ─── API Models ───────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "BV074_streaming"
    resource_id: Optional[str] = None
    rate: Optional[float] = 1.0

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/voices")
def get_voices():
    """Retrieve the available voice list with filters metadata."""
    return voices_list

@app.get("/api/audio/{filename}")
def serve_audio(filename: str):
    """Serve a merged audio file from the audio_output directory."""
    file_path = os.path.join(AUDIO_OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

@app.post("/api/tts")
def text_to_speech(payload: TTSRequest, request: Request):
    """
    Generate audio from text using CapCut TTS.
    Supports long texts by automatically splitting into chunks and merging results.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Resolve resource_id if not explicitly provided
    voice = payload.voice
    resource_id = payload.resource_id
    
    if not resource_id:
        if voice in voice_map:
            resource_id = voice_map[voice]["resource_id"]
        else:
            # Default to backup voice if not found
            voice = "BV074_streaming"
            resource_id = "7102355709945188865"

    # Preprocess text if selected voice is Vietnamese to optimize English pronunciations
    text_to_synthesize = payload.text.strip()
    is_vietnamese_voice = False
    
    if voice in voice_map:
        is_vietnamese_voice = "vi" in voice_map[voice]["lang"].lower()
    else:
        # Default voice (BV074_streaming) is Vietnamese
        is_vietnamese_voice = True
        
    if is_vietnamese_voice:
        original_text = text_to_synthesize
        text_to_synthesize = convert_english_to_vi_phonetic(text_to_synthesize)
        if text_to_synthesize != original_text:
            logger.info(f"Substituted English words for Vietnamese voice: '{original_text[:40]}' -> '{text_to_synthesize[:40]}'")

    # Split text into chunks if it exceeds the character limit
    chunks = split_text_into_chunks(text_to_synthesize)
    total_chunks = len(chunks)
    logger.info(f"TTS request: {len(payload.text)} chars → {total_chunks} chunk(s), voice='{voice}', rate={payload.rate}")
    
    try:
        if total_chunks == 1:
            # ── Single chunk: original fast path ──
            device = generate_fresh_device()
            speech_url = _synthesize_single_chunk(chunks[0], voice, resource_id, str(payload.rate), device)
            return {
                "status": "success",
                "speech_url": speech_url,
                "voice": voice,
                "display_name": voice_map.get(voice, {}).get("display_name", voice),
                "chunks": 1,
            }
        else:
            # ── Multiple chunks: synthesize each, download, merge ──
            speech_urls = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{total_chunks}: '{chunk[:40]}...' ({len(chunk)} chars)")
                # Use a fresh device for each chunk to avoid rate limiting
                device = generate_fresh_device()
                url = _synthesize_single_chunk(chunk, voice, resource_id, str(payload.rate), device)
                speech_urls.append(url)

            # Download all audio chunks and concatenate MP3 data
            merged_data = bytearray()
            for i, url in enumerate(speech_urls):
                logger.info(f"Downloading chunk {i+1}/{total_chunks} audio...")
                audio_resp = requests.get(url, timeout=60)
                if audio_resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Failed to download audio chunk {i+1}")
                merged_data.extend(audio_resp.content)

            # Save merged MP3 file
            _cleanup_old_audio_files()
            output_filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
            output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)
            with open(output_path, "wb") as f:
                f.write(merged_data)
            
            logger.info(f"Merged {total_chunks} chunks → {output_filename} ({len(merged_data)} bytes)")

            # Build the URL for the merged audio file
            base_url = str(request.base_url).rstrip("/")
            merged_speech_url = f"{base_url}/api/audio/{output_filename}"

            return {
                "status": "success",
                "speech_url": merged_speech_url,
                "voice": voice,
                "display_name": voice_map.get(voice, {}).get("display_name", voice),
                "chunks": total_chunks,
            }
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stt")
def speech_to_text(
    file: UploadFile = File(...),
    language: str = Form("vi-VN"),
    translation_language: str = Form("vi-VN"),
    use_translation: bool = Form(False)
):
    """
    Upload an audio/video file and perform subtitle recognition.
    Automatically uploads the file to VOD space, triggers the STT task, polls, and returns parsed utterances.
    """
    suffix = os.path.splitext(file.filename)[1]
    if not suffix:
        suffix = ".mp3" # default fallback
        
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, f"audio_{uuid.uuid4().hex}{suffix}")
    
    try:
        # Save uploaded file to temp path
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        device = generate_fresh_device()
        
        # 1. Upload to CapCut VOD Space
        logger.info(f"Uploading file {file.filename} to CapCut VOD space...")
        upload_info = upload_audio_file(temp_path, device)
        logger.info(f"VOD Upload successful. vid={upload_info['vid']}, duration={upload_info['duration_ms']}ms")
        
        # 2. Create STT task
        babi, body = stt_new_body(
            audio_vid=upload_info["vid"],
            audio_md5=upload_info["md5"],
            duration_ms=upload_info["duration_ms"] or 10000,
            language=language,
            translation_language=translation_language,
            use_translation=use_translation
        )
        body_text = compact_json(body)
        
        query = common_query(device, babi, include_region=True)
        url = BASE + "/lv/v1/common_task/new?" + urlencode(query)
        
        headers = base_headers(device, body_text, appid=False) # STT is appid=False
        headers["sign"] = make_sign_header(url, device["appvr"], headers["device-time"], device["tdid"])

        resp = requests.post(url, headers=headers, data=body_text.encode("utf-8"), timeout=30)
        data = checked_json_response(resp, "stt_new")
        
        tasks = data.get("data", {}).get("tasks", [])
        if not tasks:
            raise HTTPException(status_code=502, detail=f"CapCut STT task creation failed: {data}")
            
        task_id = tasks[0]["id"]
        token = tasks[0]["token"]
        logger.info(f"STT task created: task_id={task_id}")

        # 3. Poll for completion
        max_attempts = 30
        for attempt in range(1, max_attempts + 1):
            time.sleep(2.0)
            
            q_body = query_body(task_id, token, "cc_audio_subtitle_asr")
            q_body_text = compact_json(q_body)
            
            q_query = common_query(device, None, include_region=False)
            q_url = BASE + "/lv/v1/common_task/query?" + urlencode(q_query)
            
            q_headers = base_headers(device, q_body_text, appid=False) # STT query is appid=False
            q_headers["sign"] = make_sign_header(q_url, device["appvr"], q_headers["device-time"], device["tdid"])

            q_resp = requests.post(q_url, headers=q_headers, data=q_body_text.encode("utf-8"), timeout=30)
            q_data = checked_json_response(q_resp, "stt_query")
            
            q_tasks = q_data.get("data", {}).get("tasks", [])
            if not q_tasks:
                continue
                
            status = q_tasks[0].get("status")
            logger.info(f"Polling STT task {task_id} (attempt {attempt}): status={status}")
            
            if status in ["success", "succeed"]:
                payload_str = q_tasks[0].get("payload", "{}")
                task_payload = json.loads(payload_str)
                utterances = task_payload.get("utterances", [])
                
                return {
                    "status": "success",
                    "task_id": task_id,
                    "duration_ms": upload_info["duration_ms"],
                    "utterances": utterances
                }
            
            elif status in ["failed", "error"]:
                raise HTTPException(status_code=502, detail=f"CapCut engine failed to recognize subtitles: {q_tasks[0]}")
                
        raise HTTPException(status_code=504, detail="Polling CapCut STT task timed out")
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temp file
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to delete temp dir {temp_dir}: {e}")

# Serves status endpoint
@app.get("/api/status")
def system_status():
    return {
        "status": "online",
        "voices_loaded": len(voices_list),
        "timestamp": time.time()
    }

# Serves the frontend single-page application
@app.get("/")
def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "static/index.html not found"})

# Mount static folder if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
