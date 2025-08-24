from pathlib import Path
import time
import game_constants
import argparse
import os

import openai
import llm.llm as llm
import llm_players.llm_constants as llm_constants

FILENAME = "classifier_prediction_dayNumber_{}.txt"

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

# def prepareTranscript(game_id: str):
#     transcript = ""
#     # Load the game transcript
#     game_dir = get_game_dir(game_id)
#     daytime_chat = game_dir / "public_daytime_chat.txt"

#     if not daytime_chat.exists():
#         print(f"Transcript for game {starting_id} not found.", flush=True)
#         return None

#     raw = ""
#     lines = []

#     # read the lines and add them to raw
#     with open(daytime_chat, "r", encoding="utf-8") as f:
#         lines = f.readlines()
#     for line in lines:
#         if line.strip() != "":
#             raw += line.strip() + "\n"
#     daytime_up_to_day_2 = raw.strip() #
#     # print the transcript
#     # print(f"Transcript for game {game_id}:\n{daytime_up_to_day_2}", flush=True)
#     return daytime_up_to_day_2


def indexOf(list: list, substring: str) -> int:
    """
    Returns the index of the first occurrence of a substring in a list of strings.
    if the substring is not found, returns -1.
    """
    for i, item in enumerate(list):
        if substring in item:
            return i
    return -1


def prepareTranscripts(game_id: str) -> list[str]:
    print(f"Preparing transcripts for game {game_id}...", flush=True)
    """
    Prepares a list of transcripts for a given game ID.
    The list contains the chat transcripts for each day up to the specified day.
    The lenght of the list is equal to the number of days in the game.
    """
    transcript: list[str] = []
    game_dir = get_game_dir(game_id)

    # Load the game transcript - both Daytime and Manager chat
    daytime_chat = game_dir / "public_daytime_chat.txt"
    if not daytime_chat.exists():
        print(f"Daytime chat for game {starting_id} not found.", flush=True)
        return None

    manager_chat = game_dir / "public_manager_chat.txt"
    if not manager_chat.exists():
        print(f"Manager chat for game {starting_id} not found.", flush=True)
        return None

    daytimeList: list[str] = []
    daytimeDays: list[list[str]] = []

    managerList: list[str] = []
    managerDays: list[list[str]] = []

    with open(daytime_chat, "r", encoding="utf-8") as f:
        daytimeList = f.readlines()

    while (
        len(daytimeList) > 1
    ):  # While there are still lines in the daytime chat; the transcript has one empty newline at the end of the document.
        # Parse the daytime chat into multiple days; the key phrase is the last vote of the day
        key = "Daytime has ended, now it's time to vote! Waiting for all players to vote..."  # The following lines are the votes of the different players.
        firstVoteIndex = indexOf(daytimeList, key) + 1
        lastVoteIndex = firstVoteIndex
        while (
            # check if daytimeList[lastVoteIndex + 1] is not out of bounds
            lastVoteIndex + 1 < len(daytimeList)
            and "voted for" in daytimeList[lastVoteIndex + 1]
            and "Game-Manager" in daytimeList[lastVoteIndex + 1]
        ):  # find the index of the final vote of the day
            lastVoteIndex += 1
        daytimeDays.append(
            daytimeList[0 : lastVoteIndex + 1]
        )  # Add the day to the list of days
        del daytimeList[0 : lastVoteIndex + 1]  # Remove the day from the list of lines

    with open(manager_chat, "r", encoding="utf-8") as f:
        managerList = f.readlines()

    while (
        len(managerList) > 1
    ):  # While there are still lines in the daytime chat; the transcript has one empty newline at the end of the document.
        # Parse the daytime chat into multiple days; the key phrase is the last vote of the day
        # Remove the oneMafiaLeft message if it exists
        daytimeLynchKey = "Now it's Daytime for"  # The following lines are the results of the daytime lynch and nighttime kill.
        daytimeLynchIndex = indexOf(managerList, daytimeLynchKey) + 1
        # managerList[daytimeLynchIndex] = managerList[daytimeLynchIndex].split("Their role was")[0].strip() + "\n"

        nighttimeKillKey = "Now it's Nighttime for"
        nighttimeKillIndex = indexOf(managerList, nighttimeKillKey) + 1
        
        if (nighttimeKillIndex != 0):
            if "There is only one mafia member left" in managerList[nighttimeKillIndex]:
                managerList[nighttimeKillIndex] = "It is now Nighttime. \n"
                nighttimeKillIndex += 1  # Skip the "There is only one mafia member left" message

            # Remove the identity of the players who were lynched or killed
            # print("nightline", managerList[nighttimeKillIndex], flush=True)
            # Change verbage from voted out to killed in the night
            noVoteSplitList = managerList[nighttimeKillIndex].split("voted out")
            managerList[nighttimeKillIndex] = (
                noVoteSplitList[0] + "killed in the night" + noVoteSplitList[1]
            )
            # managerList[nighttimeKillIndex] = managerList[nighttimeKillIndex].split("Their role was")[0].strip()
        elif nighttimeKillIndex == 0: # Transcript ends with a daytime lynch  
            nighttimeKillIndex = daytimeLynchIndex
            
        managerDays.append(
            managerList[0 : nighttimeKillIndex + 1]
        )  # Add the day to the list of days
        del managerList[
            0 : nighttimeKillIndex + 1
        ]  # Remove the day from the list of lines

    for day in range(1, len(daytimeDays) + 1):
        subTranscript = ""
        for i in range(0, day):
            # Combine the daytime and manager chat for each day up to the specified day (inclusive)
            if i < len(daytimeDays) and i < len(managerDays):
                subTranscript += (
                    managerDays[i][0]  # Now it's Daytime...
                    + "\n"
                    + "".join(daytimeDays[i])  # The daytime chat for the day
                    + "\n"
                    + "".join(managerDays[i][1:])  # Result of lynch and kill
                    + "\n"
                )
        transcript.append(subTranscript.strip())

    return transcript


# Load the OpenAI API key
openai.api_key = llm.get_api_key(
    llm_constants.OPENAI_API_KEY_KEYWORD, llm_constants.OPENAI_API_KEY_KEYWORD
)


def detect(transcripts: list[str], game_dir: Path):
    for dayNumber, transcript in enumerate(transcripts, start=1):
        # Call gpt-4 and have it, given the transcript, predict who it thinks the mafia is.
        output = None
        while not output:
            try:
                resp = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an observer of a mafia game, a popular type of social deduction game. Your goal is to find the mafia given the game dialogue. The rules are given as follows.\n"
                            "1. Your job is to find the mafia.\n"
                            "2. There are up to 10 players, each with a unique name. They are either bystanders or mafia. Mafia can kill bystanders during nighttime. Both bystanders and the mafia can vote to lynch someone in the daytime.\n"
                            "3. There are 2 mafia in the game.\n"
                            "4. The game ends when an equal number of mafia and bystanders are left, or all mafia are dead.\n"
                            "5. You are able to access daytime dialogue and voting information. You are not allowed to access mafia-only dialogues.\n"
                            "6. Write your reason step-by-step.\n"
                            "7. Follow the example format for your response:\n"
                            "Mafia: <player name 1>,<player name 2>\n"
                            "Reason: <your reasoning here>",
                        },
                        {"role": "user", "content": transcript},
                    ],
                    temperature=0.0,
                    n=1,
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
        if (game_dir / FILENAME.format(dayNumber)).exists():
            os.remove(game_dir / FILENAME.format(dayNumber))
        with open(
            str(game_dir / FILENAME.format(dayNumber)),
            'w',
            encoding="utf-8",
        ) as f:
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
    exact_match = 0

    rawStats: list[
        dict[{"total_games", int}, {"single_match", int}, {"exact_match", int}]
    ] = []

    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(
            4
        )  # Ensure the game ID is zero-padded to 4 digits
        game_dir = get_game_dir(game_id_str)

        mafia = ""
        prediction = ""
        try:
            with open(game_dir / "mafia_names.txt") as f:
                mafia: list[str] = f.readlines()
        except FileNotFoundError:
            print(f"Mafia for game {game_id_str} not found.", flush=True)

        dayNumber = 1
        while (game_dir / FILENAME.format(dayNumber)).exists():
            try:
                with open(
                    game_dir / FILENAME.format(dayNumber),
                    "r",
                    encoding="utf-8",
                ) as f:
                    prediction: list[str] = (
                        f.readlines()[0]
                        .split("Mafia: ")[1]
                        .split("\n")[0]
                        .strip()
                        .lower()
                        .split(", ")
                    )
                    # prediction = output.split("Mafia: ")[1].split("\n")[0].strip()
            except FileNotFoundError:
                print(f"Prediction for game {game_id_str} not found.", flush=True)

            if (
                len(prediction) != 2 and len(mafia) != 2
            ):  # Check to ensure there are exactly 2 mafia and 2 predictions (10-2)
                print(
                    f"Game {game_id_str} does not have exactly 2 mafia or 2 predictions. Skipping...",
                    flush=True,
                )
                continue
            
            if mafia == [] or prediction == []:
                print(f"Results for game {game_id_str} not recognized.", flush=True)
                continue

            while len(rawStats) < dayNumber:
                # Create a list with each index represending day Number - 1
                # Ex. rawStats[0] is the stats for day 1, rawStats[1] is the stats for day 2, etc.
                rawStats.append(
                    {
                        "total_games": 0,
                        "single_match": 0,
                        "exact_match": 0,
                    }
                )
            
            dayNumberIndex = dayNumber - 1
            
            # Check if the list of mafia and predictions have predictions in commmon:
            # If they have one name in common, then it is a single-match.
            # If they have both names in common, then it is an exact match.
            # If they have no names in common, then it is not a match.
            mafia = [m.strip().lower() for m in mafia]
            prediction = [p.strip().lower() for p in prediction]
            if len(set(mafia) & set(prediction)) == 2:
                rawStats[dayNumberIndex]["exact_match"] += 1
                rawStats[dayNumberIndex]["single_match"] += 1
                # increment the total games played for that day
                rawStats[dayNumberIndex]["total_games"] += 1
            elif len(set(mafia) & set(prediction)) == 1:
                rawStats[dayNumberIndex]["single_match"] += 1
                # increment the total games played for that day
                rawStats[dayNumberIndex]["total_games"] += 1
            elif len(set(mafia) & set(prediction)) == 0:
                rawStats[dayNumberIndex]["total_games"] += 1
                
            dayNumber += 1

    # Calculate the win rate
    classifier_accuracy_str = (
        f"For {total_games} games played between {starting_id} and {ending_id}:\n"
    )
    
    for day, stats in enumerate(rawStats, start=1):
        classifier_accuracy_str += (
            f"Day {day}: out of {stats['total_games']} games:\n"
            # insert both the exact value and percentage of single matches and exact matches
            f" - {stats['single_match']} single matches: {stats['single_match'] / stats['total_games'] * 100:.2f}%\n"
            f"  - {stats['exact_match']} exact matches: {stats['exact_match'] / stats['total_games'] * 100:.2f}%\n"
        )

    with open(
        f"classifier_accuracy_analysis_{starting_id}_{ending_id}.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(classifier_accuracy_str)

    print(classifier_accuracy_str, flush=True)


def main():
    # Prepare the transcripts and detect mafia for each game
    print(
        f"Preparing transcripts and detecting mafia for games {starting_id} to {ending_id}...",
        flush=True,
    )
    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(
            4
        )  # Ensure the game ID is zero-padded to 4 digits
        game_dir = get_game_dir(game_id_str)

        transcripts = prepareTranscripts(game_id_str)
        if transcripts is None:
            print(
                f"Transcript for game {game_id_str} not found. Skipping...", flush=True
            )
            continue

        # Detect mafia from the transcript
        detect(transcripts, game_dir)

    # Analyze the accuracy of the classifier
    analyzeAccuracy()

def get_num_utterances(game_id: str) -> int:
    print(f"getting mean number of utterances for game {game_id}...", flush=True)
    """
    Returns the mean number of utterances per game for a given game ID.
    """

    transcript: list[str] = []
    game_dir = get_game_dir(game_id)

    # Load the game transcript - both Daytime and Manager chat
    daytime_chat = game_dir / "public_daytime_chat.txt"
    if not daytime_chat.exists():
        print(f"Daytime chat for game {starting_id} not found.", flush=True)
        return 0

    daytimeList: list[str] = []

    with open(daytime_chat, "r", encoding="utf-8") as f:
        daytimeList = f.readlines()

    # Find all the beginning of utterances
    is_voting = False
    day_num = 1
    
    for i, line in enumerate(daytimeList):
        if line.strip() != "":
            if ":" in line: # colon indicates a player utterance
                if "Game-Manager" not in line:  # Ignore Game-Manager messages
                    if day_num < 5:
                        transcript.append(line.strip())
                    
                    if is_voting: # End of voting, time for next day.
                        is_voting = False
                        day_num += 1
                elif "Game_Manager" in line:
                    is_voting = True
    
    print(transcript, flush=True)
    
    return len(transcript)

def get_mean_utterances() -> float:
    
    print(
        f"Finding the mean utterances per game for games {starting_id} to {ending_id}...",
        flush=True,
    )
    
    total_games = 0
    total_utterances = 0
    
    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(
            4
        )  # Ensure the game ID is zero-padded to 4 digits
        
        num_utterances = get_num_utterances(game_id_str)
        if num_utterances != 0:
            total_games += 1
            total_utterances += num_utterances
    
    # Calculate the average number of utterances per game
    mean_utterances_str = (
        f"For {total_games} games played between {starting_id} and {ending_id}:\n"
    )
    
    mean_utterances_str += (
        f"Mean number of utterances per game: {total_utterances / total_games:.2f}\n"
    )

    with open(
        f"mean_utterances_per_game_analysis_{starting_id}_{ending_id}_gpt_4_turbo.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(mean_utterances_str)

    print(mean_utterances_str, flush=True)
            
if __name__ == "__main__":
    # get_mean_utterances()
    main()
