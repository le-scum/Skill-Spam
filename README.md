# Skill Spam ⚡
A lightweight automation tool for grinding profession levels in Pandora Saga — built entirely in Python.

Skill Spam automates repetitive skill usage and sitting cycles by controlling mouse input on your selected game window. Designed for long AFK training sessions with configurable timers, hotkeys, and quick setup.

## ✨ Features
🎯 Target a specific game window\
🖱️ Automated skill spam + sit cycle\
⏱️ Adjustable durations and cooldowns\
⏸️ Pause / Resume support\
⌨️ Global hotkey controls\
🔄 Hard stop / reset functionality\
🐍 Fully written in Python\
🔍 Open source — all source code included\

## 📦 Installation
Download here or clone the repository\
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
Click Set Location, then left-click the desired hotbar slot in-game.\
Skill Location → Skill to spam\
Sit Location → Sit/rest skill location\

⏳ Skill Duration\
Controls how long the bot continuously spams the selected skill.\

_Recommended values vary depending on:_\
<sup>Skill cooldowns, Character SPI, Mana usage, Animation timing</sup>

🪑 Sit Duration\
Controls how long your character remains sitting before returning to skill spam.\
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
⌨️ Set Control Hotkey\
Assign a global hotkey to quickly pause/resume the bot while playing.\
\
⚠️ Administrator Rights Required\
Skill Spam must be run as Administrator in order to send mouse input outside of the application window.\
All source code is included in the repository for transparency and customization.\

## 🐍 Built With
Python\
GUI automation libraries\
Global keyboard hooks

📜 Disclaimer\
This project is provided for educational and personal-use purposes only. Use responsibly and at your own risk.
