import sys
import random
import json
import subprocess

def gen_id():
    return str(random.randint(10**18, 10**19 - 1))

def test():
    device_id = gen_id()
    iid = gen_id()
    device = {
        "device_id": device_id,
        "iid": iid,
        "tdid": device_id
    }
    with open("temp_device.json", "w") as f:
        json.dump(device, f)
    
    print(f"Testing with device_id: {device_id}, iid: {iid}")
    cmd = [
        "./venv/bin/python3",
        "capcut_common_task_client.py",
        "tts-new",
        "--device-json", "temp_device.json",
        "--text", "Xin chào thế giới"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)

if __name__ == "__main__":
    test()
