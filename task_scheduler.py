from tkinter import *
from tkinter import messagebox
from tkinter import ttk  # Import ttk for the dropdown menu
import json
import os
import threading
import subprocess
import sys
import time  # Import the time module

TASKS_FILE = os.path.join(os.path.expanduser("~"), "Documents", "tasks.json")

tasks_list = []
counter = 1
timer_enabled = False  # Global state variable for the timer
timer_duration = 1  # Default timer duration (1 hour)

def inputError():
    if enterTaskField.get().strip() == "":
        messagebox.showerror("Input Error", "Please enter a task.")
        return False
    return True

def clear_taskNumberField():
    taskNumberField.delete(1.0, END)

def clear_taskField():
    enterTaskField.delete(0, END)

def insertTask(event=None):
    global counter
    if not inputError():
        return

    content = enterTaskField.get().strip() + "\n"
    tasks_list.append(content)
    tag = "even" if counter % 2 == 0 else "odd"
    TextArea.insert(END, f"[ {counter} ] {content}", tag)
    counter += 1
    clear_taskField()

def delete(event=None):
    global counter
    if len(tasks_list) == 0:
        messagebox.showerror("No Task", "There are no tasks to delete.")
        return

    try:
        task_no = int(taskNumberField.get(1.0, END).strip())
        if 1 <= task_no <= len(tasks_list):
            tasks_list.pop(task_no - 1)
            counter -= 1
            update_tasks_display()
        else:
            messagebox.showerror("Invalid Task Number", "Please enter a valid task number.")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid task number.")

def clear_all():
    global counter, tasks_list
    tasks_list = []
    counter = 1
    update_tasks_display()

def save_tasks():
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks_list, f)

def load_tasks():
    global counter
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r') as f:
            tasks = json.load(f)
            for task in tasks:
                tasks_list.append(task)
                tag = "even" if counter % 2 == 0 else "odd"
                TextArea.insert(END, f"[ {counter} ] {task}", tag)
                counter += 1

def update_tasks_display():
    TextArea.delete(1.0, END)
    for i, task in enumerate(tasks_list, start=1):
        tag = "even" if i % 2 == 0 else "odd"
        TextArea.insert(END, f"[ {i} ] {task}", tag)

def restart_script():
    time.sleep(timer_duration * 3600)  # Delay for the selected number of hours
    subprocess.Popen([sys.executable] + sys.argv)

def exit_and_restart():
    save_tasks()
    if timer_enabled:
        threading.Thread(target=restart_script).start()
    gui.quit()  # Use quit() instead of destroy()

def toggle_timer():
    global timer_enabled
    timer_enabled = not timer_enabled
    toggle_button.config(text="Timer On" if timer_enabled else "Timer Off")

def update_timer_duration(event):
    global timer_duration
    selection = timer_dropdown.get().split()[0]
    if selection == "5":
        timer_duration = 5 / 3600  # Set timer duration to 5 seconds
    else:
        timer_duration = int(selection)  # Extract the number of hours from the selection

if __name__ == "__main__":
    gui = Tk()
    gui.title("My To Do List")
    gui.geometry("350x450")  # Increased vertical size
    gui.configure(bg="#f0f0f0")

    # Set column weight to ensure the layout expands correctly
    gui.grid_columnconfigure(0, weight=1)

    # Define styles
    style = {"background": "#f0f0f0", "foreground": "#333333", "font": ("Arial", 11)}

    # Create widgets
    enterTaskLabel = Label(gui, text="Enter Your Task:", **style)
    enterTaskField = Entry(gui, **style)
    submitButton = Button(gui, text="Submit", bg="#d0e8f1", fg="black", command=insertTask)
    TextArea = Text(gui, height=10, width=30, **style)
    taskNumberLabel = Label(gui, text="Delete Task Number:", **style)
    taskNumberField = Text(gui, height=1, width=5, **style)

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
    deleteButton = Button(button_frame, text="Delete", bg="#d0e8f1", fg="black", command=delete)
    deleteButton.grid(row=0, column=0, padx=(0, 10), sticky=EW)

    # Clear All button
    clearAllButton = Button(button_frame, text="Clear All", bg="#d0e8f1", fg="black", command=clear_all)
    clearAllButton.grid(row=0, column=1, padx=(0, 10), sticky=EW)

    # Exit button
    exitButton = Button(button_frame, text="Exit", bg="#d0e8f1", fg="black", command=exit_and_restart)
    exitButton.grid(row=0, column=2, padx=(0, 10), sticky=EW)

    # Toggle timer button
    toggle_button = Button(button_frame, text="Timer Off", bg="#d0e8f1", fg="black", command=toggle_timer)
    toggle_button.grid(row=0, column=3, sticky=EW)

    # Timer duration dropdown
    timer_label = Label(gui, text="Select Timer Duration:", **style)
    timer_label.grid(row=6, column=0, pady=5, padx=10, sticky=W)

    timer_options = ["1 hour", "2 hours", "3 hours", "4 hours", "5 hours", "6 hours", "5 seconds"]
    timer_dropdown = ttk.Combobox(gui, values=timer_options, state="readonly", width=12)
    timer_dropdown.current(0)  # Set default selection to 1 hour
    timer_dropdown.grid(row=6, column=0, pady=5, padx=(180, 0), sticky=W)
    timer_dropdown.bind("<<ComboboxSelected>>", update_timer_duration)

    # Apply tags for styling text in TextArea
    TextArea.tag_configure("task", font=("Calibri", 11))
    TextArea.tag_configure("even", background="#f0f0f0")
    TextArea.tag_configure("odd", background="#ffffff")

    # Bind Enter key to functions
    enterTaskField.bind("<Return>", insertTask)
    taskNumberField.bind("<Return>", delete)

    # Load tasks from file
    load_tasks()

    # Start the GUI main loop
    gui.mainloop()

    # Ensure the application closes properly
    gui.destroy()
