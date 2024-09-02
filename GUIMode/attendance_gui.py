import tkinter as tk
from tkinter import messagebox
import mysql.connector
from datetime import datetime

# Database connection setup
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'yourpassword',
    'database': 'EmployeeTracking'
}

def log_attendance(employee_id, employee_name):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        scan_time = datetime.now()
        query = "INSERT INTO Attendance (employee_id, employee_name, scan_time) VALUES (%s, %s, %s)"
        cursor.execute(query, (employee_id, employee_name, scan_time))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def on_scan():
    badge_input = badge_entry.get()
    if badge_input:
        try:
            employee_id, employee_name = badge_input.split(',')
            if log_attendance(employee_id, employee_name):
                messagebox.showinfo("Success", f"Logged: {employee_name} at {datetime.now()}")
            else:
                messagebox.showerror("Error", "Failed to log attendance.")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid input format. Please use 'employee_id,employee_name'.")
    else:
        messagebox.showwarning("Input Required", "Please enter badge data.")

# GUI setup
root = tk.Tk()
root.title("Employee Attendance Tracker")

tk.Label(root, text="Scan Badge (format: employee_id,employee_name):").pack(pady=10)
badge_entry = tk.Entry(root, width=50)
badge_entry.pack(pady=10)
scan_button = tk.Button(root, text="Log Attendance", command=on_scan)
scan_button.pack(pady=10)

root.mainloop()
