import os
import time
import random
import uuid
import json
import logging
import shutil
import tempfile
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
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
    version="1.0.0"
)

# Enable CORS for cross-origin requests (GitHub Pages → HF Spaces)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# API models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "BV074_streaming"
    resource_id: Optional[str] = None
    rate: Optional[float] = 1.0

# API endpoints
@app.get("/api/voices")
def get_voices():
    """Retrieve the available voice list with filters metadata."""
    return voices_list

@app.post("/api/tts")
def text_to_speech(payload: TTSRequest):
    """
    Generate audio from text using CapCut TTS.
    Automatically polls the task status and returns the final speech URL.
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

    device = generate_fresh_device()
    
    try:
        # 1. Create TTS task
        logger.info(f"Submitting TTS task: text='{payload.text[:30]}...', voice='{voice}', rate={payload.rate}")
        babi, body = tts_new_body([payload.text], voice, resource_id, str(payload.rate), device)
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
        logger.info(f"TTS task created: task_id={task_id}")

        # 2. Poll the status of the task
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
            logger.info(f"Polling TTS task {task_id} (attempt {attempt}): status={status}")
            
            if status in ["success", "succeed"]:
                payload_str = q_tasks[0].get("payload", "{}")
                task_payload = json.loads(payload_str)
                audio_subtitles = task_payload.get("audio_subtitles", [])
                if audio_subtitles:
                    speech_url = audio_subtitles[0].get("speech_url")
                    return {
                        "status": "success",
                        "task_id": task_id,
                        "speech_url": speech_url,
                        "voice": voice,
                        "display_name": voice_map.get(voice, {}).get("display_name", voice)
                    }
                else:
                    raise HTTPException(status_code=502, detail="No audio URL in CapCut success payload")
            
            elif status in ["failed", "error"]:
                raise HTTPException(status_code=502, detail=f"CapCut engine failed to synthesize audio: {q_tasks[0]}")
                
        raise HTTPException(status_code=504, detail="Polling CapCut TTS task timed out")
        
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
