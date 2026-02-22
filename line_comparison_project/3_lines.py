import two_lines_experiment
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

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import constants_folder.experiment_constants
import base64

image_path_1 = str(Path(__file__).parent / "comparison_lines" / "comparison_1_line.png")
image_path_2 = str(Path(__file__).parent / "comparison_lines" / "comparison_3_line.png")

secrets_file_path = project_root / ".secrets_dict.txt"
with open(secrets_file_path, "r", encoding="utf-8") as api_file:
    secrets_dict = json.load(api_file)
api_key = secrets_dict["OPENAI_API_KEY"]

def describe_double_image(image_path_1, image_path_2, num_people, context=False):
    before = time.time()
    base64_image_1 = two_lines_experiment.encode_image(image_path_1)
    base64_image_2 = two_lines_experiment.encode_image(image_path_2)


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = constants_folder.experiment_constants.get_line_comparison_payload(num_people, base64_image_1, base64_image_2, context)
#gpt-3.5-turbo 
#gpt-4o-realtime-preview
#gpt-4o-mini
#gpt-4o 
    #print(payload)
    print("posting")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    after = time.time()
    print(f"Time taken: {after-before} seconds")
    try:
        response_dict = response.json()
        response_dict["duration"] = after-before
        return response_dict
    except Exception as e:
        print(f"ERROR: {e}")
        print(response.text)
        print("i think its a malformed json response")
        return "Error", "Error", "Error", "Error", "Error", "Error"

def run_line_comparison_experiment(num_people, times_to_run, folder_path, is_context):

    # Convert context to boolean if it's a string
    if isinstance(is_context, str):
        is_context = is_context.lower() in ('true', '1', 'yes', 'on')
    elif not isinstance(is_context, bool):
        is_context = bool(is_context)  # Convert other types (int, etc.) to bool

    response_list = []
    #create the save folder if it doesn't exist
    script_dir = Path(__file__).parent
    save_folder = script_dir / folder_path  
    save_folder.mkdir(parents=True, exist_ok=True)
    error_count = 0
    for i in range(times_to_run):
        response = describe_double_image(image_path_1, image_path_2, num_people, is_context)
        response_list.append(response)
    two_lines_experiment.save_to_csv(response_list, num_people, save_folder)
    two_lines_experiment.save_to_txt(response_list, num_people, save_folder, is_context)

    print(f"Experiment completed {times_to_run} times")
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run two lines experiment")
    parser.add_argument("-n", "--num_people", type=int, default=0,
                        help="Number of people to mention in the question (default: 0)")
    parser.add_argument("-t", "--times_to_run", type=int, default=25,
                        help="Number of times to run the experiment (default: 25)")
    parser.add_argument("-f", "--folder_path", type=str, default="data",
                        help="Folder name to save results in (default: 'data')")
    parser.add_argument("-c", "--is_context", type=str, default="true",
                        help="Whether to include context or distillation in the question (default: true)")
    args = parser.parse_args()
    
    run_line_comparison_experiment(args.num_people, args.times_to_run, args.folder_path, args.is_context)