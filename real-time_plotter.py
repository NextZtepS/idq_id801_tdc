import argparse
import csv
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime

from src.id801.id801 import ID801


def main(id801: ID801, exp_time: int, coinc_win: int, switch_termination: int, channels_A: list[str], channels_B: list[str], save: bool = False):
    # Initialize the ID801 instance and set the parameters
    id801.set_timestamp_buffer_size(id801.MAX_TIMESTAMP_BUFFER_SIZE)
    id801.switch_termination(bool(switch_termination))

    # Get initial data
    data, labels, updates = id801.get_last_coinc_counters(exp_time, coinc_win)

    # Initialize the plots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
    fig.subplots_adjust(hspace=0.4)

    # Set the title and labels for bar plot
    bars = ax1.bar(labels, data)
    ax1.set_title(f"Exposure: {exp_time}ms | Coinc Window: {coinc_win}TDC | Termination: {'on' if switch_termination else 'off'}\n\nReal-Time TDC Plotter")
    ax1.set_xlabel("Channels")
    ax1.set_ylabel("Counts")
    ax1.grid(axis="y")

    # Add count labels on the bars
    def add_labels(bars, data):
        for bar, count in zip(bars, data):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, height, f"{count}", ha="center", va="bottom")

    # Initially add labels
    add_labels(bars, data)

    # Initialize the time-series plot
    frames_to_keep = 60*1000 // exp_time + 1  # to keep the last 60s of measurement 
    history_A = {label: [0] * frames_to_keep for label in channels_A}
    lines_A = {label: ax2.plot([], [], label=label)[0] for label in channels_A}
    ax2.set_xlim(0, frames_to_keep-1)
    ax2.set_ylim(0, max(data) * 1.1)
    ax2.set_title("A Channel Counters Over Time")
    ax2.set_xlabel("Frames")
    ax2.set_ylabel("Counts")
    ax2.grid()
    ax2.legend()

    history_B = {label: [0] * frames_to_keep for label in channels_B}
    lines_B = {label: ax3.plot([], [], label=label)[0] for label in channels_B}
    ax3.set_xlim(0, frames_to_keep-1)
    ax3.set_ylim(0, max(data) * 1.1)
    ax3.set_title("B Channel Counters Over Time")
    ax3.set_xlabel("Frames")
    ax3.set_ylabel("Counts")
    ax3.grid()
    ax3.legend()

    # Open the CSV file in append mode
    if save:
        start_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        csv_file = open(f"coinc_counts_{start_time}.csv", "a", newline='')
        csv_writer = csv.writer(csv_file)

        # Write the header if the file is empty
        if csv_file.tell() == 0:
            csv_file.write(f"# Exposure Time: {exp_time}ms\n# Coincidence Window: {coinc_win}TDC\n# Switch Termination: {switch_termination}\n")
            csv_writer.writerow(["timestamp"] + labels)

    def update(frame):
        # Get new data
        data, labels, updates = id801.get_last_coinc_counters(exp_time, coinc_win)

        # Update y-axis limit to accommodate the highest bar
        ax1.set_ylim(0, max(data) * 1.1)
        
        # Update bar heights and labels
        for bar, height, text in zip(bars, data, ax1.texts):
            bar.set_height(height)
            text.set_text(f"{height}")
            text.set_position((bar.get_x() + bar.get_width() / 2, height))

        # Update the time-series plot for ax2
        for channel in channels_A:
            idx = labels.index(channel)  # Find the index of the channel label
            history_A[channel].append(data[idx])
            if len(history_A[channel]) > frames_to_keep:
                history_A[channel].pop(0)
            lines_A[channel].set_data(range(len(history_A[channel])), history_A[channel])

        # Update the y-axis limit for the time-series plot for ax2
        max_y = max(max(values) for values in history_A.values())
        ax2.set_ylim(0, max_y * 1.1)

        # Update the time-series plot for ax3
        for channel in channels_B:
            idx = labels.index(channel)  # Find the index of the channel label
            history_B[channel].append(data[idx])
            if len(history_B[channel]) > frames_to_keep:
                history_B[channel].pop(0)
            lines_B[channel].set_data(range(len(history_B[channel])), history_B[channel])

        # Update the y-axis limit for the time-series plot for ax3
        max_y = max(max(values) for values in history_B.values())
        ax3.set_ylim(0, max_y * 1.1)

        # Append new data to CSV file
        if save:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
            csv_writer.writerow([timestamp] + data)

        return []

    ani = animation.FuncAnimation(fig, update, frames=1, interval=0)
    plt.show()

    if save:
        csv_file.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp_time", "-e", default=100, type=int, help="Set the exposure time (ms)")
    parser.add_argument("--coinc_win", "-w", default=100, type=int, help="Set the coincidence window (TDC Unit)")
    parser.add_argument("--switch_termination", "-t", default=0, type=int, help="Set the switch termination (0 for off | 1 for on)")
    parser.add_argument("--channels_A", "-A", nargs="+", default=["1", "2"], type=str,
                        help="'A' Channel labels to monitor over time from ['1', '2', '3', '4', '5', '6', '7', '8',\
                            '1/2', '1/3', '1/4', '2/3', '2/4', '3/4', '1/2/3', '1/2/4', '1/3/4', '2/3/4', '1/2/3/4']")
    parser.add_argument("--channels_B", "-B", nargs="+", default=["1/2"], type=str,
                        help="'B' Channel labels to monitor over time from ['1', '2', '3', '4', '5', '6', '7', '8',\
                            '1/2', '1/3', '1/4', '2/3', '2/4', '3/4', '1/2/3', '1/2/4', '1/3/4', '2/3/4', '1/2/3/4']")
    parser.add_argument("--save", "-s", default=False, help="Save the data to a file")
    args = parser.parse_args()
    exp_time = args.exp_time
    coinc_win = args.coinc_win
    switch_termination = args.switch_termination
    channels_A = args.channels_A
    channels_B = args.channels_B
    save = args.save

    id801 = ID801()
    id801.enable_channels([True] * 8)
    main(id801, exp_time, coinc_win, switch_termination, channels_A, channels_B, save)
