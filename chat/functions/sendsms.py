import requests
import sys, requests, urllib

apikey = 'e426b4c896aa557d069880e581a11c5b'
sendername = 'KENSHi'

def send_sms(number, message):
    url = 'https://api.semaphore.co/api/v4/messages'
    data = {
        'apikey': apikey,
        'number': number,
        'message': message,
        'sendername': sendername,
    }

    try:
        resp = requests.post(url, data=data)
        print(f"HTTP Status Code: {resp.status_code}")
        print(f"Response Text: {resp.text}")
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json and isinstance(resp_json, list):
            status = resp_json[0].get('status', 'Unknown')
            print(f"Message status: {status}")
            return status
        else:
            print("Unexpected JSON structure.")
    except Exception as e:
        print(f"Exception: {e}")
    
    return 'FAILED'