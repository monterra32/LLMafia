import sys
from pathlib import Path
import random
import json


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import constants.experiment_constants

payload = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "system prompt"
                    }
                ]    
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "user prompt"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"image data",
                            "detail": "low"
                        }
                    }, 
                ]
            }    
            
        ],
        "max_tokens": 1000
    }
payload["messages"][1]["content"].extend(constants.experiment_constants.get_random_naysayers(3))

if __name__ == "__main__":
    print(payload)
    print("\n\n\n")