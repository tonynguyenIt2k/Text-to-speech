import time
import random
import requests
import json
from capcut_common_task_client import (
    DEFAULT_DEVICE, tts_new_body, common_query, base_headers,
    make_sign_header, compact_json, query_body, checked_json_response,
    BASE
)
from urllib.parse import urlencode

def gen_id():
    return str(random.randint(10**18, 10**19 - 1))

def run_tts_workflow(text, voice="BV074_streaming", resource_id="7102355709945188865", rate="1.0"):
    # Initialize device with random IDs
    device = DEFAULT_DEVICE.copy()
    dev_id = gen_id()
    device["device_id"] = dev_id
    device["iid"] = gen_id()
    device["tdid"] = dev_id

    # 1. Create TTS task
    print(f"Creating TTS task for text: '{text}' using voice: {voice}")
    babi, body = tts_new_body([text], voice, resource_id, rate, device)
    body_text = compact_json(body)
    
    query = common_query(device, babi, include_region=True)
    url = BASE + "/lv/v1/common_task/new?" + urlencode(query)
    
    headers = base_headers(device, body_text, appid=True)
    headers["sign"] = make_sign_header(url, device["appvr"], headers["device-time"], device["tdid"])

    resp = requests.post(url, headers=headers, data=body_text.encode("utf-8"), timeout=60)
    data = checked_json_response(resp, "tts_new")
    
    tasks = data.get("data", {}).get("tasks", [])
    if not tasks:
        print("No tasks returned:", data)
        return None
    
    task = tasks[0]
    task_id = task["id"]
    token = task["token"]
    print(f"Task created successfully. Task ID: {task_id}, Token: {token}")

    # 2. Poll for completion
    for attempt in range(1, 16):
        print(f"Polling task (attempt {attempt}/15)...")
        time.sleep(2)
        
        q_body = query_body(task_id, token, "sami_text_to_speech")
        q_body_text = compact_json(q_body)
        
        q_query = common_query(device, None, include_region=False)
        q_url = BASE + "/lv/v1/common_task/query?" + urlencode(q_query)
        
        q_headers = base_headers(device, q_body_text, appid=True)
        q_headers["sign"] = make_sign_header(q_url, device["appvr"], q_headers["device-time"], device["tdid"])

        q_resp = requests.post(q_url, headers=q_headers, data=q_body_text.encode("utf-8"), timeout=60)
        q_data = checked_json_response(q_resp, "tts_query")
        
        q_tasks = q_data.get("data", {}).get("tasks", [])
        if not q_tasks:
            print("Query returned empty tasks:", q_data)
            continue
            
        q_task = q_tasks[0]
        status = q_task.get("status")
        print(f"Status: {status}")
        
        if status in ["success", "succeed"]:
            payload_str = q_task.get("payload", "{}")
            payload = json.loads(payload_str)
            audio_subtitles = payload.get("audio_subtitles", [])
            if audio_subtitles:
                speech_url = audio_subtitles[0].get("speech_url")
                print("\nSuccess! Speech URL found:")
                print(speech_url)
                return speech_url
            else:
                print("No audio_subtitles in payload:", payload)
                return None
        elif status in ["failed", "error"]:
            print("Task failed:", q_task)
            return None
            
    print("Polling timed out.")
    return None

if __name__ == "__main__":
    run_tts_workflow("Xin chào, đây là giọng đọc thử nghiệm từ CapCut API.")
