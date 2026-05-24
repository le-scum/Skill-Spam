import ctypes
import json
import os
import time
import tkinter as tk
from tkinter import messagebox


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "pandora_saga_bot_config.json")
BOT_CLICK_INTERVAL_MS = 100
POST_SPAM_WAIT_MS = 5000

user32 = ctypes.windll.user32
SetCursorPos = user32.SetCursorPos
GetAsyncKeyState = user32.GetAsyncKeyState
GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
EnumWindows = user32.EnumWindows

PUL = ctypes.POINTER(ctypes.c_ulong)
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_vk_name(vk: int) -> str:
    try:
        MAPVK_VK_TO_VSC = 0
        sc = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        lparam = sc << 16
        buf = ctypes.create_unicode_buffer(64)
        res = user32.GetKeyNameTextW(lparam, buf, 64)
        if res > 0:
            return buf.value
    except Exception:
        pass
    return str(vk)


def click_left_mouse() -> None:
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def move_and_click(x: int, y: int) -> None:
    SetCursorPos(x, y)
    click_left_mouse()


def get_open_windows() -> list[str]:
    titles: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        length = GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if title:
            titles.append(title)
        return True

    EnumWindows(enum_proc, None)
    return sorted(set(titles))


def use_active_window_title() -> str:
    hwnd = GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("Could not detect the active window.")
    length = GetWindowTextLengthW(hwnd)
    if length <= 0:
        raise RuntimeError("The active window does not have a usable title.")
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    title = buffer.value.strip()
    if not title:
        raise RuntimeError("The active window does not have a usable title.")
    return title


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


root = tk.Tk()
root.title("Pandora Saga Mouse Bot")
root.geometry("640x420")
root.minsize(620, 390)
root.resizable(True, True)

cfg = load_config()

bot_running = False
bot_paused = False
current_phase = "Idle"
phase_started_at = time.monotonic()
phase_max_ms = 0
hotkey_vk = int(cfg.get("stop_hotkey_vk", 0x24))
hotkey_label_var = tk.StringVar(value=f"Control hotkey: {hotkey_vk}")
hotkey_name_var = tk.StringVar(value=str(cfg.get("stop_hotkey_name", get_vk_name(hotkey_vk))))
last_hotkey_state = False


def monitor_hotkey() -> None:
    """Periodically check the configured virtual-key and toggle pause/resume on press.

    Uses rising-edge detection so holding the key doesn't repeatedly toggle state.
    """
    global last_hotkey_state
    try:
        state = bool(GetAsyncKeyState(hotkey_vk) & 0x8000)
    except Exception:
        state = False

    if state and not last_hotkey_state:
        try:
            pause_resume_bot()
        except Exception:
            pass

    last_hotkey_state = state
    root.after(100, monitor_hotkey)


def set_phase(name: str, max_ms: int) -> None:
    global current_phase, phase_started_at, phase_max_ms
    current_phase = name
    phase_started_at = time.monotonic()
    phase_max_ms = max_ms


def phase_text() -> str:
    elapsed_ms = int((time.monotonic() - phase_started_at) * 1000)
    if phase_max_ms > 0:
        elapsed_ms = min(elapsed_ms, phase_max_ms)
        return f"{current_phase}  {elapsed_ms/1000:.1f} / {phase_max_ms/1000:.1f} s"
    return f"{current_phase}  {elapsed_ms/1000:.1f} s"


phase_var = tk.StringVar(value=phase_text())


def refresh_phase() -> None:
    phase_var.set(phase_text())
    root.after(100, refresh_phase)


def stop_bot() -> None:
    global bot_running, bot_paused
    bot_running = False
    bot_paused = False
    set_phase("Stopped", 0)
    bot_status_var.set("Stopped.")


def pause_resume_bot() -> None:
    global bot_paused
    if not bot_running:
        start_bot()
        return
    bot_paused = not bot_paused
    bot_status_var.set("Paused." if bot_paused else "Resumed.")
    set_phase("Paused" if bot_paused else "Running", 0)


def control_action() -> None:
    if not bot_running:
        start_bot()
    elif bot_paused:
        pause_resume_bot()
    else:
        pause_resume_bot()


def capture_hotkey() -> None:
    global hotkey_vk
    picker = tk.Toplevel(root)
    picker.title("Set Control Hotkey")
    picker.attributes("-topmost", True)
    picker.geometry("300x110")
    tk.Label(picker, text="Press a key to use as the control hotkey.", wraplength=260).pack(pady=18)

    def on_key(event: tk.Event) -> None:
        global hotkey_vk
        hotkey_vk = int(getattr(event, "keycode", 0))
        # show human-readable key (keysym) in the UI
        name = getattr(event, "keysym", None) or get_vk_name(hotkey_vk)
        hotkey_name_var.set(str(name))
        hotkey_label_var.set(f"Control hotkey: {hotkey_vk}")
        save_current_config()
        picker.destroy()

    picker.bind("<KeyPress>", on_key)
    picker.focus_force()


def save_current_config() -> None:
    data = {
        "sit_x": sit_x_var.get().strip(),
        "sit_y": sit_y_var.get().strip(),
        "skill_x": skill_x_var.get().strip(),
        "skill_y": skill_y_var.get().strip(),
        # store times as milliseconds in the config
        "sit_time_ms": int(float(sit_time_var.get()) * 1000),
        "spam_time_ms": int(float(spam_time_var.get()) * 1000),
        "post_spam_wait_ms": int(float(post_wait_var.get()) * 1000),
        "stop_hotkey_name": hotkey_name_var.get(),
        "stop_hotkey_vk": hotkey_vk,
        "window": window_var.get(),
    }
    save_config(data)


def update_windows() -> None:
    windows = get_open_windows() or [""]
    menu = window_menu["menu"]
    menu.delete(0, "end")
    for title in windows:
        menu.add_command(label=title, command=lambda v=title: window_var.set(v))
    if window_var.get() not in windows:
        window_var.set(windows[0])


def set_active_window(var: tk.StringVar, status_var: tk.StringVar) -> None:
    try:
        var.set(use_active_window_title())
        status_var.set(f"Selected active window: {var.get()}")
    except Exception as exc:
        messagebox.showerror("No active window", str(exc))


def capture_point(x_var: tk.StringVar, y_var: tk.StringVar, label: str) -> None:
    picker = tk.Toplevel(root)
    picker.attributes("-fullscreen", True)
    picker.attributes("-topmost", True)
    picker.attributes("-alpha", 0.15)
    picker.configure(bg="black")
    picker.overrideredirect(True)
    picker.focus_force()

    tk.Label(
        picker,
        text=f"Click the {label} location anywhere on the screen",
        fg="white",
        bg="black",
        font=("Segoe UI", 20, "bold"),
    ).pack(expand=True)

    def finish(event: tk.Event) -> None:
        x_var.set(str(event.x_root))
        y_var.set(str(event.y_root))
        save_current_config()
        picker.destroy()

    picker.bind("<Button-1>", finish)
    picker.bind("<Escape>", lambda _e: picker.destroy())


def start_bot() -> None:
    global bot_running, bot_paused
    if bot_running:
        return
    bot_running = True
    bot_paused = False
    sit_x = int(sit_x_var.get() or 0)
    sit_y = int(sit_y_var.get() or 0)
    skill_x = int(skill_x_var.get() or 0)
    skill_y = int(skill_y_var.get() or 0)
    sit_time_sec = float(sit_time_var.get() or 0.0)
    spam_time_sec = float(spam_time_var.get() or 0.0)
    post_wait_sec = float(post_wait_var.get() or 0.0)
    # spam phase timing will be set at the start of each run_cycle

    def run_cycle() -> None:
        global bot_running, bot_paused
        if not bot_running:
            return
        if bot_paused:
            set_phase("Paused", 0)
            root.after(100, run_cycle)
            return

        # start the spam phase and record its duration (ms)
        set_phase("Skill spam", int(spam_time_sec * 1000))
        spam_deadline = time.monotonic() + spam_time_sec

        def spam_phase() -> None:
            global bot_running, bot_paused
            if not bot_running:
                return
            if bot_paused:
                set_phase("Paused", 0)
                root.after(100, spam_phase)
                return
            if time.monotonic() >= spam_deadline:
                def delayed_sit() -> None:
                    global bot_running, bot_paused
                    if not bot_running:
                        return
                    if bot_paused:
                        set_phase("Paused", 0)
                        root.after(100, delayed_sit)
                        return

                    move_and_click(sit_x, sit_y)
                    set_phase("Sit hold", int(sit_time_sec * 1000))
                    bot_status_var.set(f"Clicked sit at ({sit_x}, {sit_y}).")

                    def finish_sit() -> None:
                        global bot_running, bot_paused
                        if not bot_running:
                            return
                        if bot_paused:
                            set_phase("Paused", 0)
                            root.after(100, finish_sit)
                            return
                        move_and_click(sit_x, sit_y)
                        set_phase("Post-sit wait", int(post_wait_sec * 1000))
                        root.after(int(post_wait_sec * 1000), run_cycle)

                    root.after(int(sit_time_sec * 1000), finish_sit)

                root.after(int(post_wait_sec * 1000), delayed_sit)
                return

            move_and_click(skill_x, skill_y)
            root.after(BOT_CLICK_INTERVAL_MS, spam_phase)

        spam_phase()

    run_cycle()


def stop_and_save() -> None:
    save_current_config()
    root.destroy()


window_var = tk.StringVar(value=str(cfg.get("window", "")))
try:
    # save when the selected window changes
    window_var.trace_add("write", lambda *a: save_current_config())
except Exception:
    try:
        window_var.trace("w", lambda *a: save_current_config())
    except Exception:
        pass
sit_x_var = tk.StringVar(value=str(cfg.get("sit_x", "0")))
sit_y_var = tk.StringVar(value=str(cfg.get("sit_y", "0")))
skill_x_var = tk.StringVar(value=str(cfg.get("skill_x", "0")))
skill_y_var = tk.StringVar(value=str(cfg.get("skill_y", "0")))
# UI shows seconds, config stores milliseconds. Use DoubleVar for seconds.
sit_time_var = tk.DoubleVar(value=float(cfg.get("sit_time_ms", 1000)) / 1000.0)
spam_time_var = tk.DoubleVar(value=float(cfg.get("spam_time_ms", 1000)) / 1000.0)
post_wait_var = tk.DoubleVar(value=float(cfg.get("post_spam_wait_ms", 5000)) / 1000.0)
bot_status_var = tk.StringVar(value="Ready. Configure positions and start the bot.")

# Load background image if available and place it behind the UI
bg_path = os.path.join(os.path.dirname(__file__), "background.png")
if os.path.exists(bg_path):
    try:
        bg_image = tk.PhotoImage(file=bg_path)
        bg_label = tk.Label(root, image=bg_image)
        bg_label.image = bg_image
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        bg_label.lower()
    except Exception:
        bg_image = None

# Dark theme colors
UI_BG = "#1f1f1f"
ENTRY_BG = "#2b2b2b"
BTN_BG = "#2f2f2f"
FG = "#e6e6e6"
root.configure(bg=UI_BG)


tk.Label(root, text="Pandora Saga Mouse Bot by Noize", font=("Segoe UI", 14, "bold"), bg=UI_BG, fg=FG).pack(pady=(12, 6))
tk.Label(root, textvariable=bot_status_var, bg=UI_BG, fg=FG).pack(fill="x", padx=16)
tk.Label(root, textvariable=phase_var, font=("Segoe UI", 9, "bold"), bg=UI_BG, fg=FG).pack(fill="x", padx=16, pady=(4, 8))

window_row = tk.Frame(root, bg=UI_BG)
window_row.pack(fill="x", padx=16, pady=(6, 0))
tk.Label(window_row, text="Game window:", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
window_menu = tk.OptionMenu(window_row, window_var, "")
window_menu.pack(side=tk.LEFT, fill="x", expand=True, padx=8)
window_menu.config(bg=BTN_BG, fg=FG, activebackground=BTN_BG, activeforeground=FG)
window_menu['menu'].config(bg=UI_BG, fg=FG)
tk.Button(window_row, text="Refresh", command=update_windows, bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=4)
tk.Button(window_row, text="Use active", command=lambda: set_active_window(window_var, bot_status_var), bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=4)

coords = tk.Frame(root, bg=UI_BG)
coords.pack(fill="x", padx=16, pady=10)

sit_box = tk.LabelFrame(coords, text="Sit location", bg=UI_BG, fg=FG)
sit_box.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 8))
tk.Entry(sit_box, textvariable=sit_x_var, width=8, bg=ENTRY_BG, fg=FG, insertbackground=FG).grid(row=0, column=0, padx=6, pady=6)
tk.Entry(sit_box, textvariable=sit_y_var, width=8, bg=ENTRY_BG, fg=FG, insertbackground=FG).grid(row=0, column=1, padx=6, pady=6)
tk.Button(sit_box, text="Set Location", command=lambda: capture_point(sit_x_var, sit_y_var, "sit"), bg=BTN_BG, fg=FG, activebackground=BTN_BG).grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

skill_box = tk.LabelFrame(coords, text="Skill location", bg=UI_BG, fg=FG)
skill_box.pack(side=tk.LEFT, fill="both", expand=True, padx=(8, 0))
tk.Entry(skill_box, textvariable=skill_x_var, width=8, bg=ENTRY_BG, fg=FG, insertbackground=FG).grid(row=0, column=0, padx=6, pady=6)
tk.Entry(skill_box, textvariable=skill_y_var, width=8, bg=ENTRY_BG, fg=FG, insertbackground=FG).grid(row=0, column=1, padx=6, pady=6)
tk.Button(skill_box, text="Set Location", command=lambda: capture_point(skill_x_var, skill_y_var, "skill"), bg=BTN_BG, fg=FG, activebackground=BTN_BG).grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

timing = tk.Frame(root, bg=UI_BG)
timing.pack(fill="x", padx=16, pady=6)
for label, var in (("Sit Duration (sec):", sit_time_var), ("Spam Duration (sec):", spam_time_var), ("Cooldown (sec):", post_wait_var)):
    row = tk.Frame(timing, bg=UI_BG)
    row.pack(fill="x", pady=2)
    tk.Label(row, text=label, width=18, anchor="w", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
    tk.Spinbox(row, from_=0, to=600, increment=0.1, textvariable=var, width=10, bg=ENTRY_BG, fg=FG, insertbackground=FG).pack(side=tk.LEFT)

controls = tk.Frame(root, bg=UI_BG)
controls.pack(pady=12)
tk.Button(controls, text="Start", width=12, command=start_bot, bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=6)
tk.Button(controls, text="Stop", width=12, command=stop_bot, bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=6)
tk.Button(controls, text="Pause/Resume", width=12, command=pause_resume_bot, bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=6)
tk.Button(controls, text="Set Control Hotkey", width=16, command=capture_hotkey, bg=BTN_BG, fg=FG, activebackground=BTN_BG).pack(side=tk.LEFT, padx=6)

tk.Label(root, textvariable=hotkey_label_var, bg=UI_BG, fg=FG).pack(pady=(0, 2))
tk.Label(root, textvariable=hotkey_name_var, bg=UI_BG, fg=FG).pack(pady=(0, 8))

update_windows()
refresh_phase()
monitor_hotkey()
root.protocol("WM_DELETE_WINDOW", stop_and_save)
root.mainloop()
