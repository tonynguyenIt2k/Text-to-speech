import requests
import json
import os

def test_integration():
    print("1. Generating audio via local TTS...")
    tts_url = "http://127.0.0.1:8000/api/tts"
    payload = {
        "text": "Chào mừng bạn đến với hệ thống nhận dạng giọng nói",
        "voice": "BV074_streaming"
    }
    
    tts_resp = requests.post(tts_url, json=payload, timeout=60)
    if tts_resp.status_code != 200:
        print("TTS Generation failed:", tts_resp.text)
        return
        
    tts_data = tts_resp.json()
    speech_url = tts_data["speech_url"]
    print("TTS Speech URL:", speech_url)
    
    print("\n2. Downloading audio file...")
    audio_resp = requests.get(speech_url, timeout=30)
    if audio_resp.status_code != 200:
        print("Failed to download audio:", audio_resp.status_code)
        return
        
    audio_path = "test_audio_temp.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio_resp.content)
    print(f"Downloaded audio to {audio_path}")
    
    try:
        print("\n3. Uploading audio to local STT endpoint...")
        stt_url = "http://127.0.0.1:8000/api/stt"
        files = {
            "file": (audio_path, open(audio_path, "rb"), "audio/mpeg")
        }
        data = {
            "language": "vi-VN",
            "use_translation": "false",
            "translation_language": "vi-VN"
        }
        
        stt_resp = requests.post(stt_url, files=files, data=data, timeout=120)
        if stt_resp.status_code != 200:
            print("STT Request failed:", stt_resp.text)
            return
            
        stt_data = stt_resp.json()
        print("\nSTT Response received successfully!")
        print("Task ID:", stt_data.get("task_id"))
        print("Duration:", stt_data.get("duration_ms"), "ms")
        print("\nUtterances:")
        for u in stt_data.get("utterances", []):
            print(f"  [{u['start_time']}ms -> {u['end_time']}ms] {u['text']}")
            
    finally:
        # Clean up temp audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"\nCleaned up {audio_path}")

if __name__ == "__main__":
    test_integration()
