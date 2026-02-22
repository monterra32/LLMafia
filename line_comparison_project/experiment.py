from openai import OpenAI
import requests
import time
import sys
from pathlib import Path
import json
import csv
from datetime import datetime
import re
import argparse
import constants

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


import base64

def get_api_key():
    secrets_file_path = project_root / ".secrets_dict.txt"
    with open(secrets_file_path, "r", encoding="utf-8") as api_file:
        secrets_dict = json.load(api_file)
    api_key = secrets_dict["OPENAI_API_KEY"]
    return api_key

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def describe_image(game_configs):
    num_people = game_configs["num_people"]
    image_path = game_configs["image_path"]
    is_context = game_configs["is_context"]

    before = time.time()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}"
    }
    payload = constants.get_payload(game_configs)

    print("posting")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    after = time.time()
    print(f"Time taken: {after-before} seconds")
    try:
        response_dict = response.json()
        response_dict["duration"] = after-before
        response_dict["prompt"] = [
            payload["messages"][1]["content"][0]["text"]
        ]
        if game_configs["is_context"]:
            response_dict["prompt"].append(payload["messages"][1]["content"][-2]["text"])
        return response_dict
    except Exception as e:
        print(f"ERROR: {e}")
        print(response.text)
        print("i think its a malformed json response")
        return "Error", "Error", "Error", "Error", "Error", "Error"

def parse_ai_response(response_json): #json file type (dict)
    #print(response_json)    # Check if response is valid
    if "choices" not in response_json or len(response_json["choices"]) == 0:
        print(f"ERROR: Invalid response structure: {response_json}")
        raise ValueError("No choices in API response")
    
    # Get content and check if it's None
    response_str = response_json["choices"][0]["message"].get("content")
    
    if response_str is None:
        print(f"ERROR: Content is None. Full response: {json.dumps(response_json, indent=2)}")
        raise ValueError("API returned None for content field")
    response_str = response_json["choices"][0]["message"]["content"]
    #print(response_str)
    if response_str.startswith("```json"):
        response_str = re.sub(r'^```(?:json)?\s*\n', '', response_str)
    if response_str.endswith("```"):
        response_str = re.sub(r'```\s*$', '', response_str)
    content = json.loads(response_str)
    print(content)
    print(response_json)
    response_dict = {
        "prompt": response_json["prompt"],
        "answer": content["Answer"], 
        "reasoning": content["Reasoning"], 
        "confidence": content["Confidence"], 
        "input_tokens": response_json["usage"]["prompt_tokens"], 
        "output_tokens": response_json["usage"]["completion_tokens"], 
        "duration": response_json["duration"]
    }
    print(response_dict)
    return response_dict

def save_to_csv(game_configs, response_list):
    image_path = game_configs["image_path"]

    num_people = game_configs["num_people"]
    is_context = game_configs["is_context"]
    image_name = image_path.split("/")[-1].split(".")[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    save_folder_path = Path((game_configs["folder_path"]))
    csv_path = save_folder_path / f"{timestamp}_{image_name}__{len(response_list)}_runs_{num_people}_people_context-{is_context}.csv"
    response_keys = [
        "answer", 
        "reasoning", 
        "confidence", 
        "input_tokens", 
        "output_tokens", 
        "duration",
    ]
    game_config_keys = [
        "correct_answer",
        "num_people",
        "is_context"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(response_keys + game_config_keys)
        
        for i in range(len(response_list)):
            response = {}
            try:
                response = parse_ai_response(response_list[i])
            except Exception as e:
                for j in response_keys:
                    response[j] = "Error"
            writer.writerow([
                response[response_keys[0]], 
                response[response_keys[1]], 
                response[response_keys[2]], 
                response[response_keys[3]], 
                response[response_keys[4]], 
                response[response_keys[5]], 
                game_configs[game_config_keys[0]], 
                game_configs[game_config_keys[1]], 
                game_configs[game_config_keys[2]]
            ])
    return

def save_to_txt(game_configs, response_list):
    image_path = game_configs["image_path"]
    save_folder_path = Path(game_configs["folder_path"])
    num_people = game_configs["num_people"]
    is_context = game_configs["is_context"]
    correct_answer = game_configs["correct_answer"]
    image_name = image_path.split("/")[-1].split(".")[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    txt_path = save_folder_path / f"{timestamp}_{image_name}__{len(response_list)}_runs_{num_people}_people_context-{is_context}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(json.dumps( str(game_configs) +  "prompt: " + str(response_list[0]["prompt"])))
        f.write("\n")
        f.write("\n")
        f.write("\n")
        f.write("\n")
        f.write("\n")
        for i in range(len(response_list)): 
            f.write(json.dumps(response_list[i]))
            f.write("\n")
            f.write("\n")
            f.write("\n")