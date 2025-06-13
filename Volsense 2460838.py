import yfinance as yf
import datetime
import os
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import statistics
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import threading
import sys

# === SETTINGS ===
symbol = "QQQ"
save_to_desktop = True
cutoff_date = datetime.date(2024, 5, 29)

# === DATE SELECTOR POPUP ===
selected_date = None

def select_date():
    def on_select():
        global selected_date
        selected_date = cal.selection_get()
        root.destroy()

    root = tk.Tk()
    root.title("Select Date")
    cal = Calendar(root, selectmode='day', year=datetime.datetime.now().year,
                   month=datetime.datetime.now().month, day=datetime.datetime.now().day)
    cal.pack(pady=20)
    tk.Button(root, text="Submit", command=on_select).pack()
    root.mainloop()

select_date()
if not selected_date:
    sys.exit()

# === GET DATA ===
start_date = selected_date - datetime.timedelta(days=45)
data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), progress=False)
data = data.dropna()

if selected_date not in set(data.index.date):
    selected_date = data.index[-1].to_pydatetime().date()
    print("Adjusted selected_date to:", selected_date)

data = data[[d.date() <= selected_date for d in data.index]]
print("Last date in data:", data.index[-1].date(), "| Selected:", selected_date)

# === CALCULATE RAW VOLENSE VALUES ===
recent_data = data.tail(30)
raw_pressures = []

for date, row in recent_data.iterrows():
    volume = float(row['Volume'])
    open_price = float(row['Open'])
    close_price = float(row['Close'])
    buy_pressure = float(volume * (close_price - open_price) / open_price)
    raw_pressures.append(buy_pressure)

pressure_dates = [date.strftime('%m/%d') for date in recent_data.index]
pressure_datetimes = [date.date() for date in recent_data.index]

# === SCALE TO 0–100 RANGE ===
min_pressure = min(raw_pressures)
max_pressure = max(raw_pressures)
volsense = [
    round((p - min_pressure) / (max_pressure - min_pressure) * 100, 2)
    if max_pressure != min_pressure else 50.0 for p in raw_pressures
]

# === UNIVERSAL PREDICTION FUNCTION (momentum only) ===
def generate_prediction(index):
    if index < 2:
        return "gray"
    return "green" if raw_pressures[index-1] > raw_pressures[index-2] else "red"

# === PREDICTIONS ACROSS 30-DAY CHART ===
predicted_colors = []
actual_directions = []
correct_predictions = 0
total_predictions = 0

for i in range(len(raw_pressures)):
    date = pressure_datetimes[i]

    # Actual direction for accuracy tracking
    open_price = float(recent_data.iloc[i]['Open'])
    close_price = float(recent_data.iloc[i]['Close'])
    actual_direction = 'up' if close_price > open_price else 'down' if close_price < open_price else 'flat'
    actual_directions.append(actual_direction)

    if date < cutoff_date:
        predicted_colors.append("gray")
    else:
        prediction = generate_prediction(i)
        predicted_colors.append(prediction)

        total_predictions += 1
        if (prediction == 'green' and actual_direction == 'up') or (prediction == 'red' and actual_direction == 'down'):
            correct_predictions += 1

accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0

# === LAST TWO TRADING DAYS — UNIVERSALIZED ===
last_two = recent_data.tail(2)
if len(last_two) < 2:
    print("Not enough trading days.")
    sys.exit()

def to_julian_date(dt):
    return int(dt.toordinal() + 1721424.5)

dt_1 = last_two.index[0].to_pydatetime()
dt_2 = last_two.index[1].to_pydatetime()
date_1_label = f"{dt_1.strftime('%b %d, %Y')} (Julian {to_julian_date(dt_1)})"
date_2_label = f"{dt_2.strftime('%b %d, %Y')} (Julian {to_julian_date(dt_2)})"

# === RAW VOLSENSE FOR PREDICTION ===
pressures = []
for _, row in last_two.iterrows():
    volume = float(row['Volume'])
    open_price = float(row['Open'])
    close_price = float(row['Close'])
    buy_pressure = float(volume * (close_price - open_price) / open_price)
    pressures.append(buy_pressure)

pressure_1, pressure_2 = pressures

# === UNIVERSALIZED POPUP PREDICTION ===
index_of_last = len(raw_pressures) - 1
popup_prediction = generate_prediction(index_of_last)

if popup_prediction == "green":
    short_result = "BULLISH"
    color = "green"
elif popup_prediction == "red":
    short_result = "BEARISH"
    color = "red"
else:
    short_result = "NO PREDICTION"
    color = "gray"

mean_scaled = statistics.mean(volsense)

# === SCALE LAST TWO PRESSURES FOR DISPLAY ===
scaled_1 = round((pressure_1 - min_pressure) / (max_pressure - min_pressure) * 100, 2) if max_pressure != min_pressure else 50.0
scaled_2 = round((pressure_2 - min_pressure) / (max_pressure - min_pressure) * 100, 2) if max_pressure != min_pressure else 50.0

# === EXIT HANDLER ===
def on_exit():
    plt.close('all')
    os._exit(0)

# === POP-UP WINDOW ===
def show_popup():
    window = tk.Tk()
    window.title("QQQ Volsense Prediction")
    window.geometry("550x350")
    window.protocol("WM_DELETE_WINDOW", on_exit)
    label = tk.Label(window, text=short_result, font=("Helvetica", 48), fg=color)
    label.pack(pady=10)
    pressure_label = tk.Label(
        window,
        text=f"{date_2_label}\nScaled Volsense: {scaled_2:.2f}/100\n\n"
             f"{date_1_label}\nScaled Volsense: {scaled_1:.2f}/100\n\n"
             f"Avg (30d): {mean_scaled:.2f}\n"
             f"Prediction Accuracy (since 5/29): {accuracy:.2f}%",
        font=("Helvetica", 12)
    )
    pressure_label.pack()
    window.mainloop()

# === SHOW CHART ===
def show_chart():
    def on_close(event):
        on_exit()

    fig = plt.figure(figsize=(10, 4))
    plt.scatter(pressure_dates, volsense, c=predicted_colors, s=60, label="Volsense Prediction")
    plt.plot(pressure_dates, volsense, linestyle='-', color='blue', alpha=0.3)
    plt.axhline(50, color='gray', linestyle='--', linewidth=1, label="Midpoint")
    plt.axhspan(0, 39, facecolor='red', alpha=0.1, label="Bearish Zone (0–39)")
    plt.axhspan(40, 60, facecolor='yellow', alpha=0.1, label="Neutral Zone (40–60)")
    plt.axhspan(61, 100, facecolor='green', alpha=0.1, label="Bullish Zone (61–100)")

    for i, date in enumerate(recent_data.index):
        open_price = float(recent_data.loc[date, 'Open'])
        close_price = float(recent_data.loc[date, 'Close'])
        delta = round(close_price - open_price, 2)
        label = f"{'+' if delta >= 0 else ''}{delta:.2f}"
        plt.text(
            x=i,
            y=volsense[i] + 2,
            s=label,
            fontsize=8,
            ha='center',
            va='bottom',
            color=predicted_colors[i]
        )

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Predicted Bullish (green dot)', markerfacecolor='green', markersize=8),
        Line2D([0], [0], marker='o', color='w', label='Predicted Bearish (red dot)', markerfacecolor='red', markersize=8),
        Line2D([0], [0], marker='o', color='w', label='No Prediction (gray dot)', markerfacecolor='gray', markersize=8),
        Line2D([0], [0], color='blue', lw=1, label='Volsense Trend'),
        Line2D([0], [0], color='w', label='+X = Gain'),
        Line2D([0], [0], color='w', label='-X = Loss'),
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=10)

    plt.xticks(rotation=60)
    plt.ylim(0, 100)
    plt.title(f"{symbol} Volsense (Last 30 Trading Days)")
    plt.xlabel("Date")
    plt.ylabel("Volsense Score")
    plt.tight_layout()
    fig.canvas.mpl_connect("close_event", on_close)
    plt.show()

# === RUN ===
threading.Thread(target=show_popup, daemon=True).start()
show_chart()
