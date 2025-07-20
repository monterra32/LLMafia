import open_mafia
import game_constants
import argparse
import os


def main():

    def isFinished(game_id: str):
        # Wait for the game to finish before starting the next one
        isFinished = False
        game_dir = os.path.join(game_constants.DIRS_PREFIX, game_id.zfill(4))
        try:
            with open(os.path.join(game_dir, "who_wins.txt"), "r") as f:
                isFinished = True if f.read().strip() != "" else False
        except FileNotFoundError:
            isFinished = False
            # print(f"who_wins.txt not found for game {game_id}", flush=True)

        return isFinished

    # Parse command line arguments: game ID, configuration file name, and number of games to run
    p = argparse.ArgumentParser(description="Multi-game tester for Open Mafia")
    p.add_argument(
        "-i",
        "--initial_game_id",
        type=str,
        default=str(int(game_constants.get_latest_game_id()) + 1).zfill(4),
        help="Initial game ID to start testing from;"
        "must not already be an existing game ID",
    )
    p.add_argument(
        "-c",
        "--config_file_name",
        type=str,
        default=".\\configurations\\openai_5_5.json",
        help="path/to/configuration/file.json to use for the game setup, assumed LLMafia folder is root (./)",
    )
    p.add_argument(
        "-n",
        "--num_games",
        type=int,
        default=10,
        help="Number of games to run in the test",
    )
    p.add_argument(
        "-g",
        "--concurrent_games",
        type=int,
        default=1,
        help="Number of games to run concurrently",
    )
    args = p.parse_args()

    # Assign vars and print the starting parameters
    starting_id = args.initial_game_id.zfill(4)
    config_file = args.config_file_name.split("configurations\\")[1]
    num_games = args.num_games
    concurrent_games = args.concurrent_games
    print(
        f"Starting tests from game number {starting_id} (inclusive)"
        f" and using configuration file {config_file}",
        f" for {num_games} games",
        flush=True,
    )

    next_game_id = int(starting_id)  # Start making games from this ID
    game_list = []
    while game_list or next_game_id < int(starting_id) + num_games:
        game_id_str = str(next_game_id).zfill(4)
        # Remove any games that are finished
        for game in game_list:
            if isFinished(game["game_id"]):
                game_list.remove(game)
        # If there is an open slot, start a new game
        if len(game_list) < concurrent_games and next_game_id < int(starting_id) + num_games:
            open_mafia.main(
                game_id=game_id_str,
                config=config_file,
            )
            game_list.append(
                {
                    "game_id": game_id_str,
                    "config_file": config_file,
                }
            )
            next_game_id += 1
            


if __name__ == "__main__":
    main()
