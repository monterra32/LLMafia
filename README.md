# LLMafia - Asynchronous LLM Agent for Mafia Games

A research project for playing the social deduction game **Mafia** with LLM agents and human players. The LLM agents decide both *what to say* and *when to say it*, simulating natural asynchronous group conversation.

![](figures/llmafia_cover_figure.gif)

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [API Key Setup](#api-key-setup)
- [Quick Start Guide](#quick-start-guide)
- [Running a Game Step-by-Step](#running-a-game-step-by-step)
- [Game Configuration](#game-configuration)
- [Creating Custom Configurations](#creating-custom-configurations)
- [Viewing Game Logs](#viewing-game-logs)
- [Project Structure](#project-structure)
- [Citation](#citation)

---

## Overview

### The Game of Mafia

Mafia is a social deduction game where players are secretly assigned roles:
- **Mafia**: Know each other's identities, try to eliminate bystanders
- **Bystanders**: Must identify and vote out the mafia

**Game Flow:**
1. **Daytime Phase**: All players discuss and vote to eliminate one player
2. **Nighttime Phase**: Mafia secretly chooses a bystander to eliminate
3. Game continues until mafia outnumber bystanders (mafia wins) or all mafia are eliminated (bystanders win)

### The LLM Agent

The LLM agent uses a two-module design:
- **Scheduler**: Decides *when* to send a message
- **Generator**: Decides *what* to say

![](figures/agent_logic_design_figure.gif)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/LLMafia.git
cd LLMafia
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the Games Directory

```bash
mkdir games
```

---

## API Key Setup

The project supports **OpenAI** and **Together AI** models. Set up your API key using one of these methods:

### Option 1: Environment Variable (Recommended)

```bash
# For OpenAI
export OPENAI_API_KEY="sk-your-api-key-here"

# For Together AI
export TOGETHER_API_KEY="your-together-api-key"
```

Add to `~/.zshrc` or `~/.bashrc` for persistence:

```bash
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Option 2: Secrets File

Create a file named `.secrets_dict.txt` in the project root:

```python
{"OPENAI_API_KEY": "sk-your-api-key-here", "TOGETHER_API_KEY": "your-key"}
```

---

## Quick Start Guide

Here's the fastest way to run a game using the `openai_5_4.json` configuration (5 players, 4 LLMs, 1 human):

```bash
# Terminal 1: Prepare and start the game manager
cd /path/to/LLMafia
mkdir -p games

# 1. Creates the game
python prepare_game.py -c configurations/openai_5_4.json -i <game number>

# 2. Run Game Manager (game number optional)
python mafia_main.py -i <game_number>

# 3. Run Spectator (game number optional)
python spectator_chat.py -i <game_number>

# 4. Run LLM Players
# Terminal 2-5: Start the # LLM players (game number optional)
python llm_interface.py  -i <game_number>
python llm_interface.py  -i <game_number>
python llm_interface.py  -i <game_number>
python llm_interface.py  -i <game_number>

# 5. Terminal 6: Human player interface
python player_merged_chat_and_input.py -i <game_number>
```

---

## Running a Game Step-by-Step

### Step 1: Prepare the Game

This creates a new game directory with all necessary files:

```bash
python prepare_game.py -c configurations/openai_5_4.json
```

**Options:**
- `-c CONFIG_PATH`: Path to configuration file (default: `configurations/openai-5-4-1.json`)
- `-i GAME_ID`: Explicit game ID (default: auto-generated)

Output example:
```
Generated a new game id: 0001
Successfully created a new game dir in: ./games/0001
```

### Step 2: Start the Game Manager

```bash
python mafia_main.py -i 0001
```

The game manager:
- Waits for all players to join
- Controls game phases (daytime/nighttime)
- Handles voting and eliminations
- Determines the winner

### Step 3: Start LLM Players

Each LLM player runs in a separate terminal:

```bash
python llm_interface.py -i 0001
```

If multiple LLM players exist, you'll be prompted to select which one:
```
This game has multiple LLM players, which one you want to run now?
1: Addison,   2: Ronny,   3: Frankie,   4: Ari
```

**Tip:** Use `echo N | python llm_interface.py` to auto-select player N.

### Step 4: Start Human Player Interface

**Option A: Merged Interface** (recommended for single terminal)
```bash
python player_merged_chat_and_input.py -i 0001
```

**Option B: Separate Interfaces** (original design)
```bash
# Terminal A: View chat
python player_chat.py -i 0001

# Terminal B: Send messages and vote
python player_input.py -i 0001
```

### Step 5: Play the Game!

Once all players join, the game starts automatically:
- **Daytime**: Discuss who might be mafia, then vote
- **Nighttime**: Mafia chooses a victim (bystanders wait)
- Type `VOTE` when prompted to cast your vote

### Step 6: Watch as Spectator (Optional)

See all messages including mafia's secret chat:

```bash
python spectator_chat.py -i 0001
```

---

## Game Configuration

### Example: `openai_5_4.json`

```json
{
    "players": [
        {
            "name": "Addison",
            "is_mafia": false,
            "is_llm": true,
            "real_name": "LLM0",
            "llm_config": {
                "model_name": "o4-mini",
                "use_openai": true,
                "async_type": "schedule_then_generate",
                ...
            }
        },
        {
            "name": "Emerson",
            "is_mafia": false,
            "is_llm": false,
            "real_name": "chris",
            "llm_config": {}
        },
        ...
    ],
    "daytime_minutes": 1.5,
    "nighttime_minutes": 0.5
}
```

### Configuration Fields

| Field | Description |
|-------|-------------|
| `players` | Array of player configurations |
| `players[].name` | In-game codename |
| `players[].is_mafia` | Whether player is mafia |
| `players[].is_llm` | Whether player is an LLM agent |
| `players[].real_name` | Real name (human) or identifier (LLM) |
| `players[].llm_config` | LLM-specific settings |
| `daytime_minutes` | Duration of daytime discussion |
| `nighttime_minutes` | Duration of nighttime phase |

### LLM Configuration Options

| Option | Description |
|--------|-------------|
| `model_name` | Model to use (`o4-mini`, `gpt-4o`, etc.) |
| `use_openai` | Use OpenAI API |
| `use_together` | Use Together AI API |
| `async_type` | Agent type (`schedule_then_generate`) |
| `temperature` | Sampling temperature |
| `max_tokens` | Maximum response tokens |

---

## Creating Custom Configurations

### Using `prepare_config.py`

Generate configs with **random role assignment**:

```bash
python prepare_config.py -o my_game.json -p 5 -m 1 -l 3 -n names.txt
```

**Options:**

| Flag | Description |
|------|-------------|
| `-o` | Output filename |
| `-p` | Total number of players |
| `-m` | Number of mafia players |
| `-l` | Number of LLM players |
| `-b` | LLM can only be bystander |
| `-n` | File with human player names (one per line) |
| `-dt` | Daytime minutes |
| `-nt` | Nighttime minutes |
| `-j` | Path to custom LLM config JSON |

**Example: 7-player game with 2 mafia, 4 LLMs:**

```bash
# Create names file
echo -e "Alice\nBob\nCharlie" > names.txt

# Generate config
python prepare_config.py -o custom_game.json -p 7 -m 2 -l 4 -n names.txt -dt 3 -nt 1
```

---

## Viewing Game Logs

### During the Game

Use the spectator view to see all chat including mafia's secret discussions:

```bash
python spectator_chat.py -i 0001
```

### After the Game

All logs are stored in `./games/XXXX/`:

| File | Content |
|------|---------|
| `public_daytime_chat.txt` | Daytime discussion messages |
| `public_nighttime_chat.txt` | Mafia nighttime chat |
| `public_manager_chat.txt` | Game announcements (votes, eliminations) |
| `{PlayerName}_chat.txt` | Individual player's messages |
| `{PlayerName}_vote.txt` | Player's votes |
| `{PlayerName}_log.txt` | LLM player's internal logs |
| `config.json` | Game configuration |
| `who_wins.txt` | Final result |
| `mafia_names.txt` | Mafia player names |

**View complete game history:**

```bash
# All public messages
cat games/0001/public_manager_chat.txt games/0001/public_daytime_chat.txt

# Include mafia's secret chat
cat games/0001/public_nighttime_chat.txt

# LLM reasoning logs
cat games/0001/Addison_log.txt
```

---

## Project Structure

```
LLMafia/
├── prepare_config.py      # Generate game configurations
├── prepare_game.py        # Initialize a new game
├── mafia_main.py          # Game manager (run the game)
├── llm_interface.py       # LLM player interface
├── player_chat.py         # Human player chat view
├── player_input.py        # Human player input
├── player_merged_chat_and_input.py  # Combined human interface
├── spectator_chat.py      # Watch all game messages
├── game_constants.py      # Game settings and constants
├── game_status_checks.py  # Game state utilities
├── configurations/        # Pre-made game configs
│   ├── openai_5_4.json
│   ├── openai_3_2.json
│   └── ...
├── llm/
│   └── llm.py            # LLM API implementations
├── llm_players/
│   ├── llm_player.py     # Base LLM player class
│   ├── schedule_then_generate_player.py  # Main agent implementation
│   ├── llm_constants.py  # Prompts and LLM settings
│   └── factory.py        # Player factory
├── games/                 # Game data (created at runtime)
│   └── 0001/
│       ├── config.json
│       ├── public_daytime_chat.txt
│       └── ...
└── requirements.txt
```

---

## Citation

If you find this useful for your research, please cite:

```bibtex
@misc{eckhaus2025timetalkllmagents,
      title={Time to Talk: LLM Agents for Asynchronous Group Communication in Mafia Games}, 
      author={Niv Eckhaus and Uri Berger and Gabriel Stanovsky},
      year={2025},
      eprint={2506.05309},
      archivePrefix={arXiv},
      primaryClass={cs.MA},
      url={https://arxiv.org/abs/2506.05309}, 
}
```

---

## Links

- 🌐 [Project Page](https://niveck.github.io/Time-to-Talk/)
- 📃 [Paper](https://arxiv.org/abs/2506.05309)
- 📚 [Dataset on HuggingFace](https://huggingface.co/datasets/niveck/LLMafia)
