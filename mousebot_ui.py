import ctypes
import ctypes.wintypes
import json
import os
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import cv2
import numpy as np


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "pandora_saga_bot_config.json")
BOT_CLICK_INTERVAL_MS = 100
POST_SPAM_WAIT_MS = 5000
SKILL_LOCATION_COUNT = 5

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


def get_window_rect(window_title: str) -> tuple[int, int, int, int] | None:
    """Get window coordinates (x, y, width, height) by window title."""
    try:
        hwnd = None
        
        def enum_proc(h, _):
            nonlocal hwnd
            if not IsWindowVisible(h):
                return True
            length = GetWindowTextLengthW(h)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(h, buffer, length + 1)
            title = buffer.value.strip()
            # Try exact match first, then substring match (case-insensitive)
            if title == window_title or title.lower() == window_title.lower():
                hwnd = h
                return False
            if window_title.lower() in title.lower():
                hwnd = h
                return False
            return True
        
        EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_proc), None)
        
        if hwnd:
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            # Validate rect coordinates
            x, y, w, h = rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
            if w > 0 and h > 0:
                return (x, y, w, h)
    except Exception as e:
        print(f"Error in get_window_rect: {e}")
    return None


def take_window_screenshot(window_title: str) -> np.ndarray | None:
    """Take a screenshot of the specified window and return as BGR numpy array."""
    try:
        import PIL.ImageGrab
        
        print(f"[DEBUG] Taking screenshot for window: '{window_title}'")
        rect = get_window_rect(window_title)
        if not rect:
            print(f"[DEBUG] get_window_rect returned None for '{window_title}'")
            return None
        
        x, y, w, h = rect
        print(f"[DEBUG] Window rect: x={x}, y={y}, w={w}, h={h}")
        
        # Validate coordinates
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            print(f"[DEBUG] Invalid coordinates: x={x}, y={y}, w={w}, h={h}")
            return None
        
        # Capture the window area
        bbox = (x, y, x + w, y + h)
        print(f"[DEBUG] PIL.ImageGrab bbox: {bbox}")
        img = PIL.ImageGrab.grab(bbox=bbox)
        
        # Convert PIL Image to numpy array and BGR format
        img_array = np.array(img)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        print(f"[DEBUG] Screenshot captured successfully: shape={img_bgr.shape}")
        return img_bgr
    except Exception as e:
        print(f"[DEBUG] Exception in take_window_screenshot: {e}")
        import traceback
        traceback.print_exc()
        return None


def image_found_in_screenshot(window_title: str, template_path: str, threshold: float = 0.8) -> bool:
    """Check if the template image is found in the window screenshot."""
    try:
        screenshot = take_window_screenshot(window_title)
        if screenshot is None:
            return False
        
        if not os.path.exists(template_path):
            return False
        
        template = cv2.imread(template_path)
        if template is None:
            return False
        
        # Use template matching
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        return max_val >= threshold
    except Exception:
        return False


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
root.title("Pandora Saga Skill Spam Bot")
root.geometry("760x680")
root.minsize(720, 620)
root.resizable(True, True)

cfg = load_config()

bot_running = False
bot_paused = False
current_phase = "Idle"
phase_started_at = time.monotonic()
phase_max_ms = 0
hotkey_vk = int(cfg.get("stop_hotkey_vk", 0x24))
hotkey_label_var = tk.StringVar(value="Pause/Resume Hotkey:")
hotkey_name_var = tk.StringVar(value=str(cfg.get("stop_hotkey_name", get_vk_name(hotkey_vk))))
last_hotkey_state = False
capturing_hotkey = False


def monitor_hotkey() -> None:
    """Periodically check the configured virtual-key and toggle pause/resume on press.

    Uses rising-edge detection so holding the key doesn't repeatedly toggle state.
    """
    global last_hotkey_state
    if capturing_hotkey:
        last_hotkey_state = False
        root.after(100, monitor_hotkey)
        return

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
    global capturing_hotkey, hotkey_vk, last_hotkey_state
    capturing_hotkey = True
    last_hotkey_state = False
    picker = tk.Toplevel(root)
    picker.title("Set Control Hotkey")
    picker.attributes("-topmost", True)
    picker.geometry("300x110")
    tk.Label(picker, text="Press a key to use as the control hotkey.", wraplength=260).pack(pady=18)

    def close_picker() -> None:
        global capturing_hotkey, last_hotkey_state
        capturing_hotkey = False
        last_hotkey_state = False
        picker.destroy()

    def on_key(event: tk.Event) -> str:
        global hotkey_vk
        hotkey_vk = int(getattr(event, "keycode", 0))
        # show human-readable key (keysym) in the UI
        name = getattr(event, "keysym", None) or get_vk_name(hotkey_vk)
        hotkey_name_var.set(str(name))
        save_current_config()
        close_picker()
        return "break"

    picker.bind("<KeyPress>", on_key)
    picker.protocol("WM_DELETE_WINDOW", close_picker)
    picker.focus_force()


def allow_integer_input(value: str) -> bool:
    return value == "" or value.isdigit()


def read_int_var(var: tk.Variable, default: int = 0) -> int:
    try:
        value = str(var.get()).strip()
    except (tk.TclError, ValueError):
        return default
    if not value:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def save_current_config() -> None:
    skill_locations = [
        {"x": x_var.get().strip(), "y": y_var.get().strip()}
        for x_var, y_var in skill_location_vars
    ]
    data = {
        "sit_x": sit_x_var.get().strip(),
        "sit_y": sit_y_var.get().strip(),
        "sit_enabled": sit_enabled_var.get(),
        "logout_checker_enabled": logout_enabled_var.get(),
        "logout_connect_x": logout_connect_x_var.get().strip(),
        "logout_connect_y": logout_connect_y_var.get().strip(),
        "logout_begin_x": logout_begin_x_var.get().strip(),
        "logout_begin_y": logout_begin_y_var.get().strip(),
        "logout_loop_count": max(1, read_int_var(logout_loop_count_var, 1)),
        "skill_x": skill_locations[0]["x"],
        "skill_y": skill_locations[0]["y"],
        "skill_locations": skill_locations,
        "skill_location_enabled": [enabled_var.get() for enabled_var in skill_enabled_vars],
        "skill_rotate_time_ms": read_int_var(skill_rotate_time_var, 1) * 1000,
        # store times as milliseconds in the config
        "sit_time_ms": read_int_var(sit_time_var, 1) * 1000,
        "spam_time_ms": read_int_var(spam_time_var, 1) * 1000,
        "post_spam_wait_ms": read_int_var(post_wait_var, 5) * 1000,
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


def open_github_releases(_event: tk.Event | None = None) -> None:
    webbrowser.open("https://github.com/le-scum/Skill-Spam")


def start_bot() -> None:
    global bot_running, bot_paused
    if bot_running:
        return
    bot_running = True
    bot_paused = False
    sit_x = read_int_var(sit_x_var)
    sit_y = read_int_var(sit_y_var)
    sit_enabled = sit_enabled_var.get()
    logout_enabled = logout_enabled_var.get()
    logout_connect_x = read_int_var(logout_connect_x_var)
    logout_connect_y = read_int_var(logout_connect_y_var)
    logout_begin_x = read_int_var(logout_begin_x_var)
    logout_begin_y = read_int_var(logout_begin_y_var)
    logout_loops_before_check = max(1, read_int_var(logout_loop_count_var, 1))
    logout_loop_counter = 0
    skill_locations = [
        (read_int_var(x_var), read_int_var(y_var))
        for (x_var, y_var), enabled_var in zip(skill_location_vars, skill_enabled_vars)
        if enabled_var.get()
    ]
    sit_time_sec = read_int_var(sit_time_var)
    spam_time_sec = read_int_var(spam_time_var)
    skill_rotate_time_sec = read_int_var(skill_rotate_time_var)
    post_wait_sec = read_int_var(post_wait_var)
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
        set_phase("Spamming Skill(s)", int(spam_time_sec * 1000))
        spam_started_at = time.monotonic()
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
                if not sit_enabled:
                    set_phase("Sit disabled", 0)
                    bot_status_var.set("Sit phase skipped.")
                    root.after(BOT_CLICK_INTERVAL_MS, run_cycle)
                    return

                def delayed_sit() -> None:
                    global bot_running, bot_paused
                    nonlocal logout_loop_counter
                    if not bot_running:
                        return
                    if bot_paused:
                        set_phase("Paused", 0)
                        root.after(100, delayed_sit)
                        return

                    move_and_click(sit_x, sit_y)
                    set_phase("Sitting", int(sit_time_sec * 1000))
                    bot_status_var.set(f"Regaining MP.")

                    def finish_sit() -> None:
                        global bot_running, bot_paused
                        nonlocal logout_loop_counter
                        if not bot_running:
                            return
                        if bot_paused:
                            set_phase("Paused", 0)
                            root.after(100, finish_sit)
                            return
                        move_and_click(sit_x, sit_y)
                        set_phase("Post-sit wait", int(post_wait_sec * 1000))

                        if logout_enabled:
                            logout_loop_counter += 1
                            if logout_loop_counter >= logout_loops_before_check:
                                logout_loop_counter = 0

                                def check_logout_and_proceed() -> None:
                                    global bot_running, bot_paused
                                    if not bot_running:
                                        return
                                    if bot_paused:
                                        set_phase("Paused", 0)
                                        root.after(100, check_logout_and_proceed)
                                        return
                                    
                                    logout_image_path = os.path.join(os.path.dirname(__file__), "logout.png")
                                    window_title = window_var.get()
                                    
                                    # Validate window title
                                    if not window_title or not window_title.strip():
                                        available_windows = get_open_windows()
                                        bot_status_var.set(f"ERROR: No window selected. Available: {', '.join(available_windows[:3])}")
                                        print(f"ERROR: No window title set. Available windows: {available_windows}")
                                        root.after(15000, run_cycle)
                                        return
                                    
                                    # Check screenshot FIRST
                                    screenshot = take_window_screenshot(window_title)
                                    if screenshot is not None:
                                        try:
                                            debug_screenshot_path = os.path.join(os.path.dirname(__file__), "logout_check_debug.png")
                                            success = cv2.imwrite(debug_screenshot_path, screenshot)
                                            if success:
                                                bot_status_var.set(f"Debug screenshot saved: {debug_screenshot_path}")
                                                print(f"Screenshot saved successfully to {debug_screenshot_path}")
                                            else:
                                                bot_status_var.set(f"Failed to save screenshot: cv2.imwrite returned False")
                                                print(f"cv2.imwrite failed for {debug_screenshot_path}")
                                        except Exception as e:
                                            bot_status_var.set(f"Error saving screenshot: {str(e)}")
                                            print(f"Exception while saving screenshot: {e}")
                                    else:
                                        available_windows = get_open_windows()
                                        bot_status_var.set(f"ERROR: Could not find window '{window_title}'. Available: {', '.join(available_windows[:3])}")
                                        print(f"Failed to capture screenshot for window: '{window_title}'")
                                        print(f"Available windows: {available_windows}")
                                    
                                    # IF logout dialog is detected, click Connect then Begin
                                    if image_found_in_screenshot(window_title, logout_image_path):
                                        bot_status_var.set(f"Logout dialog detected. Clicking Connect at ({logout_connect_x}, {logout_connect_y}).")
                                        move_and_click(logout_connect_x, logout_connect_y)
                                        bot_status_var.set(f"Logout check: clicked Connect at ({logout_connect_x}, {logout_connect_y}).")
                                        
                                        # Click Begin button after a short delay
                                        def click_begin() -> None:
                                            if bot_running:
                                                move_and_click(logout_begin_x, logout_begin_y)
                                                bot_status_var.set(f"Logout check: clicked Begin at ({logout_begin_x}, {logout_begin_y}).")
                                        
                                        root.after(5000, click_begin)
                                        root.after(15000, run_cycle)
                                    else:
                                        bot_status_var.set("Logout dialog not detected. Skipping logout check.")
                                        root.after(15000, run_cycle)

                                root.after(int(post_wait_sec * 1000), check_logout_and_proceed)
                            else:
                                root.after(int(post_wait_sec * 1000), run_cycle)
                        else:
                            root.after(int(post_wait_sec * 1000), run_cycle)

                    root.after(int(sit_time_sec * 1000), finish_sit)

                root.after(int(post_wait_sec * 1000), delayed_sit)
                return

            if len(skill_locations) > 1 and skill_rotate_time_sec > 0:
                skill_index = int((time.monotonic() - spam_started_at) / skill_rotate_time_sec) % len(skill_locations)
            else:
                skill_index = 0
            if skill_locations:
                skill_x, skill_y = skill_locations[skill_index]
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
sit_enabled_var = tk.BooleanVar(value=bool(cfg.get("sit_enabled", True)))
logout_enabled_var = tk.BooleanVar(value=bool(cfg.get("logout_checker_enabled", False)))
logout_connect_x_var = tk.StringVar(value=str(cfg.get("logout_connect_x", "0")))
logout_connect_y_var = tk.StringVar(value=str(cfg.get("logout_connect_y", "0")))
logout_begin_x_var = tk.StringVar(value=str(cfg.get("logout_begin_x", "0")))
logout_begin_y_var = tk.StringVar(value=str(cfg.get("logout_begin_y", "0")))
logout_loop_count_var = tk.IntVar(value=int(cfg.get("logout_loop_count", 1)))
saved_skill_locations = cfg.get("skill_locations")
if not isinstance(saved_skill_locations, list):
    saved_skill_locations = [{"x": cfg.get("skill_x", "0"), "y": cfg.get("skill_y", "0")}]
saved_skill_locations = [
    location if isinstance(location, dict) else {"x": "0", "y": "0"}
    for location in saved_skill_locations[:SKILL_LOCATION_COUNT]
]
while len(saved_skill_locations) < SKILL_LOCATION_COUNT:
    saved_skill_locations.append({"x": "0", "y": "0"})
skill_location_vars = [
    (
        tk.StringVar(value=str(saved_skill_locations[i].get("x", "0"))),
        tk.StringVar(value=str(saved_skill_locations[i].get("y", "0"))),
    )
    for i in range(SKILL_LOCATION_COUNT)
]
saved_skill_enabled = cfg.get("skill_location_enabled")
if not isinstance(saved_skill_enabled, list):
    extra_enabled = bool(cfg.get("extra_skill_locations_enabled", False))
    saved_skill_enabled = [True] + [extra_enabled] * (SKILL_LOCATION_COUNT - 1)
saved_skill_enabled = [
    bool(value)
    for value in saved_skill_enabled[:SKILL_LOCATION_COUNT]
]
while len(saved_skill_enabled) < SKILL_LOCATION_COUNT:
    saved_skill_enabled.append(False)
skill_enabled_vars = [
    tk.BooleanVar(value=saved_skill_enabled[i])
    for i in range(SKILL_LOCATION_COUNT)
]
# UI shows seconds as whole integers; config stores milliseconds.
sit_time_var = tk.IntVar(value=int(float(cfg.get("sit_time_ms", 1000)) / 1000.0))
spam_time_var = tk.IntVar(value=int(float(cfg.get("spam_time_ms", 1000)) / 1000.0))
skill_rotate_time_var = tk.IntVar(value=int(float(cfg.get("skill_rotate_time_ms", 1000)) / 1000.0))
post_wait_var = tk.IntVar(value=int(float(cfg.get("post_spam_wait_ms", 5000)) / 1000.0))
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
DISABLED_BG = "#242424"
START_BG = "#2f5f3a"
STOP_BG = "#6a3333"
PAUSE_BG = "#6a5a2f"
FG = "#e6e6e6"
DISABLED_FG = "#777777"
root.configure(bg=UI_BG)

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass
try:
    style.configure("Dark.TNotebook", background=UI_BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "Dark.TNotebook.Tab",
        background=BTN_BG,
        foreground=FG,
        bordercolor=UI_BG,
        lightcolor=BTN_BG,
        darkcolor=BTN_BG,
        padding=(8, 4),
    )
    style.map(
        "Dark.TNotebook.Tab",
        background=[("selected", ENTRY_BG), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_FG), ("selected", FG)],
    )
except tk.TclError:
    pass

integer_vcmd = (root.register(allow_integer_input), "%P")
integer_entry_options = {"validate": "key", "validatecommand": integer_vcmd}

tk.Label(root, text="Pandora Saga Skill Spam Bot", font=("Segoe UI", 14, "bold"), bg=UI_BG, fg=FG).pack(pady=(12, 6))
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

sit_controls: list[tk.Widget] = []


def update_sit_controls() -> None:
    widget_state = tk.NORMAL if sit_enabled_var.get() else tk.DISABLED
    for widget in sit_controls:
        try:
            widget.configure(state=widget_state)
        except tk.TclError:
            pass
    save_current_config()


sit_box = tk.LabelFrame(coords, text="Sit location", bg=UI_BG, fg=FG)
sit_box.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 8))
sit_content = tk.Frame(sit_box, bg=UI_BG)
sit_content.pack(expand=True, anchor=tk.CENTER, padx=6, pady=6)
tk.Checkbutton(
    sit_content,
    text="Enable sitting phase",
    variable=sit_enabled_var,
    command=update_sit_controls,
    bg=UI_BG,
    fg=FG,
    selectcolor=ENTRY_BG,
    activebackground=UI_BG,
    activeforeground=FG,
    disabledforeground=DISABLED_FG,
    highlightthickness=0,
    bd=0,
).grid(row=0, column=0, columnspan=2, pady=(0, 6))
sit_x_entry = tk.Entry(
    sit_content,
    textvariable=sit_x_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
sit_x_entry.grid(row=1, column=0, padx=6, pady=6)
sit_y_entry = tk.Entry(
    sit_content,
    textvariable=sit_y_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
sit_y_entry.grid(row=1, column=1, padx=6, pady=6)
sit_set_button = tk.Button(
    sit_content,
    text="Set Location",
    command=lambda: capture_point(sit_x_var, sit_y_var, "sit"),
    bg=BTN_BG,
    fg=FG,
    activebackground=BTN_BG,
    disabledforeground=DISABLED_FG,
)
sit_set_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))
sit_duration_row = tk.Frame(sit_content, bg=UI_BG)
sit_duration_row.grid(row=3, column=0, columnspan=2, pady=(2, 0))
tk.Label(sit_duration_row, text="Sit Duration (sec):", bg=UI_BG, fg=FG).pack(side=tk.LEFT, padx=(0, 4))
sit_duration_spinbox = tk.Spinbox(
    sit_duration_row,
    from_=0,
    to=600,
    increment=1,
    textvariable=sit_time_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
sit_duration_spinbox.pack(side=tk.LEFT)
sit_controls.extend([sit_x_entry, sit_y_entry, sit_set_button, sit_duration_spinbox])
update_sit_controls()

skill_box = tk.LabelFrame(coords, text="Skill location", bg=UI_BG, fg=FG)
skill_box.pack(side=tk.LEFT, fill="both", expand=True, padx=(8, 0))
skill_content = tk.Frame(skill_box, bg=UI_BG)
skill_content.pack(expand=True, anchor=tk.CENTER, padx=6, pady=6)
skill_options = tk.Frame(skill_content, bg=UI_BG)
skill_options.pack(anchor=tk.CENTER, pady=(0, 2))

skill_tabs: list[tk.Frame] = []
skill_tab_widgets: list[list[tk.Widget]] = []


def update_skill_tabs() -> None:
    first_enabled_tab = None
    for index, tab in enumerate(skill_tabs):
        tab_state = "normal" if skill_enabled_vars[index].get() else "disabled"
        if tab_state == "normal" and first_enabled_tab is None:
            first_enabled_tab = tab
        skill_notebook.tab(tab, state=tab_state)
        widget_state = tk.NORMAL if tab_state == "normal" else tk.DISABLED
        for widget in skill_tab_widgets[index]:
            try:
                widget.configure(state=widget_state)
            except tk.TclError:
                pass
    selected_tab = skill_notebook.select()
    if selected_tab and skill_notebook.tab(selected_tab, "state") == "disabled" and first_enabled_tab:
        skill_notebook.select(first_enabled_tab)
    save_current_config()


skill_enabled_row = tk.Frame(skill_options, bg=UI_BG)
skill_enabled_row.pack(anchor=tk.CENTER)
tk.Label(skill_enabled_row, text="Enabled:", bg=UI_BG, fg=FG).pack(side=tk.LEFT, padx=(0, 4))
for index, enabled_var in enumerate(skill_enabled_vars):
    tk.Checkbutton(
        skill_enabled_row,
        text=str(index + 1),
        variable=enabled_var,
        command=update_skill_tabs,
        bg=UI_BG,
        fg=FG,
        selectcolor=ENTRY_BG,
        activebackground=UI_BG,
        activeforeground=FG,
        disabledforeground=DISABLED_FG,
        highlightthickness=0,
        bd=0,
    ).pack(side=tk.LEFT, padx=(0, 4))

skill_rotate_row = tk.Frame(skill_options, bg=UI_BG)
skill_rotate_row.pack(anchor=tk.CENTER, pady=(4, 0))
tk.Label(skill_rotate_row, text="Rotate every:", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
tk.Spinbox(
    skill_rotate_row,
    from_=0,
    to=600,
    increment=1,
    textvariable=skill_rotate_time_var,
    width=7,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    **integer_entry_options,
).pack(side=tk.LEFT, padx=(4, 4))
tk.Label(skill_rotate_row, text="sec", bg=UI_BG, fg=FG).pack(side=tk.LEFT)

skill_notebook = ttk.Notebook(skill_content, style="Dark.TNotebook")
skill_notebook.pack(anchor=tk.CENTER, padx=6, pady=(2, 6))

for index, (x_var, y_var) in enumerate(skill_location_vars):
    tab = tk.Frame(skill_notebook, bg=UI_BG)
    skill_tabs.append(tab)
    skill_notebook.add(tab, text=f"Skill {index + 1}")

    tk.Label(tab, text="X:", bg=UI_BG, fg=FG).grid(row=0, column=0, padx=(6, 2), pady=6)
    x_entry = tk.Entry(
        tab,
        textvariable=x_var,
        width=8,
        bg=ENTRY_BG,
        fg=FG,
        insertbackground=FG,
        disabledbackground=DISABLED_BG,
        disabledforeground=DISABLED_FG,
        **integer_entry_options,
    )
    x_entry.grid(row=0, column=1, padx=(0, 6), pady=6)
    tk.Label(tab, text="Y:", bg=UI_BG, fg=FG).grid(row=0, column=2, padx=(6, 2), pady=6)
    y_entry = tk.Entry(
        tab,
        textvariable=y_var,
        width=8,
        bg=ENTRY_BG,
        fg=FG,
        insertbackground=FG,
        disabledbackground=DISABLED_BG,
        disabledforeground=DISABLED_FG,
        **integer_entry_options,
    )
    y_entry.grid(row=0, column=3, padx=(0, 6), pady=6)
    set_button = tk.Button(
        tab,
        text="Set Location",
        command=lambda xv=x_var, yv=y_var, n=index + 1: capture_point(xv, yv, f"skill {n}"),
        bg=BTN_BG,
        fg=FG,
        activebackground=BTN_BG,
        disabledforeground=DISABLED_FG,
    )
    set_button.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6, pady=(0, 6))
    skill_tab_widgets.append([x_entry, y_entry, set_button])

skill_spam_row = tk.Frame(skill_content, bg=UI_BG)
skill_spam_row.pack(anchor=tk.CENTER, pady=(0, 2))
tk.Label(skill_spam_row, text="Spam Duration (sec):", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
tk.Spinbox(
    skill_spam_row,
    from_=0,
    to=600,
    increment=1,
    textvariable=spam_time_var,
    width=7,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    **integer_entry_options,
).pack(side=tk.LEFT, padx=(4, 0))

update_skill_tabs()

logout_controls: list[tk.Widget] = []


def update_logout_controls() -> None:
    widget_state = tk.NORMAL if logout_enabled_var.get() else tk.DISABLED
    for widget in logout_controls:
        try:
            widget.configure(state=widget_state)
        except tk.TclError:
            pass
    save_current_config()


logout_box = tk.LabelFrame(root, text="Logout checker", bg=UI_BG, fg=FG)
logout_box.pack(fill="x", padx=16, pady=(0, 6))
logout_content = tk.Frame(logout_box, bg=UI_BG)
logout_content.pack(anchor=tk.CENTER, padx=6, pady=6)
tk.Checkbutton(
    logout_content,
    text="Enable logout checker",
    variable=logout_enabled_var,
    command=update_logout_controls,
    bg=UI_BG,
    fg=FG,
    selectcolor=ENTRY_BG,
    activebackground=UI_BG,
    activeforeground=FG,
    disabledforeground=DISABLED_FG,
    highlightthickness=0,
    bd=0,
).grid(row=0, column=0, columnspan=6, pady=(0, 6))

logout_connect_section = tk.Frame(logout_content, bg=UI_BG)
logout_connect_section.grid(row=1, column=0, padx=(0, 12), pady=(0, 8))
tk.Label(logout_connect_section, text="Connect Button", bg=UI_BG, fg=FG).grid(row=0, column=0, columnspan=2, pady=(0, 2))
logout_connect_x_entry = tk.Entry(
    logout_connect_section,
    textvariable=logout_connect_x_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
logout_connect_x_entry.grid(row=1, column=0, padx=6, pady=4)
logout_connect_y_entry = tk.Entry(
    logout_connect_section,
    textvariable=logout_connect_y_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
logout_connect_y_entry.grid(row=1, column=1, padx=6, pady=6)
logout_connect_button = tk.Button(
    logout_connect_section,
    text="Set Location",
    command=lambda: capture_point(logout_connect_x_var, logout_connect_y_var, "logout connect"),
    bg=BTN_BG,
    fg=FG,
    activebackground=BTN_BG,
    disabledforeground=DISABLED_FG,
)
logout_connect_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 4))

logout_begin_section = tk.Frame(logout_content, bg=UI_BG)
logout_begin_section.grid(row=1, column=1, padx=(12, 0), pady=(0, 8))
tk.Label(logout_begin_section, text="Begin Button", bg=UI_BG, fg=FG).grid(row=0, column=0, columnspan=2, pady=(0, 2))
logout_begin_x_entry = tk.Entry(
    logout_begin_section,
    textvariable=logout_begin_x_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
logout_begin_x_entry.grid(row=1, column=0, padx=6, pady=4)
logout_begin_y_entry = tk.Entry(
    logout_begin_section,
    textvariable=logout_begin_y_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
logout_begin_y_entry.grid(row=1, column=1, padx=6, pady=6)
logout_begin_button = tk.Button(
    logout_begin_section,
    text="Set Location",
    command=lambda: capture_point(logout_begin_x_var, logout_begin_y_var, "logout begin"),
    bg=BTN_BG,
    fg=FG,
    activebackground=BTN_BG,
    disabledforeground=DISABLED_FG,
)
logout_begin_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 4))

logout_loop_row = tk.Frame(logout_content, bg=UI_BG)
logout_loop_row.grid(row=2, column=0, columnspan=2, pady=(0, 0))
tk.Label(logout_loop_row, text="Loops before checking:", bg=UI_BG, fg=FG).pack(side=tk.LEFT, padx=(0, 4))
logout_loop_spinbox = tk.Spinbox(
    logout_loop_row,
    from_=1,
    to=9999,
    increment=1,
    textvariable=logout_loop_count_var,
    width=8,
    bg=ENTRY_BG,
    fg=FG,
    insertbackground=FG,
    disabledbackground=DISABLED_BG,
    disabledforeground=DISABLED_FG,
    **integer_entry_options,
)
logout_loop_spinbox.pack(side=tk.LEFT)
logout_controls.extend([
    logout_connect_x_entry,
    logout_connect_y_entry,
    logout_connect_button,
    logout_begin_x_entry,
    logout_begin_y_entry,
    logout_begin_button,
    logout_loop_spinbox,
])
update_logout_controls()

timing = tk.Frame(root, bg=UI_BG)
timing.pack(fill="x", padx=16, pady=6)
for label, var in (("Cooldown (sec):", post_wait_var),):
    row = tk.Frame(timing, bg=UI_BG)
    row.pack(fill="x", pady=2)
    tk.Label(row, text=label, width=18, anchor="w", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
    tk.Spinbox(
        row,
        from_=0,
        to=600,
        increment=1,
        textvariable=var,
        width=10,
        bg=ENTRY_BG,
        fg=FG,
        insertbackground=FG,
        **integer_entry_options,
    ).pack(side=tk.LEFT)

hotkey_row = tk.Frame(timing, bg=UI_BG)
hotkey_row.pack(fill="x", pady=(6, 0))
tk.Label(hotkey_row, textvariable=hotkey_label_var, width=18, anchor="w", bg=UI_BG, fg=FG).pack(side=tk.LEFT)
tk.Label(
    hotkey_row,
    textvariable=hotkey_name_var,
    bg=UI_BG,
    fg="#7fd88f",
    font=("Segoe UI", 9, "bold"),
).pack(side=tk.LEFT, padx=(0, 8))
tk.Button(
    hotkey_row,
    text="Set Pause Hotkey",
    width=16,
    command=capture_hotkey,
    bg=BTN_BG,
    fg=FG,
    activebackground=BTN_BG,
).pack(side=tk.LEFT)

controls = tk.Frame(root, bg=UI_BG)
controls.pack(pady=12)
tk.Button(controls, text="Start", width=12, command=start_bot, bg=START_BG, fg=FG, activebackground=START_BG).pack(side=tk.LEFT, padx=6)
tk.Button(controls, text="Stop", width=12, command=stop_bot, bg=STOP_BG, fg=FG, activebackground=STOP_BG).pack(side=tk.LEFT, padx=6)
tk.Button(controls, text="Pause/Resume", width=12, command=pause_resume_bot, bg=PAUSE_BG, fg=FG, activebackground=PAUSE_BG).pack(side=tk.LEFT, padx=6)

tk.Frame(root, height=26, bg=UI_BG).pack(fill="x")

footer = tk.Frame(root, bg=UI_BG)
footer.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-8)
github_link = tk.Label(
    footer,
    text="Github Releases",
    bg=UI_BG,
    fg="#8ab4f8",
    cursor="hand2",
)
github_link.pack(side=tk.RIGHT)
github_link.bind("<Button-1>", open_github_releases)
tk.Label(footer, text="Made by SHVWN (Noize)  |  ver 1.01  | ", bg=UI_BG, fg=DISABLED_FG).pack(side=tk.RIGHT)

update_windows()
refresh_phase()
monitor_hotkey()
root.protocol("WM_DELETE_WINDOW", stop_and_save)
root.mainloop()
