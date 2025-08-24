from pathlib import Path
import time
import game_constants
import argparse
import os
import pandas as pd
import numpy as np
import traceback

import openai
import llm.llm as llm
import llm_players.llm_constants as llm_constants

FILENAME: str = "classifier_prediction_dayNumber_{}.txt"

# Constants for day phase changes
DAY_START_KEY = "Phase Change to Daytime"
DAY_END_KEY = "Phase Change to Nighttime"
DAY_START_KEY_MODIFIED = "Nighttime ended."
DAY_END_KEY_MODIFIED = "Daytime ended."

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


def indexOf(data: pd.DataFrame, substring: str) -> int:
    """
    Returns the index of the first occurrence of a substring in a csv file.
    if the substring is not found, returns -1.
    """
    for i, row in data.iterrows():
        contents = row['contents']
        if substring in contents:
            return i
    return -1

def removeNighttimeChat(data: pd.DataFrame) -> pd.DataFrame:
    """
    Removes the nighttime chat from the data.
    The nighttime chat is between the "Phase Change to Nighttime" and "Phase Change to Daytime" lines.
    """
    tmpData = data.copy()  # Create a copy of the data to avoid modifying the original DataFrame
    
    # Find all rows that are between nighttime phases
    rows_to_drop = []
    in_nighttime = False
    
    for i, row in data.iterrows():
        contents = row['contents']
        
        if DAY_START_KEY in contents:
            in_nighttime = False
        elif DAY_END_KEY in contents:
            in_nighttime = True
        elif in_nighttime:
            # If we're in nighttime, mark this row for removal
            rows_to_drop.append(i)
    
    # Drop the nighttime rows
    if rows_to_drop:
        tmpData = tmpData.drop(index=rows_to_drop)
    
    print(f"Removed {len(rows_to_drop)} nighttime rows", flush=True)
    return tmpData

def modifyDaytimeChat(data: pd.DataFrame) -> pd.DataFrame:
    
    tmpData = data.copy()  # Create a copy of the data to avoid modifying the original DataFrame
    
    #print(f"Modifying chat data...", flush=True)
    
    for i, row in tmpData.iterrows(): 
            contents = row['contents']
            type = row['type']
            
            if type == "vote":
                parsed = contents.split(": ")
                voter = parsed[0].strip()  # The player who voted
                votee = parsed[1].strip()  # The player who was voted for

                new_content = f"{voter} voted for {votee}"
                tmpData.at[i, 'contents'] = new_content  # Update the contents to be more readable
                # print(f"  Row {i}: Modified vote '{contents}' -> '{new_content}'", flush=True)
                
            elif type == "info" and "Phase Change to" in contents:
                # If the type is info and the contents contain "Phase Change to", it is either the beginning or the end of the day
                if DAY_START_KEY in contents:
                    parsed = [contents, "No one"]
                    if "Victim - " in contents:
                        parsed = contents.split("Victim - ")
                    
                    new_content = f"{DAY_START_KEY_MODIFIED} {parsed[1].strip()} was killed in the night. It is now Daytime."
                    tmpData.at[i, 'contents'] = new_content
                    # print(f"  Row {i}: Modified info (daytime) '{contents}' -> '{new_content}'", flush=True)
                elif DAY_END_KEY in contents:
                    parsed = [contents, "No one"]
                    if "Victim - " in contents:
                        parsed = contents.split("Victim - ")
                    
                    new_content = f"{DAY_END_KEY_MODIFIED} {parsed[1].strip()} was voted out. It is now Nighttime."
                    tmpData.at[i, 'contents'] = new_content
                    # print(f"  Row {i}: Modified info (nighttime) '{contents}' -> '{new_content}'", flush=True)
    
    #print(f"Finished modifying chat data", flush=True)
    return tmpData  # Return the modified DataFrame with more readable contents

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
    chat = game_dir / "info.csv"
    if not chat.exists():
        print(f"Transcript for game {starting_id} not found.", flush=True)
        return None

    daytimeList: pd.DataFrame = []
    daytimeDays: list[list[str]] = []
    
    daytimeList = pd.read_csv(chat, encoding="utf-8")
    print(f"Original data shape: {daytimeList.shape}", flush=True)
    print(f"Original data preview:", flush=True)
    with pd.option_context('display.max_columns', None, 'display.width', None):
        print(daytimeList.head(10), flush=True)
    
    daytimeList = removeNighttimeChat(daytimeList)  # Remove the nighttime chat from the data
    print(f"After removing nighttime chat: {daytimeList.shape}", flush=True)
    print(f"After removing nighttime chat preview:", flush=True)
    with pd.option_context('display.max_columns', None, 'display.width', None):
        print(daytimeList.head(10), flush=True)
    
    daytimeList = modifyDaytimeChat(daytimeList)  # Modify the daytime chat to be more readable
    print(f"After modifying chat: {daytimeList.shape}", flush=True)
    print(f"After modifying chat preview:", flush=True)
    with pd.option_context('display.max_columns', None, 'display.width', None):
        print(daytimeList.head(10), flush=True)
    
    # debugging to show the final daytime list
    # print(f"All contents in daytimeList:", flush=True)
    # for i, row in daytimeList.iterrows():
    #   print(f"Row {i}: Type={row['type']}, Content='{row['contents']}'", flush=True)
    
    # Parse the daytime chat into multiple days; the key phrase is the last vote of the day
    dayStartKey = DAY_START_KEY_MODIFIED  # The following lines are the daytime chat
    dayEndKey = DAY_END_KEY_MODIFIED  # marks the end of the day

    tempDay: str = ""
    currentDay = 0
    firstDayStarted = False  # Flag to track if we've started the first meaningful day
    
    for i, row in daytimeList.iterrows():
        contents = row['contents']
        timestamp = row['creation_time']
        
        # Start a new day when we see "Phase Change to Daytime"
        if dayStartKey in contents:
            if tempDay.strip() and firstDayStarted:  # Save previous day if it exists and we've started
                daytimeDays.append(tempDay.strip())
            tempDay = f"[{timestamp}] {contents}\n"  # Start new day with timestamp
            firstDayStarted = True  # Mark that we've started the first meaningful day
            currentDay += 1
            continue
            
        # End the day when we see "Phase Change to Nighttime"
        if dayEndKey in contents:
            if firstDayStarted:  # Only add content if we've started the first meaningful day
                tempDay += f"[{timestamp}] {contents}\n"
                daytimeDays.append(tempDay.strip())  # Save the completed day
            tempDay = ""  # Reset for next day
            continue

        # Add all other content to current day (only if we've started the first meaningful day)
        if firstDayStarted:
            tempDay += f"[{timestamp}] {contents}\n"
    
    # Don't forget the last day if it doesn't end with a phase change
    if tempDay.strip() and firstDayStarted:
        daytimeDays.append(tempDay.strip())
    
    print(f"Parsed {len(daytimeDays)} days:", flush=True)
    for i, day in enumerate(daytimeDays):
        print(f"Day {i+1} length: {len(day)} characters", flush=True)
        print(f"Day {i+1} preview: {day[:100]}...", flush=True)
       
    for day in range(1, len(daytimeDays) + 1):
        subTranscript = ""
        for i in range(0, day):
            # Combine the daytime and manager chat for each day up to the specified day (inclusive)
            if i < len(daytimeDays):
                subTranscript += (
                    daytimeDays[i]  # The daytime chat for the day
                    + "\n"
                )
        transcript.append(subTranscript.strip())
        print(f"Day {day} transcript length: {len(subTranscript)} characters", flush=True)
        print(f"Day {day} transcript preview: {subTranscript[:200]}...", flush=True)

    return transcript  # Return the list of transcripts for each day


# Load the OpenAI API key
openai.api_key = llm.get_api_key(
    llm_constants.OPENAI_API_KEY_KEYWORD, llm_constants.OPENAI_API_KEY_KEYWORD
)


def detect(transcripts: list[str], game_dir: Path):
    
    # Clean up any existing classifier prediction files before starting analysis
    print(f"Cleaning up existing classifier prediction files in {game_dir}...", flush=True)
    
    # Delete any existing classifier_prediction_dayNumber_*.txt files using FILENAME
    for day_num in range(1, 20):
        day_file = game_dir / FILENAME.format(day_num)
        if day_file.exists():
            os.remove(str(day_file))
            print(f"  Deleted: {FILENAME.format(day_num)}", flush=True)
    
    print(f"Cleanup complete. Starting analysis...", flush=True)
    
    for dayNumber, transcript in enumerate(transcripts, start=1):
        print(f"\n{'='*80}", flush=True)
        print(f"DAY {dayNumber} ANALYSIS", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"Transcript being sent to LLM (length: {len(transcript)} characters):", flush=True)
        print(f"-----------------", flush=True)
        print(transcript, flush=True)

        print(f"{'='*80}", flush=True)
        
        # Call gpt-4 and have it, given the transcript, predict who it thinks the mafia is.
        output = None
        retry_count = 0
        max_retries = 3  # Prevent infinite loops
        
        while not output and retry_count < max_retries:
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
                print(f"LLM Output: {output}", flush=True)  # Debug output
                if "Mafia: " not in output:
                    print(f"Output doesn't contain 'Mafia: '. Retry {retry_count + 1}/{max_retries}...", flush=True)
                    output = None
                    retry_count += 1
                    continue
                prediction = output.split("Mafia: ")[1].split("\n")[0].strip()
                if prediction == "":
                    print(f"No mafia detected. Retry {retry_count + 1}/{max_retries}...", flush=True)
                    output = None
                    retry_count += 1
            except openai.OpenAIError as e:
                print(e, flush=True)
                retry_count += 1
                time.sleep(1)
        
        # If we exhausted all retries, create a fallback output
        if not output:
            print(f"Failed to get valid LLM response after {max_retries} retries for day {dayNumber}. Creating fallback.", flush=True)
            output = "Mafia: Unable to determine\nReason: Failed to get valid LLM response after multiple attempts."

        # save who the predicted mafia is into classifier_prediction.txt
        if Path(game_dir / "classifier_prediction.txt").exists():
            # delete the file if it exists
            os.remove(str(game_dir / f"classifier_prediction_day.txt"))
        for day_num in range (1, 12):
            if Path(game_dir / f"classifier_prediction_day_{day_num}.txt").exists():
                # delete the file if it exists
                os.remove(str(game_dir / f"classifier_prediction_day_{day_num}.txt"))
        if Path(game_dir / FILENAME.format(dayNumber)).exists():
            # delete the file if it exists
            os.remove(str(game_dir / FILENAME.format(dayNumber)))
        with open(
            str(game_dir / FILENAME.format(dayNumber)),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(f"{output}")


def get_game_dir(game_id: str):
    return Path(game_constants.DIRS_PREFIX) / game_id

def getMafiaNames(game_id: str) -> list[str]:
    game_dir = get_game_dir(game_id)
    
    mafia_names_file = game_dir / "node.csv"
    mafiaList: list[str] = []
    
    playerList: pd.DataFrame = pd.read_csv(mafia_names_file, encoding="utf-8")
    
    for i, row in playerList.iterrows():
        if "mafioso" in row['type']:
            mafiaList.append(row['property1'].strip())
    
    return mafiaList

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
            mafia: list[str] = getMafiaNames(game_id_str)
        except FileNotFoundError as e:
            print(f"Mafia for game {game_id_str} not found.", flush=True)
            print(e, flush=True)
            print(traceback.print_exc(), flush=True)

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
            
            if mafia == []:
                print(f"Results for game {game_id_str} not recognized, no ground truth mafia", flush=True)
                continue
            if prediction == []:
                print(f"Results for game {game_id_str} not recognized, no predictions.", flush=True)
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
    daytime_chat = game_dir / "info.csv"
    if not daytime_chat.exists():
        print(f"Daytime chat for game {starting_id} not found.", flush=True)
        return 0

    daytimeList: list[str] = []

    daytimeList = pd.read_csv(daytime_chat, encoding="utf-8").copy()

    # Find all the beginning of utterances
    for i, line in daytimeList.iterrows():
        if line['type'] == "text":  # Only consider player utterances, ignore Game-Manager messages
            transcript.append(line['contents'].strip())
                    
    print(transcript, flush=True)
    
    return len(transcript)

def get_mean_utterances(game_id: str) -> float:
    
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
        f"mean_utterances_per_game_analysis_{starting_id}_{ending_id}.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(mean_utterances_str)

    print(mean_utterances_str, flush=True)

def get_num_words(game_id: str) -> int:
    # Get the number of words in the daytime chat for a given game ID, exluding Game-Manager messages
    print(f"getting number of words for game {game_id}...", flush=True)
    """
    Returns the number of words in the daytime chat for a given game ID.
    """
    game_dir = get_game_dir(game_id)
    num_words = 0
    # Load the Daytime chat
    daytime_chat = game_dir / "info.csv"
    if not daytime_chat.exists():
        print(f"Daytime chat for game {starting_id} not found.", flush=True)
        return 0
    daytimeList: list[str] = []
    daytimeList = pd.read_csv(daytime_chat, encoding="utf-8").copy()
    for i, line in daytimeList.iterrows():
        if line['type'] == "text":  # Ignore Game-Manager messages
            content = line['contents']
            if ":" in content:
                raw = content.split(":", 1)[1]
                num_words += len(raw.split(" "))
            if ":" not in content:
                num_words += len(content.split(" "))
    
    return num_words

def get_mean_words_per_utterance():
    # Get the mean number of words per utterance for all games between starting_id and ending_id
    print(
        f"Finding the mean words per utterance for games {starting_id} to {ending_id}...",
        flush=True,
    )
    total_utterances = 0
    total_words = 0
    
    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(
            4
        )
    
    total_utterances = get_num_utterances(game_id_str)
    total_words = get_num_words(game_id_str)
    
    mean_words_per_utterance_str = (
        f"For {total_utterances} utterances between {starting_id} and {ending_id}:\n"
    )
    mean_words_per_utterance_str += (
        f"Mean number of words per utterance: {total_words / total_utterances:.2f}\n"
    )
    print(mean_words_per_utterance_str, flush=True)
    with open(
        f"mean_words_per_utterance_analysis_{starting_id}_{ending_id}.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(mean_words_per_utterance_str)

def get_random_chance():
    # Get the single and exact match chance of randomly guessing 2 mafia out of n players
    # n being the number of players in that game_id.
    # Do it using monte carlo simulation
    print(
        f"Finding the random chance of guessing 2 mafia out of n players...",
        flush=True,
    )
    import random
    total_simulations = 0
    num_simulations = 10000
    single_match = 0
    exact_match = 0
    num_mafia = 2
    for game_id in range(int(starting_id), int(ending_id) + 1):
        game_id_str = str(game_id).zfill(
            4
        )
        
        # Find the number of players in the game
        game_dir = get_game_dir(game_id_str)
        player_file = game_dir / "node.csv"
        playerList: pd.DataFrame = pd.read_csv(player_file, encoding="utf-8").copy()
        num_players = playerList.shape[0] - 1  # Exclude the Game-Manager node
        
        for _ in range(num_simulations):
            players = [f"player_{i}" for i in range(num_players)]
            mafia = random.sample(players, num_mafia)
            prediction = random.sample(players, num_mafia)
            if len(set(mafia) & set(prediction)) == 2:
                exact_match += 1
                single_match += 1
            elif len(set(mafia) & set(prediction)) == 1:
                single_match += 1
        
        total_simulations += num_simulations
        
    random_chance_str = (
        f"For {total_simulations} simulations of randomly guessing 2 mafia out of n players:\n"
    )
    random_chance_str += (
        f"Single match chance: {single_match / total_simulations * 100:.2f}%\n"
        f"Exact match chance: {exact_match / total_simulations * 100:.2f}%\n"
    )
    print(random_chance_str, flush=True)
    with open(
        f"random_chance_analysis_{starting_id}_{ending_id}.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(random_chance_str)
 
if __name__ == "__main__":
    # main()
    # get_mean_words_per_utterance()
    get_random_chance()
