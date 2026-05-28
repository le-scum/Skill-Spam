# Skill Spam ⚡
A lightweight automation tool for grinding profession levels in Pandora Saga — built entirely in Python.
<img width="755" height="707" alt="mpSgbdC" src="https://github.com/user-attachments/assets/144a8a40-f484-4416-866a-4cfa66c1262b" />


Skill Spam automates repetitive skill usage and sitting cycles by controlling mouse input on your selected game window. Designed for long AFK training sessions with configurable timers, hotkeys, and quick setup.

## ✨ Features
🎯 Target a specific game window\
🖱️ Automated spam mutliple skills + sit cycle\
⏱️ Adjustable durations and cooldowns\
⚠️ Smart logout detector\
⏸️ Pause / Resume support\
⌨️ Global hotkey controls\
🔄 Hard stop / reset functionality\
🐍 Fully written in Python\
🔍 Open source — all source code included

## 📦 Installation
[Download here](https://github.com/le-scum/Skill-Spam/releases) or clone the repository\
Extract the files into a folder\
Run mousebot_ui as Administrator ⚠️\
Configure your skill locations and timers\
Press Start\
Go AFK 😎

## 🚀 Usage

Skill Spam works by repeatedly clicking configured hotbar locations during two phases:

Skill Spam Phase — repeatedly casts skills
Sit Phase — forces your character to sit and regenerate resources

The bot alternates between these phases automatically based on your configured timers.

## ⚙️ Configuration Options
🎮 Game Window\
Select the game window the bot should focus and click inside.\
\
📍 Sit Location / Skill Location\
Click Set Location, then left-click the desired hotbar slot in-game.

Skill Location → Skill to spam\
Sit Location → Sit/rest skill location

⏳ Skill Duration\
Controls how long the bot continuously spams the selected skill.\
You can rotate up to 5 different skills to level different profiencies. Set the "Rotate Every X sec" to set how long each skill is spammed for before switching.

_Recommended values vary depending on:_\
<sup>Skill cooldowns, Character SPI, Mana usage, Animation timing</sup>

🪑 Sit Duration\
Controls how long your character remains sitting before returning to skill spam.\
Enable / Disable sitting phase: Allows user to disable the sitting phase\
\
⚠️ Logout Checker\
Checks to see if the player has been disconnected from the server and reconnects them.\
This portion of the bot has a smart feature and checks the screen for a certain dialog that appears on the login screen. If it detects this dialog, then it runs the clicks. If it does not detect the clicks, it skips it. Make sure your skill and sit clicks are not overlapping with the Connect and Begin button locations.\
\
Enable/Disable the logout checker\
Connect button and Begin button locations: Set these so the bot knows where to click.\
Loops before checking: How many Skill and Sit phases it goes through to check the client if its logged out.\
\
🕒 Cooldown\
Delay between switching phases.\
Recommended: 5 seconds\
**This value is important for preventing timing issues and maintaining consistent cycles.**\

▶️ Start Button\
Starts the automation beginning with the skill spam phase.\
\
⏹️ Stop Button\
Immediately stops and resets the bot.\
\
⏸️ Pause / Resume Button\
Temporarily pauses the bot and resumes when pressed again.\
\
⌨️ Set Pause / Resume Hotkey\
Assign a global hotkey to quickly pause/resume the bot while playing.\
\
⚠️ Administrator Rights Required\
Skill Spam must be run as Administrator in order to send mouse input outside of the application window.\
All source code is included in the repository for transparency and customization.

## 🐍 Built With
Python\
GUI automation libraries\
Global keyboard hooks\
bettercam\
opencv-python\
pillow

📜 Disclaimer\
This project is provided for educational and personal-use purposes only. Use responsibly and at your own risk.
