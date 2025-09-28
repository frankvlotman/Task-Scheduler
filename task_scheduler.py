
import sys
import time
import subprocess
import os
import signal
import json
from tkinter import *
from tkinter import messagebox, ttk
from tkinter import font as tkfont
from PIL import Image
from datetime import datetime, timedelta

# ─── Constants ────────────────────────────────────────────────────────────────
ICON_PATH   = r'C:\Users\Frank\Desktop\blank.ico'
TASKS_FILE  = os.path.join(os.path.expanduser("~"), "Documents", "tasks.json")
STATE_FILE  = os.path.join(os.path.expanduser("~"), "Documents", "timer_state.json")
LOG_FILE    = os.path.join(os.path.expanduser("~"), "Documents", "app_log.txt")
LOCK_FILE   = os.path.join(os.path.expanduser("~"), "Documents", "app.lock")

# ─── Globals ─────────────────────────────────────────────────────────────────
tasks_list             = []
counter                = 1
timer_enabled          = False
timer_duration_seconds = 0
countdown_job          = None
countdown_label        = None
sleeper_pid            = None

# GUI globals
gui = None
enterTaskField = None
TextArea = None
taskNumberField = None
clock_label = None

# Timer dialog globals
timer_window = None
mode_var = None           # "duration" | "specific"
h_var = m_var = s_var = None
at_h_var = at_m_var = None
target_hint_label_dlg = None
start_btn_dlg = None
stop_btn_dlg = None

# ─── Logging ─────────────────────────────────────────────────────────────────
def log_message(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

# ─── Single-instance lock ─────────────────────────────────────────────────────
def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            old = json.load(open(LOCK_FILE))["pid"]
            os.kill(old, 0)  # raises if not running
            sys.exit()       # another GUI is running
        except:
            try: os.remove(LOCK_FILE)
            except: pass
    try:
        json.dump({"pid": os.getpid()}, open(LOCK_FILE, 'w'))
    except:
        pass

def remove_lock():
    try: os.remove(LOCK_FILE)
    except: pass

# ─── Ensure blank ICO ────────────────────────────────────────────────────────
def create_blank_ico(path):
    d = os.path.dirname(path)
    try: os.makedirs(d, exist_ok=True)
    except: pass
    if not os.path.isfile(path):
        try:
            img = Image.new("RGBA", (16,16), (255,255,255,0))
            img.save(path, format="ICO")
            log_message(f"Created blank ICO at {path}")
        except: pass

create_blank_ico(ICON_PATH)

# ─── Task Helpers ────────────────────────────────────────────────────────────
def inputError():
    if not enterTaskField.get().strip():
        messagebox.showerror("Input Error","Please enter a task.")
        return False
    return True

def clear_taskField():
    enterTaskField.delete(0, END)

def insertTask(event=None):
    global counter
    if not inputError(): return
    t = enterTaskField.get().strip() + "\n"
    tasks_list.append(t)
    tag = "even" if counter % 2 == 0 else "odd"
    TextArea.insert(END, f"[ {counter} ] {t}", tag)
    log_message(f"Inserted task #{counter}: {t.strip()}")
    counter += 1
    clear_taskField()

def deleteTask(event=None):
    global counter
    if not tasks_list:
        messagebox.showerror("No Task","Nothing to delete.")
        return
    try:
        n = int(taskNumberField.get(1.0, END).strip())
    except:
        messagebox.showerror("Invalid Input","Enter valid task number.")
        return
    if 1 <= n <= len(tasks_list):
        rem = tasks_list.pop(n-1)
        log_message(f"Deleted task #{n}: {rem.strip()}")
        counter -= 1
        refreshTasks()
    else:
        messagebox.showerror("Invalid Task Number","That number is out of range.")

def clear_all():
    global tasks_list, counter
    tasks_list.clear()
    counter = 1
    refreshTasks()
    log_message("Cleared all tasks.")

def refreshTasks():
    TextArea.delete(1.0, END)
    for i, t in enumerate(tasks_list, 1):
        tag = "even" if i % 2 == 0 else "odd"
        TextArea.insert(END, f"[ {i} ] {t}", tag)

def save_tasks():
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks_list, f)
        log_message(f"Saved {len(tasks_list)} tasks.")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def load_tasks():
    global counter
    if os.path.isfile(TASKS_FILE):
        try:
            with open(TASKS_FILE) as f:
                loaded = json.load(f)
            for t in loaded:
                tasks_list.append(t)
                tag = "even" if counter % 2 == 0 else "odd"
                TextArea.insert(END, f"[ {counter} ] {t}", tag)
                counter += 1
            log_message(f"Loaded {len(tasks_list)} tasks.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

# ─── Timer Core Helpers ──────────────────────────────────────────────────────
def _to_int(val, lo, hi, fallback):
    try:
        x = int(str(val).strip())
    except:
        x = fallback
    return max(lo, min(hi, x))

def _compute_delay_to_target(hh:int, mm:int) -> int:
    """Seconds until next occurrence of HH:MM local time (today or tomorrow)."""
    now = datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(0, int(round((target - now).total_seconds())))

def _format_delta(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h}h {m}m {s}s"

def _current_seconds_from_dialog() -> int:
    """Recalculate seconds based on dialog mode and inputs."""
    if timer_window is None or not (mode_var and h_var and m_var and s_var and at_h_var and at_m_var):
        return 0
    if mode_var.get() == "specific":
        th = _to_int(at_h_var.get(), 0, 23, datetime.now().hour)
        tm = _to_int(at_m_var.get(), 0, 59, (datetime.now().minute + 1) % 60)
        secs = _compute_delay_to_target(th, tm)
        log_message(f"[MODE specific] {th:02d}:{tm:02d} -> {secs}s")
        if target_hint_label_dlg:
            now = datetime.now(); target = now + timedelta(seconds=secs)
            when = "today" if target.date() == now.date() else "tomorrow"
            target_hint_label_dlg.config(
                text=f"Target: {target.strftime('%Y-%m-%d %H:%M:%S')} ({when}) • Δ { _format_delta(secs) }"
            )
        return secs
    else:
        h = _to_int(h_var.get(), 0, 23, 0)
        m = _to_int(m_var.get(), 0, 59, 0)
        s = _to_int(s_var.get(), 0, 59, 0)
        secs = h * 3600 + m * 60 + s
        log_message(f"[MODE duration] {h}h{m}m{s}s -> {secs}s")
        if target_hint_label_dlg:
            now = datetime.now(); target = now + timedelta(seconds=secs)
            target_hint_label_dlg.config(
                text=f"Target: {target.strftime('%Y-%m-%d %H:%M:%S')} • Δ { _format_delta(secs) }" if secs>0 else ""
            )
        return secs

def _update_dialog_enables(*_args):
    secs = _current_seconds_from_dialog()
    if start_btn_dlg:
        start_btn_dlg.config(state=NORMAL if secs > 0 else DISABLED)
    if stop_btn_dlg:
        stop_btn_dlg.config(state=NORMAL if timer_enabled else DISABLED)

def _relaunch_now():
    """Launch a fresh instance and close this one (used at countdown zero)."""
    try:
        save_tasks()
    except:
        pass
    global sleeper_pid
    if sleeper_pid:
        try:
            if os.name == 'nt':
                subprocess.call(['taskkill','/PID', str(sleeper_pid), '/F'])
            else:
                os.kill(sleeper_pid, signal.SIGTERM)
            log_message(f"Killed sleeper {sleeper_pid} before relaunch.")
        except:
            pass
        sleeper_pid = None

    # Remove lock so the new instance isn't blocked
    remove_lock()
    flags = (0x00000008 | 0x00000200) if os.name=='nt' else 0
    try:
        subprocess.Popen([sys.executable, sys.argv[0]], creationflags=flags, close_fds=True)
        log_message("Relaunched a fresh GUI from countdown.")
    except Exception as e:
        log_message(f"Relaunch failed: {e}")

    try: gui.quit()
    except: pass
    sys.exit()

def start_countdown(sec):
    """Counts down; when it reaches zero, relaunch immediately."""
    global countdown_job
    if not timer_enabled:
        countdown_label.config(text="")
        return

    if sec <= 0:
        countdown_label.config(text="Relaunching…")
        _relaunch_now()
        return

    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    countdown_label.config(text=f"Restart in {h:02d}:{m:02d}:{s:02d}")
    countdown_job = gui.after(1000, lambda: start_countdown(sec - 1))

def start_timer_from_dialog():
    """Compute seconds from dialog, enable timer, and begin countdown."""
    global timer_enabled, timer_duration_seconds, countdown_job
    secs = _current_seconds_from_dialog()
    if secs <= 0:
        messagebox.showerror("Timer Error", "Set a valid duration or time first.")
        return

    timer_duration_seconds = secs
    timer_enabled = True
    if countdown_job:
        gui.after_cancel(countdown_job)
    start_countdown(timer_duration_seconds)
    log_message(f"Timer started for {secs}s.")
    _update_dialog_enables()

def stop_timer():
    """Stop the current timer and clear countdown."""
    global timer_enabled, countdown_job
    timer_enabled = False
    if countdown_job:
        gui.after_cancel(countdown_job)
        countdown_job = None
    countdown_label.config(text="")
    log_message("Timer stopped.")
    _update_dialog_enables()

# ─── Exit + Sleep-then-Relaunch (existing behavior preserved) ────────────────
def exit_and_restart():
    global sleeper_pid
    save_tasks()

    if timer_enabled and timer_duration_seconds > 0:
        end_ts = time.time() + timer_duration_seconds

        if sleeper_pid:
            try:
                os.kill(sleeper_pid, 0)
                if os.name=='nt':
                    subprocess.call(['taskkill','/PID', str(sleeper_pid), '/F'])
                else:
                    os.kill(sleeper_pid, signal.SIGTERM)
            except:
                pass

        flags = (0x00000008 | 0x00000200) if os.name=='nt' else 0
        proc = subprocess.Popen(
            [sys.executable, sys.argv[0], '--restart-timer', str(timer_duration_seconds)],
            creationflags=flags, close_fds=True
        )
        sleeper_pid = proc.pid
        log_message(f"Spawned sleeper {sleeper_pid} for {timer_duration_seconds}s")

        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({"end_ts": end_ts, "sleeper_pid": sleeper_pid}, f)
        except:
            pass
    else:
        log_message("Exiting without restart.")
        try: os.remove(STATE_FILE)
        except: pass

    remove_lock()
    try: gui.quit()
    except: pass
    sys.exit()

def main_timer():
    idx = sys.argv.index('--restart-timer')
    if idx + 1 < len(sys.argv):
        dur = float(sys.argv[idx + 1])
        log_message(f"Sleeper sleeping {dur}s …")
        time.sleep(dur)
        subprocess.Popen(
            [sys.executable, sys.argv[0]],
            creationflags=(0x00000008 | 0x00000200) if os.name=='nt' else 0,
            close_fds=True
        )
        log_message("Sleeper launched new GUI.")
    sys.exit()

# ─── Timer Dialog ────────────────────────────────────────────────────────────
def open_timer_dialog():
    global timer_window, mode_var, h_var, m_var, s_var, at_h_var, at_m_var
    global target_hint_label_dlg, start_btn_dlg, stop_btn_dlg

    if timer_window is not None and timer_window.winfo_exists():
        timer_window.deiconify()
        timer_window.lift()
        timer_window.focus_force()
        return

    timer_window = Toplevel(gui)
    timer_window.title("Timer")
    timer_window.configure(bg="#f0f0f0")
    timer_window.resizable(False, False)
    timer_window.transient(gui)
    timer_window.grab_set()  # modal-ish
    try:
        timer_window.iconbitmap(ICON_PATH)
    except:
        pass

    ws = {"background":"#f0f0f0","foreground":"#333","font":("Arial",11)}

    # Mode selector
    Label(timer_window, text="Timer Mode:", **ws).grid(row=0, column=0, padx=10, pady=(10,4), sticky=W)
    mode_frame = Frame(timer_window, bg="#f0f0f0")
    mode_frame.grid(row=1, column=0, padx=10, pady=(0,6), sticky=W)
    mode_var = StringVar(value="duration")
    ttk.Radiobutton(mode_frame, text="Duration (H:M:S)", value="duration", variable=mode_var, command=_update_dialog_enables).pack(side=LEFT, padx=(0,10))
    ttk.Radiobutton(mode_frame, text="Specific time (HH:MM)", value="specific", variable=mode_var, command=_update_dialog_enables).pack(side=LEFT)

    # Duration controls
    dframe = Frame(timer_window, bg="#f0f0f0")
    dframe.grid(row=2, column=0, padx=10, pady=(0,6), sticky=E)
    Label(dframe, text="H:", **ws).grid(row=0, column=0, sticky=E)
    h_var = StringVar(value="0")
    Spinbox(dframe, from_=0, to=23, width=3, textvariable=h_var, command=_update_dialog_enables).grid(row=0, column=1, padx=5)
    Label(dframe, text="M:", **ws).grid(row=0, column=2, sticky=E)
    m_var = StringVar(value="0")
    Spinbox(dframe, from_=0, to=59, width=3, textvariable=m_var, command=_update_dialog_enables).grid(row=0, column=3, padx=5)
    Label(dframe, text="S:", **ws).grid(row=0, column=4, sticky=E)
    s_var = StringVar(value="0")
    Spinbox(dframe, from_=0, to=59, width=3, textvariable=s_var, command=_update_dialog_enables).grid(row=0, column=5, padx=5)

    # Specific time controls
    sframe = Frame(timer_window, bg="#f0f0f0")
    sframe.grid(row=3, column=0, padx=10, pady=(0,6), sticky=E)
    Label(sframe, text="HH:", **ws).grid(row=0, column=0, sticky=E)
    at_h_var = StringVar(value=datetime.now().strftime("%H"))
    Spinbox(sframe, from_=0, to=23, width=3, textvariable=at_h_var, command=_update_dialog_enables).grid(row=0, column=1, padx=5)
    Label(sframe, text="MM:", **ws).grid(row=0, column=2, sticky=E)
    at_m_var = StringVar(value=f"{(datetime.now().minute + 1) % 60:02d}")
    Spinbox(sframe, from_=0, to=59, width=3, textvariable=at_m_var, command=_update_dialog_enables).grid(row=0, column=3, padx=5)

    # Trace so typing immediately recomputes
    for v in (h_var, m_var, s_var, at_h_var, at_m_var, mode_var):
        v.trace_add("write", lambda *_: _update_dialog_enables())

    # Target hint
    target_hint_label_dlg = Label(timer_window, text="", **ws)
    target_hint_label_dlg.grid(row=4, column=0, padx=10, pady=(0,6), sticky=W)

    # Buttons (colored styles applied below in main_app style section)
    bf = Frame(timer_window, bg="#f0f0f0")
    bf.grid(row=5, column=0, padx=10, pady=10, sticky=EW)
    for i in range(3):
        bf.grid_columnconfigure(i, weight=1)
    start_btn_dlg = ttk.Button(bf, text="Start", command=start_timer_from_dialog, style="Start.TButton", state=DISABLED)
    start_btn_dlg.grid(row=0, column=0, padx=5, sticky=EW)
    stop_btn_dlg = ttk.Button(bf, text="Stop", command=stop_timer, style="Stop.TButton", state=DISABLED)
    stop_btn_dlg.grid(row=0, column=1, padx=5, sticky=EW)
    ttk.Button(bf, text="Close", command=timer_window.destroy).grid(row=0, column=2, padx=5, sticky=EW)

    # Initialize
    _update_dialog_enables()
    timer_window.bind("<Escape>", lambda e: timer_window.destroy())

# ─── Font Helpers ────────────────────────────────────────────────────────────
def _choose_digital_font(root):
    """Pick a digital/7-segment-style font if installed; fallback to monospace.
    Returns a tkfont.Font instance with a small size for minimal height.
    """
    try:
        available = set(f.lower() for f in tkfont.families(root))
    except:
        available = set()

    candidates = [
        # Popular seven-segment / digital fonts users often install
        "DS-Digital", "Digital-7", "DSEG7 Classic", "DSEG7 Classic Regular",
        "DSEG7 Classic Mini", "Seven Segment", "Segment7", "LCD", "Quartz MS",
        # Clean tech-ish fonts as secondary options
        "Orbitron", "Oxanium", "Rajdhani",
        # Monospace fallbacks (present on most systems)
        "Consolas", "Courier New", "Lucida Console"
    ]

    chosen = None
    for name in candidates:
        if name.lower() in available:
            chosen = name
            break
    if chosen is None:
        # As a last resort, Tk default monospace
        chosen = "Courier New"

    # Smaller profile: 10pt looks neat; tweak here if you want even smaller
    return tkfont.Font(root=root, family=chosen, size=10, weight="normal")

# ─── Main GUI ────────────────────────────────────────────────────────────────
def main_app():
    global gui, enterTaskField, TextArea, taskNumberField
    global countdown_label, clock_label
    global timer_enabled, timer_duration_seconds, sleeper_pid

    acquire_lock()

    # restore timer state & existing sleeper if present
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                st = json.load(f)
            rem = int(st.get("end_ts", 0) - time.time())
            if rem > 0:
                timer_enabled = True
                timer_duration_seconds = rem
                pid = st.get("sleeper_pid")
                if pid:
                    try:
                        os.kill(pid, 0)
                        sleeper_pid = pid
                    except:
                        pass
            else:
                os.remove(STATE_FILE)
        except:
            pass

    gui = Tk()
    gui.title("To Do List")
    gui.geometry("480x660")
    gui.configure(bg="#f0f0f0")
    gui.protocol("WM_DELETE_WINDOW", exit_and_restart)

    # bring to front briefly
    gui.attributes("-topmost", True)
    gui.after(100, lambda: gui.attributes("-topmost", False))

    # styles
    style = ttk.Style(); style.theme_use("clam")
    style.configure("Custom.TButton", background="#d0e8f1")
    style.map("Custom.TButton", background=[('active','#87CEFA')])

    # ---- Colored button styles for Timer dialog ----
    style.configure("Start.TButton", background="#90EE90", foreground="#000000")
    style.map("Start.TButton",
              background=[('active', '#76C776'), ('disabled', '#dfeee0')])

    style.configure("Stop.TButton", background="#F08080", foreground="#000000")
    style.map("Stop.TButton",
              background=[('active', '#e86464'), ('disabled', '#f0c0c0')])

    ws = {"background":"#f0f0f0","foreground":"#333","font":("Arial",11)}
    ws_small = {**ws, "font": ("Arial", 9)}  # smaller font variant

    # ── Top bar with live clock (small digital font) ──
    topbar = Frame(gui, bg="#f0f0f0")
    topbar.grid(row=0, column=0, sticky=EW, padx=10, pady=(4,0))  # smaller vertical padding
    Label(topbar, text="", **ws_small).pack(side=LEFT)  # clock title here (empty)

    digital_font = _choose_digital_font(gui)
    global clock_label
    clock_label = Label(topbar, text="--:--:--", bg="#f0f0f0", fg="#222", font=digital_font)
    clock_label.pack(side=LEFT, padx=(6,0))

    def _tick_clock():
        try:
            now = datetime.now().strftime("%H:%M:%S")
            clock_label.config(text=now)
        finally:
            gui.after(1000, _tick_clock)
    _tick_clock()

    # task entry
    Label(gui, text="Enter Your Task:", **ws).grid(row=1, column=0, padx=10, pady=(10,5), sticky=W)
    global enterTaskField
    enterTaskField = Entry(gui, **ws)
    enterTaskField.grid(row=2, column=0, padx=10, pady=5, ipadx=50, sticky=EW)
    ttk.Button(gui, text="Submit", style="Custom.TButton", command=insertTask)\
        .grid(row=3, column=0, padx=10, pady=5, sticky=W)

    # task display
    global TextArea
    TextArea = Text(gui, height=10, width=40, bg="white", fg="black", font=("Arial",11))
    TextArea.grid(row=4, column=0, padx=10, pady=10, sticky=NSEW)

    # delete
    Label(gui, text="Delete Task Number:", **ws).grid(row=5, column=0, padx=10, pady=5, sticky=W)
    global taskNumberField
    taskNumberField = Text(gui, height=1, width=5, bg="white", fg="black", font=("Arial",11))
    taskNumberField.grid(row=6, column=0, padx=10, pady=5, sticky=W)

    # countdown label (stays in the main window for minimalist status)
    global countdown_label
    countdown_label = Label(gui, text="", **ws)
    countdown_label.grid(row=8, column=0, padx=10, pady=(5,10), sticky=W)

    # buttons (minimalist: Timer button opens dialog)
    bf = Frame(gui, bg="#f0f0f0"); bf.grid(row=7, column=0, padx=10, pady=10, sticky=EW)
    for i in range(4):
        bf.grid_columnconfigure(i, weight=1)
    ttk.Button(bf, text="Delete", style="Custom.TButton", command=deleteTask).grid(row=0, column=0, padx=5, sticky=EW)
    ttk.Button(bf, text="Clear All", style="Custom.TButton", command=clear_all).grid(row=0, column=1, padx=5, sticky=EW)
    ttk.Button(bf, text="Exit", style="Custom.TButton", command=exit_and_restart).grid(row=0, column=2, padx=5, sticky=EW)
    ttk.Button(bf, text="Timer", style="Custom.TButton", command=open_timer_dialog).grid(row=0, column=3, padx=5, sticky=EW)

    # styling & bindings
    TextArea.tag_configure("even", background="#f0f0f0")
    TextArea.tag_configure("odd", background="#ffffff")
    enterTaskField.bind("<Return>", insertTask)
    taskNumberField.bind("<Return>", deleteTask)

    gui.grid_rowconfigure(4, weight=1)
    gui.grid_columnconfigure(0, weight=1)

    load_tasks()
    try:
        gui.iconbitmap(ICON_PATH)
    except:
        pass

    # if we restored an active timer, start countdown immediately
    if timer_enabled and timer_duration_seconds > 0:
        start_countdown(timer_duration_seconds)

    gui.mainloop()
    try: gui.destroy()
    except: pass
    remove_lock()
    log_message("App closed.")

if __name__ == "__main__":
    if '--restart-timer' in sys.argv:
        main_timer()
    else:
        main_app()
