from pathlib import Path
import game_constants
import argparse
import os

# Parse command line arguments: game ID, configuration file name, and number of games to run
p = argparse.ArgumentParser(description="Win Rate Analysis for Mafia Games.")
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
    print("No initial game ID provided. Please specify an ID using -i or --initial_game_id.", flush=True)
    exit()
if ending_id is None:
    print("No ending game ID provided. Please specify an ID using -e or --ending_game_id.", flush=True)
    exit()

# Loop through the game IDs from starting_id (inclusive) to ending_id (inclusive)

print(f"Analyzing win rates from game {starting_id} to {ending_id}...", flush=True)

total_games = 0
mafia_wins = 0

for game_id in range(int(starting_id), int(ending_id) + 1):
    game_id_str = str(game_id).zfill(4)  # Ensure the game ID is zero-padded to 4 digits
    game_dir = Path(game_constants.DIRS_PREFIX) / game_id_str
    
    # Load the game results (assuming a function exists to do this)
    try:
        with open(game_dir / "who_wins.txt") as f:
            results = f.readlines()[0].strip().lower()

        if "mafia" in results:
            mafia_wins += 1
            total_games += 1
        elif "bystanders" in results:
            total_games += 1
        else:
            print(f"Results for game {game_id_str} not recognized.", flush=True)
            continue

    except FileNotFoundError:
        print(f"Results for game {game_id_str} not found.", flush=True)
        
# Calculate the win rate
winrate_str = f"For {total_games} games played between {starting_id} and {ending_id}:\n" \
              f"Mafia won {mafia_wins} times, and Villagers won {total_games-mafia_wins} times.\n" \
              f"Mafia win rate: {mafia_wins / total_games * 100:.2f}%\n" \
              f"Villagers win rate: {(total_games - mafia_wins) / total_games * 100:.2f}%\n"
              
with open(f"win_rate_analysis_{starting_id}_{ending_id}.txt", "w") as f:
    f.write(winrate_str)

print(winrate_str, flush=True)