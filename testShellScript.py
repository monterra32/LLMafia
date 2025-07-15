import subprocess

def open_ps_window(commands):
    """
    Opens a new PowerShell window and runs a list of commands in one session.
    Keeps the window open afterwards.
    """
    # 1) join them with semicolons
    body = "; ".join(commands)
    # 2) wrap in a script block so -Command sees it as one unit
    script = f"& {{ {body} }}"
    subprocess.Popen(
        ["powershell.exe", "-NoExit", "-Command", script],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

# ─── EDIT THESE ───
ANACONDA_ROOT = r"C:\Users\cococ\anaconda3"
ENV_NAME      = "LLMafia-env"
TARGET_DIR    = r"C:\Users\cococ\Documents\GitHub\LLMafia"
# ──────────────────

hook = rf"& '{ANACONDA_ROOT}\shell\condabin\conda-hook.ps1'"

# Example: echo 1 and echo 2 in one new window
open_ps_window([
    hook,
    f"conda activate '{ENV_NAME}'",
    f"Set-Location -Path '{TARGET_DIR}'",
    "echo 1",
    "echo 2"
])
