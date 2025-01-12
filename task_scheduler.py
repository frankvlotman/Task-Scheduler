import sys
import time
import subprocess
from tkinter import *
from tkinter import messagebox
from tkinter import ttk  # Import ttk for styling
import json
import os
from PIL import Image

# Constants
ICON_PATH = 'C:\\Users\\Frank\\Desktop\\blank.ico'  # Update this path as needed
TASKS_FILE = os.path.join(os.path.expanduser("~"), "Documents", "tasks.json")
LOG_FILE = os.path.join(os.path.expanduser("~"), "Documents", "app_log.txt")

# Logging Function
def log_message(message):
    """Logs a message with a timestamp to the LOG_FILE."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Logging failed: {e}")

# Create a blank (transparent) ICO file if it doesn't exist
def create_blank_ico(path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    if not os.path.exists(path):
        size = (16, 16)  # Size of the icon
        image = Image.new("RGBA", size, (255, 255, 255, 0))  # Transparent image
        image.save(path, format="ICO")
        log_message(f"Created blank ICO at {path}")
    else:
        log_message(f"ICO already exists at {path}")

create_blank_ico(ICON_PATH)

# Global Variables
tasks_list = []
counter = 1
timer_enabled = False  # Global state variable for the timer
timer_duration_seconds = None  # No default timer duration

# Helper Functions
def inputError():
    """Checks if the task entry field is empty."""
    if enterTaskField.get().strip() == "":
        messagebox.showerror("Input Error", "Please enter a task.")
        return False
    return True

def clear_taskNumberField():
    """Clears the task number field."""
    taskNumberField.delete(1.0, END)

def clear_taskField():
    """Clears the task entry field."""
    enterTaskField.delete(0, END)

def insertTask(event=None):
    """Inserts a new task into the task list and updates the display."""
    global counter
    if not inputError():
        return

    content = enterTaskField.get().strip() + "\n"
    tasks_list.append(content)
    tag = "even" if counter % 2 == 0 else "odd"
    TextArea.insert(END, f"[ {counter} ] {content}", tag)
    log_message(f"Inserted task #{counter}: {content.strip()}")
    counter += 1
    clear_taskField()

def delete(event=None):
    """Deletes a task based on the entered task number."""
    global counter
    if len(tasks_list) == 0:
        messagebox.showerror("No Task", "There are no tasks to delete.")
        return

    try:
        task_no = int(taskNumberField.get(1.0, END).strip())
        if 1 <= task_no <= len(tasks_list):
            removed_task = tasks_list.pop(task_no - 1)
            log_message(f"Deleted task #{task_no}: {removed_task.strip()}")
            counter -= 1
            update_tasks_display()
        else:
            messagebox.showerror("Invalid Task Number", "Please enter a valid task number.")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid task number.")

def clear_all():
    """Clears all tasks from the task list and updates the display."""
    global counter, tasks_list
    tasks_list = []
    counter = 1
    update_tasks_display()
    log_message("Cleared all tasks.")

def save_tasks():
    """Saves the current task list to a JSON file."""
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks_list, f)
        log_message(f"Saved {len(tasks_list)} tasks to {TASKS_FILE}.")
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save tasks: {e}")
        log_message(f"Failed to save tasks: {e}")

def load_tasks():
    """Loads tasks from the JSON file into the task list."""
    global counter
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
                for task in tasks:
                    tasks_list.append(task)
                    tag = "even" if counter % 2 == 0 else "odd"
                    TextArea.insert(END, f"[ {counter} ] {task}", tag)
                    counter += 1
            log_message(f"Loaded {len(tasks_list)} tasks from {TASKS_FILE}.")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load tasks: {e}")
            log_message(f"Failed to load tasks: {e}")
    else:
        log_message(f"No existing tasks file found at {TASKS_FILE}.")

def update_tasks_display():
    """Updates the TextArea to display the current tasks."""
    TextArea.delete(1.0, END)
    for i, task in enumerate(tasks_list, start=1):
        tag = "even" if i % 2 == 0 else "odd"
        TextArea.insert(END, f"[ {i} ] {task}", tag)

def exit_and_restart():
    """Exits the application and, if timer is enabled, starts the timer to restart."""
    save_tasks()
    if timer_enabled:
        duration_seconds = timer_duration_seconds
        
        # Check if duration is set and valid
        if not duration_seconds:
            messagebox.showerror("Timer Error", "Timer duration is not set.")
            log_message("Timer enabled but duration is not set. Exiting without restart.")
            gui.quit()
            sys.exit()

        # Determine creation flags for detached process on Windows
        if os.name == 'nt':
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            creationflags = 0  # No special flags for Unix-based systems

        try:
            # Launch the timer process
            subprocess.Popen(
                [sys.executable, sys.argv[0], '--restart-timer', str(duration_seconds)],
                creationflags=creationflags,
                close_fds=True
            )
            log_message(f"Launched timer process with duration {duration_seconds} seconds.")
        except Exception as e:
            messagebox.showerror("Timer Error", f"Failed to start timer: {e}")
            log_message(f"Failed to start timer: {e}")
    else:
        log_message("Timer not enabled. Exiting without restart.")

    gui.quit()
    sys.exit()

def toggle_timer():
    """Toggles the timer on or off and updates the button color accordingly."""
    global timer_enabled
    
    if timer_duration_seconds is None or timer_duration_seconds <= 0:
        messagebox.showerror("Timer Error", "Please set a valid timer duration before enabling the timer.")
        return

    timer_enabled = not timer_enabled
    toggle_button.config(text="Timer On" if timer_enabled else "Timer Off")
    
    # Update the button style based on the timer state
    if timer_enabled:
        toggle_button.config(style="ToggleOn.TButton")
    else:
        toggle_button.config(style="ToggleOff.TButton")
    
    log_message(f"Timer toggled to {'On' if timer_enabled else 'Off'}.")

def update_timer_duration(event=None):
    """Updates the timer_duration_seconds based on the user's selection."""
    global timer_duration_seconds
    try:
        hours = int(hours_spinbox.get())
        minutes = int(minutes_spinbox.get())
        seconds = int(seconds_spinbox.get())
    except (ValueError, NameError):
        messagebox.showerror("Input Error", "Please enter valid numerical values for hours, minutes, and seconds.")
        log_message("Invalid input in hours, minutes, or seconds Spinbox.")
        # Default to no duration if parsing fails
        timer_duration_seconds = None
        toggle_button.config(state=DISABLED)
        return

    # Calculate total seconds
    timer_duration_seconds = hours * 3600 + minutes * 60 + seconds
    log_message(f"Timer duration set to {hours} hour(s), {minutes} minute(s), and {seconds} second(s) ({timer_duration_seconds} seconds).")

    # Enable the toggle button only if a valid duration is set
    if timer_duration_seconds > 0:
        toggle_button.config(state=NORMAL)
    else:
        toggle_button.config(state=DISABLED)

def set_window_on_top(gui_window):
    """Sets the Tkinter window to appear on top of all other windows."""
    gui_window.attributes("-topmost", True)
    gui_window.lift()
    gui_window.focus_force()
    # Optionally, remove the topmost attribute after a short delay to avoid being intrusive
    gui_window.after(100, lambda: gui_window.attributes("-topmost", False))
    log_message("Window set to topmost temporarily.")

def main_app():
    """Initializes and runs the main Tkinter application."""
    global gui, enterTaskField, TextArea, taskNumberField, toggle_button, hours_spinbox, minutes_spinbox, seconds_spinbox

    gui = Tk()
    gui.title("Frank's To Do List")
    gui.geometry("450x500")  # Increased size for better layout
    gui.configure(bg="#f0f0f0")

    # Make the window appear on top of all other windows
    set_window_on_top(gui)

    # Initialize ttk.Style
    style = ttk.Style()
    style.theme_use("clam")  # Use 'clam' theme for better customization

    # Define custom style for buttons
    style.configure("Custom.TButton",
                    background="#d0e8f1",
                    foreground="black",
                    borderwidth=1,
                    focusthickness=3,
                    focuscolor='none')

    # Define style map for hover (active) state
    style.map("Custom.TButton",
              background=[('active', '#87CEFA')],
              foreground=[('active', 'black')])

    # Define a new style for the Timer button when it's turned on
    style.configure("ToggleOn.TButton",
                    background="#90EE90",  # Light green background when timer is on
                    foreground="black",
                    borderwidth=1,
                    focusthickness=3,
                    focuscolor='none')

    # Define style map for the ToggleOn.TButton's active state
    style.map("ToggleOn.TButton",
              background=[('active', '#76C776')],  # Slightly darker light green when active
              foreground=[('active', 'black')])

    # Define a new style for the Timer button when it's turned off
    style.configure("ToggleOff.TButton",
                    background="#d0e8f1",  # Same as Custom.TButton
                    foreground="black",
                    borderwidth=1,
                    focusthickness=3,
                    focuscolor='none')

    # Define style map for the ToggleOff.TButton's active state
    style.map("ToggleOff.TButton",
              background=[('active', '#87CEFA')],
              foreground=[('active', 'black')])

    # Define widget styles to avoid conflict with ttk.Style
    widget_style = {"background": "#f0f0f0", "foreground": "#333333", "font": ("Arial", 11)}

    # Create widgets
    enterTaskLabel = Label(gui, text="Enter Your Task:", **widget_style)
    enterTaskField = Entry(gui, **widget_style)
    submitButton = ttk.Button(gui, text="Submit", style="Custom.TButton", command=insertTask)
    TextArea = Text(gui, height=10, width=40, bg="white", fg="black", font=("Arial", 11))
    taskNumberLabel = Label(gui, text="Delete Task Number:", **widget_style)
    taskNumberField = Text(gui, height=1, width=5, bg="white", fg="black", font=("Arial", 11))

    # Place widgets using grid layout
    enterTaskLabel.grid(row=0, column=0, pady=(10, 5), padx=10, sticky=W)
    enterTaskField.grid(row=1, column=0, pady=5, padx=10, ipadx=50, sticky=EW)
    submitButton.grid(row=2, column=0, pady=5, padx=10, ipadx=10, sticky=W)
    TextArea.grid(row=3, column=0, pady=10, padx=10, sticky=NSEW)
    taskNumberLabel.grid(row=4, column=0, pady=5, padx=10, sticky=W)
    taskNumberField.grid(row=5, column=0, pady=5, padx=10)

    # Frame for buttons at the bottom
    button_frame = Frame(gui, bg="#f0f0f0")
    button_frame.grid(row=7, column=0, pady=(10, 10), padx=10, sticky=EW)

    # Configure button frame to expand
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)
    button_frame.grid_columnconfigure(2, weight=1)
    button_frame.grid_columnconfigure(3, weight=1)

    # Delete button
    deleteButton = ttk.Button(button_frame, text="Delete", style="Custom.TButton", command=delete)
    deleteButton.grid(row=0, column=0, padx=(0, 5), sticky=EW)

    # Clear All button
    clearAllButton = ttk.Button(button_frame, text="Clear All", style="Custom.TButton", command=clear_all)
    clearAllButton.grid(row=0, column=1, padx=(5, 5), sticky=EW)

    # Exit button
    exitButton = ttk.Button(button_frame, text="Exit", style="Custom.TButton", command=exit_and_restart)
    exitButton.grid(row=0, column=2, padx=(5, 5), sticky=EW)

    # Toggle timer button with initial style set to ToggleOff.TButton and disabled
    toggle_button = ttk.Button(button_frame, text="Timer Off", style="ToggleOff.TButton", command=toggle_timer, state=DISABLED)
    toggle_button.grid(row=0, column=3, padx=(5, 0), sticky=EW)

    # Timer duration input section
    timer_label = Label(gui, text="Set Timer Duration:", **widget_style)
    timer_label.grid(row=6, column=0, pady=5, padx=10, sticky=W)

    # Create a sub-frame for timer inputs (hours, minutes, seconds)
    timer_input_frame = Frame(gui, bg="#f0f0f0")
    timer_input_frame.grid(row=6, column=0, pady=5, padx=10, sticky=W)

    # Hours Spinbox
    hours_label = Label(timer_input_frame, text="Hours:", **widget_style)
    hours_label.grid(row=0, column=0, padx=(0, 2), sticky=E)
    hours_spinbox = Spinbox(timer_input_frame, from_=0, to=23, width=3, font=("Arial", 10), command=lambda: update_timer_duration())
    hours_spinbox.grid(row=0, column=1, padx=(0, 10), sticky=W)
    hours_spinbox.delete(0, END)
    hours_spinbox.insert(0, "0")  # Default value

    # Minutes Spinbox
    minutes_label = Label(timer_input_frame, text="Minutes:", **widget_style)
    minutes_label.grid(row=0, column=2, padx=(0, 2), sticky=E)
    minutes_spinbox = Spinbox(timer_input_frame, from_=0, to=59, width=3, font=("Arial", 10), command=lambda: update_timer_duration())
    minutes_spinbox.grid(row=0, column=3, padx=(0, 10), sticky=W)
    minutes_spinbox.delete(0, END)
    minutes_spinbox.insert(0, "0")  # Default value

    # Seconds Spinbox
    seconds_label = Label(timer_input_frame, text="Seconds:", **widget_style)
    seconds_label.grid(row=0, column=4, padx=(0, 2), sticky=E)
    seconds_spinbox = Spinbox(timer_input_frame, from_=0, to=59, width=3, font=("Arial", 10), command=lambda: update_timer_duration())
    seconds_spinbox.grid(row=0, column=5, padx=(0, 10), sticky=W)
    seconds_spinbox.delete(0, END)
    seconds_spinbox.insert(0, "0")  # Default value

    # Bind Spinboxes to update_timer_duration when their values change
    hours_spinbox.bind("<FocusOut>", update_timer_duration)
    minutes_spinbox.bind("<FocusOut>", update_timer_duration)
    seconds_spinbox.bind("<FocusOut>", update_timer_duration)

    # Apply tags for styling text in TextArea
    TextArea.tag_configure("task", font=("Calibri", 11))
    TextArea.tag_configure("even", background="#f0f0f0")
    TextArea.tag_configure("odd", background="#ffffff")

    # Bind Enter key to functions
    enterTaskField.bind("<Return>", insertTask)
    taskNumberField.bind("<Return>", delete)

    # Configure grid weights for proper resizing
    gui.grid_rowconfigure(3, weight=1)
    gui.grid_columnconfigure(0, weight=1)

    # Load tasks from file
    load_tasks()

    # Set the blank icon to the Tkinter window
    try:
        gui.iconbitmap(ICON_PATH)
        log_message(f"Set window icon to {ICON_PATH}.")
    except Exception as e:
        print(f"Icon not found or invalid format: {e}")
        log_message(f"Failed to set window icon: {e}")

    # Start the GUI main loop
    gui.mainloop()

    # Ensure the application closes properly
    gui.destroy()
    log_message("Application closed.")

def main_timer():
    """Handles the timer functionality when the script is launched with '--restart-timer'."""
    if '--restart-timer' in sys.argv:
        idx = sys.argv.index('--restart-timer')
        if idx + 1 < len(sys.argv):
            try:
                duration = float(sys.argv[idx + 1])
                log_message(f"Timer started for {duration} seconds.")
                time.sleep(duration)
                log_message("Timer elapsed. Restarting the application.")
                # Relaunch the main application
                subprocess.Popen([sys.executable] + [sys.argv[0]],
                                 creationflags=0,
                                 close_fds=True)
                log_message("Main application relaunched.")
            except ValueError:
                log_message("Invalid duration provided for the timer.")
            except Exception as e:
                log_message(f"An error occurred while restarting the application: {e}")
        else:
            log_message("No duration provided for the timer.")
        sys.exit()

# Entry point
if __name__ == "__main__":
    # Check if the script is launched as a timer process
    if '--restart-timer' in sys.argv:
        main_timer()
    else:
        main_app()
