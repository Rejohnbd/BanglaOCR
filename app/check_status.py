# check_status.py
import requests
import time
import sys

task_id = sys.argv[1] if len(sys.argv) > 1 else input("Enter Task ID: ")

while True:
    resp = requests.get(f"http://localhost:8000/status/{task_id}")
    data = resp.json()
    
    print(f"Status: {data.get('status')}")
    
    if data.get('status') == 'completed':
        print(f"✅ Done! Found {data.get('count')} voters")
        print(f"📥 Download: http://localhost:8000/download/{task_id}")
        break
    elif data.get('status') == 'failed':
        print(f"❌ Failed: {data.get('error')}")
        break
    
    time.sleep(3)