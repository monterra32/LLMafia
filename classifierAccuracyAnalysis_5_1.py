# TODO: Allow for analysis of multi-mafia games

from pathlib import Path
import time
import game_constants
import argparse
import os

import openai
import llm.llm as llm
import llm_players.llm_constants as llm_constants

# Parse command line arguments: game ID, configuration file name, and number of games to run
p = argparse.ArgumentParser(
    description="Third-Party Classifier Accuracy Analysis for Mafia Games."
)
p.add_argument(
    "-i",
    "--initial_game_id",
    type=str,
    default=None,
    help="Initial game ID to start analysis from (inclusive)",
)
p.add_argument(
    "-e",
    "--ending_game_id",
    type=str,
    default=None,
    help="Ending game ID to stop analysis at (inclusive)",
)

args = p.parse_args()

# Handle the arguments
starting_id = args.initial_game_id
ending_id = args.ending_game_id

if starting_id is None:
    print(
        "No initial game ID provided. Please specify an ID using -i or --initial_game_id.",
        flush=True,
    )
    exit()
if ending_id is None:
    print(
        "No ending game ID provided. Please specify an ID using -e or --ending_game_id.",
        flush=True,
    )
    exit()
    
def prepareTranscript(game_id: str):
    transcript = ""
    # Load the game transcript
    game_dir = get_game_dir(game_id)
    daytime_chat = game_dir / "public_daytime_chat.txt"
    
    if not daytime_chat.exists():
        print(f"Transcript for game {starting_id} not found.", flush=True)
        return None
    
    raw = ""
    lines = []

    # read the lines and add them to raw
    with open(daytime_chat, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if line.strip() != "":
            raw += line.strip() + "\n"
    daytime_up_to_day_2 = raw.strip() # TODO: Handle different amounts of days, diferent amounts of mafia, players, etc.    
    # print the transcript
    # print(f"Transcript for game {game_id}:\n{daytime_up_to_day_2}", flush=True)
    return daytime_up_to_day_2

# Load the OpenAI API key
openai.api_key = llm.get_api_key(llm_constants.OPENAI_API_KEY_KEYWORD, llm_constants.OPENAI_API_KEY_KEYWORD)

def detect(transcript: str, game_dir: Path):
    # Call gpt-4 and have it, given the transcript, predict who it thinks the mafia is.
    output = None
    while not output:
        try:
            resp = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an observer of a mafia game, a popular type of social deduction game. Your goal is to find the mafia given the game dialogue. The rules are given as follows.\n" \
                                   "1. Your job is to find the mafia.\n" \
                                   "2. There are up to 5 players, each with a unique name. They are either bystanders or mafia. Mafia can kill bystanders during nighttime. Both bystanders and the mafia can vote to lynch someone in the daytime.\n" \
                                   "3. There are 1 mafia in the game.\n" \
                                   "4. The game ends when an equal number of mafia and bystanders are left, or all mafia are dead.\n" \
                                   "5. You are able to access daytime dialogue and voting information. You are not allowed to access mafia‑only dialogues.\n" \
                                   "6. Write your reason step-by-step.\n" \
                                   "7. Follow the example format for your response:\n" \

                                   "Mafia: <player name>\n" \
                                   "Reason: <your reasoning here>"
                    },
                    {
                        "role": "user",
                        "content": transcript
                    },
                ],
                temperature=0.0,
                n=1
            )
            output = resp.choices[0].message.content
            prediction = output.split("Mafia: ")[1].split("\n")[0].strip()
            if prediction == "":
                print("No mafia detected. Retrying...", flush=True)
                output = None
        except openai.OpenAIError as e:
            print(e, flush=True)
            time.sleep(1)
            
    # save who the predicted mafia is into classifier_prediction.txt
    if Path(game_dir / "classifier_prediction.txt").exists():
        # delete the file if it exists
        os.remove(str(game_dir / "classifier_prediction.txt"))
    with open(str(game_dir / "classifier_prediction.txt"), "w", encoding="utf-8") as f:
        f.write(f"{output}")
    
def get_game_dir(game_id: str):
    return Path(game_constants.DIRS_PREFIX) / game_id

def analyzeAccuracy():
    # Loop through the game IDs from starting_id (inclusive) to ending_id (inclusive)

    print(
        f"Analyzing classifier accuracies from game {starting_id} to {ending_id}...",
        flush=True,
    )

    total_games = 0
    single_match = 0

    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(4)  # Ensure the game ID is zero-padded to 4 digits
        game_dir = get_game_dir(game_id_str)

        mafia = ""
        prediction = ""
        try:
            with open(game_dir / "mafia_names.txt") as f:
                mafia = (
                    f.readlines()[0].strip().lower()
                )  # TODO: Handle multiple mafia names
        except FileNotFoundError:
            print(f"Mafia for game {game_id_str} not found.", flush=True)

        try:
            with open(game_dir / "classifier_prediction.txt", "r", encoding='utf-8') as f:
                prediction = f.readlines()[0].split("Mafia: ")[1].split("\n")[0].strip().lower()
                # prediction = output.split("Mafia: ")[1].split("\n")[0].strip()
        except FileNotFoundError:
            print(f"Prediction for game {game_id_str} not found.", flush=True)

        if mafia == "" or prediction == "":
            print(f"Results for game {game_id_str} not recognized.", flush=True)
            continue
        elif mafia == prediction:
            single_match += 1
            total_games += 1
        elif mafia != prediction:
            total_games += 1

    # Calculate the win rate
    classifier_accuracy_str = (
        f"For {total_games} games played between {starting_id} and {ending_id}:\n"
        f"Classifier correctly predicted {single_match} times, and incorrectly predicted {total_games - single_match} times.\n"
        f"Classifier accuracy: {single_match / total_games * 100:.2f}%\n"
    )

    with open(f"classifier_accuracy_analysis_{starting_id}_{ending_id}.txt", "w", encoding="utf-8") as f:
        f.write(classifier_accuracy_str)

    print(classifier_accuracy_str, flush=True)

def main():
    # Prepare the transcripts and detect mafia for each game
    print(
        f"Preparing transcripts and detecting mafia for games {starting_id} to {ending_id}...",
        flush=True,
        )
    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(4)  # Ensure the game ID is zero-padded to 4 digits
        game_dir = get_game_dir(game_id_str)

        transcript = prepareTranscript(game_id_str)
        if transcript is None:
            print(f"Transcript for game {game_id_str} not found. Skipping...", flush=True)
            continue
        
        # Detect mafia from the transcript
        detect(transcript, game_dir)
        
    # Analyze the accuracy of the classifier
    analyzeAccuracy()
    
if __name__ == "__main__":
    main()