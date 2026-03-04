from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from reservation_service import OverlapError, ReservationService, ValidationError

BUSINESS_OPEN_HOUR = 9
BUSINESS_CLOSE_HOUR = 17
DEFAULT_DURATION_MINUTES = 60

service = ReservationService(open_hour=BUSINESS_OPEN_HOUR, close_hour=BUSINESS_CLOSE_HOUR)


def refresh_list():
    reservation_listbox.delete(0, tk.END)
    reservation_ids.clear()

    for reservation in service.list_reservations():
        line = (
            f'#{reservation.id} | '
            f'{reservation.start_at.strftime("%Y-%m-%d %H:%M")} - '
            f'{reservation.end_at.strftime("%H:%M")} | '
            f'{reservation.customer_name} | '
            f'{reservation.phone or "No phone"}'
        )
        reservation_listbox.insert(tk.END, line)
        reservation_ids.append(reservation.id)


def build_requested_datetime():
    try:
        requested = datetime(
            year=year.get(),
            month=month.get(),
            day=day.get(),
            hour=hour.get(),
            minute=minute.get(),
        )
    except ValueError:
        messagebox.showerror("Invalid Date", "Please enter a real calendar date and time.")
        return None

    return requested


def confirm_reservation():
    customer_name = name.get().strip()
    phone_value = phone.get().strip()
    duration = duration_minutes.get()

    if not customer_name:
        messagebox.showerror("Missing Name", "Please enter a customer name.")
        return

    if duration <= 0:
        messagebox.showerror("Invalid Duration", "Duration must be greater than 0 minutes.")
        return

    start_at = build_requested_datetime()
    if start_at is None:
        return

    try:
        service.validate_request(customer_name, start_at, duration)
    except ValidationError as exc:
        messagebox.showerror("Invalid Reservation", str(exc))
        return

    if service.has_conflict(start_at, duration):
        messagebox.showwarning("Conflict", "That time overlaps with an existing reservation.")
        return

    label = start_at.strftime("%Y-%m-%d %H:%M")
    if not messagebox.askyesno(
        "Confirm Reservation",
        f"Create reservation?\n\nName: {customer_name}\nPhone: {phone_value or 'N/A'}\nTime: {label}\nDuration: {duration} min",
    ):
        return

    try:
        service.create_reservation(customer_name, phone_value, start_at, duration)
    except OverlapError as exc:
        messagebox.showwarning("Conflict", str(exc))
        return

    refresh_list()
    messagebox.showinfo("Confirmed", f"Reservation saved for {label}.")


def cancel_selected():
    selected = reservation_listbox.curselection()
    if not selected:
        messagebox.showwarning("No Selection", "Select a reservation to cancel.")
        return

    index = selected[0]
    reservation_id = reservation_ids[index]
    line = reservation_listbox.get(index)

    if not messagebox.askyesno("Cancel Reservation", f"Cancel this reservation?\n\n{line}"):
        return

    cancelled = service.cancel_reservation(reservation_id)
    if not cancelled:
        messagebox.showerror("Not Found", "Reservation was not found. Refreshing list.")
        refresh_list()
        return

    refresh_list()
    messagebox.showinfo("Cancelled", f"Reservation #{reservation_id} was cancelled.")


# GUI
root = tk.Tk()
root.title("Reservation System")
root.geometry("560x470")
root.resizable(False, False)

now = datetime.now()

name = tk.StringVar()
phone = tk.StringVar()
year = tk.IntVar(value=now.year)
month = tk.IntVar(value=now.month)
day = tk.IntVar(value=now.day)
hour = tk.IntVar(value=max(BUSINESS_OPEN_HOUR, now.hour))
minute = tk.IntVar(value=0)
duration_minutes = tk.IntVar(value=DEFAULT_DURATION_MINUTES)

reservation_ids = []

form = tk.Frame(root, padx=12, pady=10)
form.pack(fill="x")

tk.Label(form, text="Customer Name").grid(row=0, column=0, sticky="w")
tk.Entry(form, textvariable=name, width=26).grid(row=0, column=1, sticky="w", padx=6)

tk.Label(form, text="Phone").grid(row=1, column=0, sticky="w")
tk.Entry(form, textvariable=phone, width=26).grid(row=1, column=1, sticky="w", padx=6)

tk.Label(form, text="Year").grid(row=2, column=0, sticky="w")
tk.Spinbox(form, from_=2024, to=2100, textvariable=year, width=8).grid(row=2, column=1, sticky="w", padx=6)

tk.Label(form, text="Month").grid(row=3, column=0, sticky="w")
tk.Spinbox(form, from_=1, to=12, textvariable=month, width=8).grid(row=3, column=1, sticky="w", padx=6)

tk.Label(form, text="Day").grid(row=4, column=0, sticky="w")
tk.Spinbox(form, from_=1, to=31, textvariable=day, width=8).grid(row=4, column=1, sticky="w", padx=6)

tk.Label(form, text="Hour (24h)").grid(row=5, column=0, sticky="w")
tk.Spinbox(form, from_=0, to=23, textvariable=hour, width=8).grid(row=5, column=1, sticky="w", padx=6)

tk.Label(form, text="Minute").grid(row=6, column=0, sticky="w")
tk.Spinbox(form, values=(0, 15, 30, 45), textvariable=minute, width=8).grid(row=6, column=1, sticky="w", padx=6)

tk.Label(form, text="Duration (min)").grid(row=7, column=0, sticky="w")
tk.Spinbox(form, from_=15, to=480, increment=15, textvariable=duration_minutes, width=8).grid(
    row=7, column=1, sticky="w", padx=6
)

buttons = tk.Frame(root, padx=12, pady=6)
buttons.pack(fill="x")
tk.Button(buttons, text="Confirm Reservation", command=confirm_reservation).pack(side="left")
tk.Button(buttons, text="Refresh List", command=refresh_list).pack(side="left", padx=8)
tk.Button(buttons, text="Cancel Selected", command=cancel_selected).pack(side="left")

tk.Label(root, text="Upcoming Reservations", anchor="w", padx=12).pack(fill="x")
reservation_listbox = tk.Listbox(root, height=12, width=80)
reservation_listbox.pack(padx=12, pady=6, fill="both", expand=True)

note = (
    f"Business hours: {BUSINESS_OPEN_HOUR:02d}:00-{BUSINESS_CLOSE_HOUR:02d}:00 | "
    "Times use local system clock."
)
tk.Label(root, text=note, fg="#555").pack(fill="x", padx=12, pady=6)

refresh_list()
root.mainloop()
