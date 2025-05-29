import yfinance as yf
import datetime
import os
import tkinter as tk
import statistics
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for GUI
import matplotlib.pyplot as plt
import sys

# === SETTINGS ===
symbol = "QQQ"
save_to_desktop = True

# === GET DATA ===
today = datetime.datetime.now()
start_date = today - datetime.timedelta(days=45)
data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), progress=False)
data = data.dropna()
data = data[data.index.date < datetime.date.today()]

# === CALCULATE RAW BUY PRESSURE VALUES ===
recent_data = data.tail(30)
raw_pressures = []
pressure_dates = []

for date, row in recent_data.iterrows():
    volume = float(row['Volume'].item())
    open_price = float(row['Open'].item())
    close_price = float(row['Close'].item())
    buy_pressure = float(volume * (close_price - open_price) / open_price)
    raw_pressures.append(buy_pressure)
    pressure_dates.append(date.strftime('%m/%d'))

# === SCALE TO 0–100 RANGE ===
min_pressure = min(raw_pressures)
max_pressure = max(raw_pressures)

if max_pressure == min_pressure:
    scaled_pressures = [50.0 for _ in raw_pressures]
else:
    scaled_pressures = [
        round((p - min_pressure) / (max_pressure - min_pressure) * 100, 2)
        for p in raw_pressures
    ]

# === LAST TWO TRADING DAYS ===
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

# === RAW BUY PRESSURE FOR PREDICTION ===
pressures = []
for _, row in last_two.iterrows():
    volume = float(row['Volume'].item())
    open_price = float(row['Open'].item())
    close_price = float(row['Close'].item())
    buy_pressure = float(volume * (close_price - open_price) / open_price)
    pressures.append(buy_pressure)

pressure_1 = pressures[0]
pressure_2 = pressures[1]

# === PREDICTION ===
if pressure_2 > pressure_1:
    short_result = "BULLISH"
    color = "green"
    prediction = "🚀 BULLISH\n\nQQQ is predicted to go up today."
else:
    short_result = "BEARISH"
    color = "red"
    prediction = "📉 BEARISH\n\nQQQ may stay flat or go down today."

# === STATS (ON SCALED DATA) ===
mean_scaled = statistics.mean(scaled_pressures)
try:
    mode_scaled = statistics.mode(scaled_pressures)
except statistics.StatisticsError:
    mode_scaled = "No repeating values"

# === SCALE LAST TWO PRESSURES FOR DISPLAY ===
scaled_1 = round((pressure_1 - min_pressure) / (max_pressure - min_pressure) * 100, 2) if max_pressure != min_pressure else 50.0
scaled_2 = round((pressure_2 - min_pressure) / (max_pressure - min_pressure) * 100, 2) if max_pressure != min_pressure else 50.0

# === RESULT TEXT ===
formula = "Buy Pressure = volume × (close - open) / open"
result = (
    f"{prediction}\n\n"
    f"{formula}\n\n"
    f"{date_1_label}:\n  Scaled Pressure: {scaled_1:.2f} / 100\n\n"
    f"{date_2_label}:\n  Scaled Pressure: {scaled_2:.2f} / 100\n\n"
    f"30-Day Stats (Scaled):\n"
    f"  Average Buy Pressure: {mean_scaled:.2f}\n"
    f"  Mode Buy Pressure: {mode_scaled if isinstance(mode_scaled, str) else f'{mode_scaled:.2f}'}"
)

# === SAVE TO FILE ===
if save_to_desktop:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"QQQ_Prediction_{today.strftime('%Y-%m-%d')}.txt"
    filepath = os.path.join(desktop, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(result)

# === EXIT HANDLER ===
def on_exit():
    plt.close('all')
    os._exit(0)

# === POP-UP WINDOW ===
def show_popup():
    window = tk.Tk()
    window.title("QQQ Sentiment Prediction")
    window.geometry("550x350")
    window.protocol("WM_DELETE_WINDOW", on_exit)
    label = tk.Label(window, text=short_result, font=("Helvetica", 48), fg=color)
    label.pack(pady=10)
    pressure_label = tk.Label(
        window,
        text=f"{date_2_label}\nScaled Pressure: {scaled_2:.2f}/100\n\n"
             f"{date_1_label}\nScaled Pressure: {scaled_1:.2f}/100\n\n"
             f"Avg (30d): {mean_scaled:.2f}\nMode (30d): {mode_scaled if isinstance(mode_scaled, str) else f'{mode_scaled:.2f}'}",
        font=("Helvetica", 12)
    )
    pressure_label.pack()
    window.mainloop()

# === SHOW CHART ===
def show_chart():
    def on_close(event):
        on_exit()

    point_colors = []
    for _, row in recent_data.iterrows():
        open_price = float(row['Open'].item())
        close_price = float(row['Close'].item())
        if close_price > open_price:
            point_colors.append("green")
        elif close_price < open_price:
            point_colors.append("red")
        else:
            point_colors.append("gray")

    fig = plt.figure(figsize=(10, 4))
    plt.scatter(pressure_dates, scaled_pressures, c=point_colors, s=60, label="Daily Buy Pressure")
    plt.plot(pressure_dates, scaled_pressures, linestyle='-', color='blue', alpha=0.3)
    plt.axhline(50, color='gray', linestyle='--', linewidth=1, label="Midpoint")
    plt.axhspan(0, 34, facecolor='red', alpha=0.1, label="Bearish Zone (<38)")
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    plt.title(f"{symbol} Buy Pressure - Last 30 Trading Days (Scaled)")
    plt.xlabel("Date")
    plt.ylabel("Scaled Pressure")
    plt.legend()
    plt.tight_layout()
    fig.canvas.mpl_connect("close_event", on_close)
    plt.show()

import threading

threading.Thread(target=show_popup, daemon=True).start()
show_chart()
