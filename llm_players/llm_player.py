import json
import re
from abc import ABC, abstractmethod
from game_constants import GAME_CONFIG_FILE, PLAYERS_KEY_IN_CONFIG, get_role_string, GAME_START_TIME_FILE, PERSONAL_CHAT_FILE_FORMAT, \
    MESSAGE_PARSING_PATTERN, SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_USE_TURN_LOG, MODEL_CHOSE_TO_PASS_TURN_LOG
from game_status_checks import is_nighttime
from llm_players.llm_constants import turn_task_into_prompt, GENERAL_SYSTEM_INFO, \
    PASS_TURN_TOKEN_KEY, USE_TURN_TOKEN_KEY, WORDS_PER_SECOND_WAITING_KEY, PASS_TURN_TOKEN_OPTIONS
# from llm_players.llm_wrapper import LLMWrapper
from llm_players.logger import Logger

from llm.llm import * # cocochief's implementation


class LLMPlayer(ABC):

    TYPE_NAME = None

    def __init__(self, name, is_mafia, llm_config, game_dir, **kwargs):
        self.name = name
        self.is_mafia = is_mafia
        self.role = get_role_string(is_mafia)
        self.game_dir = game_dir
        self.logger = Logger(name, game_dir)
        self.pass_turn_token = llm_config[PASS_TURN_TOKEN_KEY]
        self.use_turn_token = llm_config[USE_TURN_TOKEN_KEY]
        self.num_words_per_second_to_wait = llm_config[WORDS_PER_SECOND_WAITING_KEY]
        # self.llm = LLMWrapper(self.logger, **llm_config)
        print("creating llm...", flush=True)
        self.llm = create_llm(self.logger, **llm_config)

    def get_system_info_message(self, attention_to_not_repeat=False, only_special_tokens=False):
        system_info = f"Your name is {self.name}.{GENERAL_SYSTEM_INFO} \n" \
                      f"You were assigned the following role: {self.role}. \n"
        chat_room_open_time = (self.game_dir / GAME_START_TIME_FILE).read_text().strip()
        if chat_room_open_time:  # if the game has started, the file isn't empty
            system_info += f"The game's chat room was open at [{chat_room_open_time}].\n"
            system_info += f"The other players in the game are:\n"
            with open (self.game_dir / GAME_CONFIG_FILE, "r", encoding='utf-8') as f:
                config = json.load(f)
                players = (self.game_dir / "player_names.txt").read_text().splitlines()
                remaining_players = (self.game_dir / "remaining_players.txt").read_text().splitlines()
                i = -1
                for player in players:
                    i += 1
                    if player != self.name:
                        # reveal the role only if the self player is a mafia or the player is dead
                        player_role = get_role_string(config[PLAYERS_KEY_IN_CONFIG][i]['is_mafia']) if self.is_mafia or player not in remaining_players else "unknown"
                        system_info += f" {player} ( {player_role} ) \n"
                system_info += f"The other players that have not been eliminated (lynched or killed) yet are:\n"
                i = -1
                for player in players:
                    i += 1
                    if player != self.name and player in remaining_players:
                        player_role = get_role_string(config[PLAYERS_KEY_IN_CONFIG][i]['is_mafia']) if self.is_mafia else "unknown"
                        system_info += f"{player} ( {player_role} ) \n"
        if attention_to_not_repeat:
            # system_info += "Note: Do not repeat any messages already present in the message history below!\n"
            """ system_info += "IMPORTANT RULES FOR RESPONSES:\n" \
                           "1. Never repeat the exact messages you've said before! " \
                           "(as detailed bellow)\n" \
                           "2. Your response must be different in both wording and meaning " \
                           "from your previous messages.\n" \
                           "3. Keep your message short and casual, " \
                           "matching the style of recent messages.\n" \
                           "4. Don't use comma or other punctuation marks.\n" \
                           "5. Focus on adding new information or reactions " \
                           "to the current situation.\n" \
                           "6. Don't start messages with common phrases you've used before.\n" """
            previous_messages = (self.game_dir / PERSONAL_CHAT_FILE_FORMAT.format(self.name)
                                 ).read_text().splitlines()
            if previous_messages:
                system_info += "The following message are the previous messages that you've " \
                               "sent and you should never repeat:\n"
                for message in previous_messages:
                    matcher = re.match(MESSAGE_PARSING_PATTERN, message)
                    if not matcher:
                        continue
                    message_content = matcher.group(5)  # depends on MESSAGE_PARSING_PATTERN
                    system_info += f"* \"{message_content}\"\n"
        if only_special_tokens:
                            # First line to try and prevent conflict with o4-mini hidden scratchpad.
            system_info += f"In your response to that is shown to the user (excluding your hidden scratchpad), " \
                           f"you can ONLY respond with one of two possible outputs:\n" \
                           f"{self.pass_turn_token} - indicating your character in the game " \
                           f"should wait and not send a message in the current timing;\n" \
                           f"{self.use_turn_token} - indicating your character in the game should " \
                           f"send a message to the public chat now.\n\n" \
                           f"You must NEVER output any other text, explanations, or variations " \
                           f"of these tokens. Only these exact tokens are allowed: " \
                           f"{self.pass_turn_token} or {self.use_turn_token}.\n"
        return system_info

    @abstractmethod
    def should_generate_message(self, context):
        raise NotImplementedError()

    @abstractmethod
    def generate_message(self, message_history):
        raise NotImplementedError()

    def interpret_scheduling_decision(self, decision):
        if not decision:
            generate = False
        elif self.pass_turn_token in decision:
            generate = False
        elif self.use_turn_token in decision:
            generate = True
        # for more robustness:
        elif any([option in decision for option in PASS_TURN_TOKEN_OPTIONS]):
            generate = False
        else:
            generate = True
        if generate:
            self.logger.log(SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_USE_TURN_LOG)
        else:
            self.logger.log(SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_PASS_TURN_LOG)
        return generate

    def get_vote(self, message_history, candidate_vote_names):
        task_nighttime = f"Since you are a mafia, it is now time for you to determine who you want to kill. " \
               f"From the following remaining players, which player you want " \
               f"to kill? Base your answer on the conversation as seen in the message " \
               f"history, and especially on what you ({self.name}) said. " \
               f"Think through your choice carefully, as it will affect the game outcome. " \
               f"Reply with only one name from the list, and nothing but that name: "
        task_daytime = f"From the following remaining players, which player you want to vote for " \
               f"to lynch? Base your answer on the conversation as seen in the message " \
               f"history, and especially on what you ({self.name}) said. " \
               f"Think through your choice carefully, as it will affect the game outcome. " \
               f"Reply with only one name from the list, and nothing but that name: "
        task = ""
        if is_nighttime(self.game_dir):
            task = task_nighttime
        else:
            task = task_daytime
        task += ", ".join(candidate_vote_names)
        prompt = turn_task_into_prompt(task, message_history)
        system_info = self.get_system_info_message()
        self.logger.log("prompt for get_vote", prompt)
        self.logger.log("system_info for get_vote", system_info)
        vote = self.llm.generate(prompt, system_info)
        self.logger.log("generated vote in get_vote", vote)
        return vote
