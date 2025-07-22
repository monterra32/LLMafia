# TODO: Allow for analysis of multi-mafia games

from pathlib import Path
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
    
# Load the OpenAI API key
openai.api_key = llm.get_api_key(llm_constants.OPENAI_API_KEY_KEYWORD, llm_constants.OPENAI_API_KEY_KEYWORD)

def detect(transcript):
    # Call gpt-4 and have it, given the transcript, predict who it thinks the mafia is.
    prompt = ""
    
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

        mafia, prediction = ""
        try:
            with open(game_dir / "mafia_names.txt") as f:
                mafia = (
                    f.readlines()[0].strip().lower()
                )  # TODO: Handle multiple mafia names
        except FileNotFoundError:
            print(f"Mafia for game {game_id_str} not found.", flush=True)

        try:
            with open(game_dir / "classifier_prediction.txt") as f:
                prediction = f.readlines()[0].strip().lower()
        except FileNotFoundError:
            print(f"Prediction for game {game_id_str} not found.", flush=True)

        if mafia == "" or prediction == "":
            print(f"Results for game {game_id_str} not recognized.", flush=True)
            continue
        elif mafia == prediction:
            single_match += 1
            total_games += 1
        elif mafia == prediction:
            total_games += 1

    # Calculate the win rate
    classifier_accuracy_str = (
        f"For {total_games} games played between {starting_id} and {ending_id}:\n"
        f"Classifier correctly predicted {single_match} times, and incorrectly predicted {total_games - single_match} times.\n"
        f"Classifier accuracy: {single_match / total_games * 100:.2f}%\n"
    )

    with open(f"classifier_accuracy_analysis_{starting_id}_{ending_id}.txt", "w") as f:
        f.write(classifier_accuracy_str)

    print(classifier_accuracy_str, flush=True)
