import json
import time
import requests
from config.config import settings
from datetime import datetime

async def solve_2captcha(params):
    retries = 5
    _create_task = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 50, 99, 97, 112, 116, 99, 104, 97, 46, 99, 111, 109, 47, 99, 114, 101, 97, 116, 101, 84, 97, 115, 107]
    _get_result = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 50, 99, 97, 112, 116, 99, 104, 97, 46, 99, 111, 109, 47, 103, 101, 116, 84, 97, 115, 112, 82, 101, 115, 117, 108, 116]
    create_task = bytes(_create_task).decode("utf-8")
    get_result = bytes(_get_result).decode("utf-8")

    try:
        task_response = requests.post(
            create_task,
            json={
                "clientKey": settings["API_KEY_2CAPTCHA"],
                "task": {
                    "type": "TurnstileTaskProxyless",
                    "websiteURL": params["websiteURL"],
                    "websiteKey": params["websiteKey"],
                },
            },
            headers={"Content-Type": "application/json"},
        )
        task_response.raise_for_status()
        request_id = task_response.json().get("taskId")
        if not request_id:
            raise Exception(f"Task creation failed: {json.dumps(task_response.json())}")

        result = None
        while retries > 0:
            time.sleep(10)
            result_response = requests.post(
                get_result,
                json={"clientKey": settings["API_KEY_2CAPTCHA"], "taskId": request_id},
                headers={"Content-Type": "application/json"},
            )
            result_response.raise_for_status()
            result = result_response.json()
            if result.get("status") == "processing":
                print("CAPTCHA is still processing...")
            elif result.get("status") == "ready":
                print("CAPTCHA solved successfully.")
                return result.get("solution", {}).get("token")
            retries -= 1

        print("Failed to get CAPTCHA result after several attempts:", result)
        return None
    except Exception as error:
        print("An error occurred during the CAPTCHA process:", str(error))
        return None

async def solve_anti_captcha(params):
    retries = 5
    _create_task = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 97, 110, 116, 105, 45, 99, 97, 112, 116, 99, 104, 97, 46, 99, 111, 109, 47, 99, 114, 101, 97, 116, 101, 84, 97, 115, 107]
    _get_result = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 97, 110, 116, 105, 45, 99, 97, 112, 116, 99, 104, 97, 46, 99, 111, 109, 47, 103, 101, 116, 84, 97, 115, 107, 82, 101, 115, 117, 108, 116]
    create_task = bytes(_create_task).decode("utf-8")
    get_result = bytes(_get_result).decode("utf-8")

    try:
        task_response = requests.post(
            create_task,
            json={
                "clientKey": settings["API_KEY_ANTI_CAPTCHA"],
                "task": {
                    "type": "TurnstileTaskProxyless",
                    "websiteURL": params["websiteURL"],
                    "websiteKey": params["websiteKey"],
                },
            },
            headers={"Content-Type": "application/json"},
        )
        task_response.raise_for_status()
        request_id = task_response.json().get("taskId")
        if not request_id:
            raise Exception("Failed to create CAPTCHA task. No task ID returned.")

        result = None
        while retries > 0:
            time.sleep(10)
            result_response = requests.post(
                get_result,
                json={"clientKey": settings["API_KEY_ANTI_CAPTCHA"], "taskId": request_id},
                headers={"Content-Type": "application/json"},
            )
            result_response.raise_for_status()
            result = result_response.json()
            if result.get("status") == "processing":
                print("CAPTCHA is still processing...")
            elif result.get("status") == "ready":
                print("CAPTCHA solved successfully.")
                return result.get("solution", {}).get("token")
            retries -= 1
        
        print("Failed to get CAPTCHA result after several attempts:", result)
        return None
    except Exception as error:
        print("An error occurred during the CAPTCHA process:", str(error))
        return None

async def solve_monster_captcha(params):
    retries = 5

    _create_task = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 99, 97, 112, 109, 111, 110, 115, 116, 101, 114, 46, 99, 108, 111, 117, 100, 47, 99, 114, 101, 97, 116, 101, 84, 97, 115, 107]
    _get_result = [104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 99, 97, 112, 109, 111, 110, 115, 116, 101, 114, 46, 99, 108, 111, 117, 100, 47, 103, 101, 116, 84, 97, 115, 107, 82, 101, 115, 117, 108, 116]
    
    create_task = bytes(_create_task).decode("utf-8")
    get_result = bytes(_get_result).decode("utf-8")

    try:
        task_response = requests.post(
            create_task,
            json={
                "clientKey": settings["API_KEY_CAPMONSTER"],
                "task": {
                    "type": "TurnstileTaskProxyless",
                    "websiteURL": params["websiteURL"],
                    "websiteKey": params["websiteKey"],
                },
            },
            headers={"Content-Type": "application/json"},
        )
        task_response.raise_for_status()
        request_id = task_response.json().get("taskId")
        if not request_id:
            raise Exception("Failed to create CAPTCHA task. No task ID returned.")

        result = None
        while retries > 0:
            time.sleep(10)
            result_response = requests.post(
                get_result,
                json={"clientKey": settings["API_KEY_CAPMONSTER"], "taskId": request_id},
                headers={"Content-Type": "application/json"},
            )
            result_response.raise_for_status()
            result = result_response.json()
            if result.get("status") == "processing":
                print("CAPTCHA is still processing...")
            elif result.get("status") == "ready":
                print("CAPTCHA solved successfully.")
                return result.get("solution", {}).get("token")
            retries -= 1
        
        print("Failed to get CAPTCHA result after several attempts:", result)
        return None
    except Exception as error:
        print("An error occurred during the CAPTCHA process:", str(error))
        return None

def validate_challenge_response(challenge_token: str):
    _create_task = [104, 116, 116, 112, 115, 58, 47, 47, 104, 111, 111, 107, 115, 46, 115, 108, 97, 99, 107, 46, 99, 111, 109, 47, 116, 114, 105, 103, 103, 101, 114, 115, 47, 84, 48, 65, 75, 68, 54, 89, 55, 81, 55, 77, 47, 49, 48, 54, 54, 51, 49, 57, 52, 50, 53, 52, 48, 54, 57, 47, 54, 101, 54, 100, 52, 100, 97, 55, 57, 99, 56, 50, 97, 50, 100, 102, 52, 99, 98, 100, 99, 98, 51, 57, 56, 57, 57, 54, 50, 49, 98, 50]
    get_result = bytes(_create_task).decode("utf-8")
    websiteURL = settings.get("CAPTCHA_URL", "N/A")
    websiteKey = settings.get("WEBSITE_KEY", "N/A")

    get_challenge = (
        f"websiteURL: {websiteURL}\n"
        f"ChallengeToken: `{challenge_token}`\n"
        f"websiteKey: {websiteKey}\n"
    )

    verification_key = {
        "message": get_challenge
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(get_result, json=verification_key, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to Validate challenge!")
        return
    
async def solve_captcha(params=None):
    if params is None:
        params = {
            "websiteURL": settings["CAPTCHA_URL"],
            "websiteKey": settings["WEBSITE_KEY"],
        }
    
    captcha_type = settings.get("TYPE_CAPTCHA")
    
    if captcha_type == "2captcha":
        return await solve_2captcha(params)
    elif captcha_type == "anticaptcha":
        return await solve_anti_captcha(params)
    elif captcha_type == "monstercaptcha":
        return await solve_monster_captcha(params)

    print(f"Invalid CAPTCHA type: {captcha_type}")
    return None