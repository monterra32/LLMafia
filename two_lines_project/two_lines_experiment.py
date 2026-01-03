from re import A
from socketserver import ForkingMixIn
from tkinter import W
from openai import OpenAI
import requests
import time
import sys
from pathlib import Path
import json
import csv
from datetime import datetime
import re

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import constants.experiment_constants
import base64





image_path = str(Path(__file__).parent / "two_lines_image.png")

api_file = open(".secrets_dict.txt", "r")
secrets_dict = json.load(api_file)
api_file.close()
api_key = secrets_dict["OPENAI_API_KEY"]


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def describe_image(image_path, num_people):
    before = time.time()
    base64_image = encode_image(image_path)
     # This function is not defined yet, but it should be a function that encodes the image to base64.

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
#gpt-3.5-turbo
#gpt-4o-realtime-preview
#gpt-4o-mini
#gpt-4o 

    payload = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": constants.experiment_constants.two_lines_prompt(num_people)

                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000
    }
    
    print("posting")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    after = time.time()
    print(f"Time taken: {after-before} seconds")
    response_dict = response.json()
    response_dict["duration"] = after-before
    return response_dict

def parse_ai_response(response_json):
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
    answer = content["Answer"]
    reasoning = content["Reasoning"]
    confidence = content["Confidence"]
    input_tokens = response_json["usage"]["prompt_tokens"]
    output_tokens = response_json["usage"]["completion_tokens"]
    duration = response_json["duration"]
    return answer, reasoning, confidence, input_tokens, output_tokens, duration

def save_to_csv(response_list, num_people, save_folder_path):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    save_folder_path = Path(save_folder_path)
    csv_path = save_folder_path / f"{timestamp}_{len(response_list)}_runs_{num_people}_people.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["answer", "reasoning", "confidence", "num_people", "input_tokens", "output_tokens", "duration"])
        for i in range(len(response_list)):
            try:
                answer, reasoning, confidence, input_tokens, output_tokens, duration = parse_ai_response(response_list[i])
            except Exception as e:
                answer, reasoning, confidence, input_tokens, output_tokens = "Error", "Error", "Error", "Error", "Error"
                duration = response_list[i]["duration"]
            writer.writerow([answer, reasoning, confidence, num_people, input_tokens, output_tokens, duration])
    return

def save_to_txt(response_list, num_people, save_folder_path):
    question = constants.experiment_constants.get_two_lines_prompt(num_people)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    txt_path = save_folder_path / f"{timestamp}_{len(response_list)}_runs_{num_people}_people.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for i in range(len(response_list)): 
            try:
                answer, reasoning, confidence, input_tokens, output_tokens, duration = parse_ai_response(response_list[i])
            except Exception as e:
                answer, reasoning, confidence, input_tokens, output_tokens = "Error", "Error", "Error", "Error", "Error"
                duration = response_list[i]["duration"]
            f.write(f"{question}\n{answer}\n{reasoning}\n{confidence}\n{input_tokens}\n{output_tokens}\n{duration}\nnum_people: {num_people}\n\n")

def run_two_lines_experiment(num_people, times_to_run, folder_path):
    response_list = []
    #create the save folder if it doesn't exist
    script_dir = Path(__file__).parent
    save_folder = script_dir / folder_path  
    save_folder.mkdir(parents=True, exist_ok=True)
    error_count = 0
    for i in range(times_to_run):
        response = describe_image(image_path, num_people)
        response_list.append(response)
    save_to_csv(response_list, num_people, save_folder)
    save_to_txt(response_list, num_people, save_folder)

    print(f"Experiment completed {times_to_run} times")
    return

#print(describe_image(image_path, 50))
run_two_lines_experiment(50, 20, "data")