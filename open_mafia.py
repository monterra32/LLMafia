#!/usr/bin/env python3
import os
import re
import subprocess
import sys

# ─────────── EDIT THESE ───────────
ANACONDA_ROOT     = "C:\\Users\\cococ\\anaconda3"  # Full path to Anaconda/Miniconda root
ENV_NAME          = 'LLMafia-env'                  # Name of the Conda environment to activate
TARGET_DIR        = "C:\\Users\\cococ\\Documents\\GitHub\\LLMafia"  # Root project folder
CONFIG_DIR        = os.path.join(TARGET_DIR, 'configurations')  # Directory where config files are stored
CONFIG_FILE_NAME  = 'openai_5_5.json'               # Config file in format word_n_m.json
# ────────────────────────────────────


def open_ps_window(commands):
    """
    Opens a new PowerShell window and runs a list of commands in one session.
    Keeps the window open afterwards.
    """
    # 1) join commands with semicolons
    body = "; ".join(commands)
    # 2) wrap in a script block so PowerShell -Command executes them all sequentially
    script = f"& {{ {body} }}"
    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-Command", script
            ],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except Exception as e:
        print(f"Failed to open PowerShell window: {e}")


def main():
    # Resolve and validate paths
    hook_script = os.path.join(ANACONDA_ROOT, 'shell', 'condabin', 'conda-hook.ps1')
    config_path = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)
    base_name   = os.path.splitext(CONFIG_FILE_NAME)[0]

    # Extract n (total players) and m (number of LLMs)
    match = CONFIG_FILE_NAME.split('.')[0].split('_')
    if not match[1].isdigit() or not match[2].isdigit():
        print("CONFIG_FILE_NAME must be in the form word_n_m.json (e.g. abcd_8_3.json)")
        sys.exit(1)
    n = int(match[1])
    m = int(match[2])

    # Common commands: hook, activate, cd
    hook      = f"& '{hook_script}'"
    activate  = f"conda activate '{ENV_NAME}'"
    cd_cmd    = f"Set-Location -Path '{TARGET_DIR}'"

    # 1) Setup window: prepare_game -> mafia_main
    open_ps_window([
        hook,
        activate,
        cd_cmd,
        f"python prepare_game.py -c '{config_path}'",
        "python mafia_main.py"
    ])

    # 2) m windows for LLM players
    for i in range(1, m+1):
        open_ps_window([
            hook,
            activate,
            cd_cmd,
            f"echo {i} | python llm_interface.py"
        ])

    # 3) (n-m) windows for human players
    human_count = n - m
    for j in range(1, human_count+1):
        open_ps_window([
            hook,
            activate,
            cd_cmd,
            f"echo {j} | python player_merged_chat_and_input.py"
        ])
    
    # Create a spectator window
    open_ps_window([
        hook,
        activate,
        cd_cmd,
        "python spectator_chat.py"
    ])
    


if __name__ == '__main__':
    main()
