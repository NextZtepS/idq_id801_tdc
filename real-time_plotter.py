"""
If you are using the ID801 in server mode, you need to run the server first like this:
python3 id801_server.py

If not using the server mode, you can run this script directly like this:
python3 real-time_plotter.py -A "1" "2" -B "1/2" -w 500
-e 100 would set the exposure time to 100ms, which is the default
-w 500 sets the coincidence window to 500 * 81ps = 40.5 ns
-A is the list of channels for the top plot, usually singles channels
-B is the list of channels for the bottom plot, usually coincidence channels
"""

import argparse
import csv
import matplotlib
import os
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
from id801 import ID801
from id801 import ID801_Subscriber


def main(
    id801: ID801 | ID801_Subscriber,
    exp_time: int,
    coinc_win: int,
    channels_A: list[str],
    channels_B: list[str],
    save: bool,
):
    # Get initial data
    data, labels, _ = id801.get_last_coinc_counters(exp_time, coinc_win)

    # Initialize the plots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
    fig.subplots_adjust(hspace=0.4)

    # Bar plot setup
    bars = ax1.bar(labels, data)
    ax1.set_title(
        f"Exposure: {exp_time}ms | Coinc Window: {coinc_win}TDC\n\nReal-Time TDC Plotter"
    )
    ax1.set_xlabel("Channels")
    ax1.set_ylabel("Counts")
    ax1.grid(axis="y")

    def add_labels(bars, data):
        for bar, count in zip(bars, data):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{count}",
                ha="center",
                va="bottom",
            )

    add_labels(bars, data)

    # Time-series plots
    frames_to_keep = 60 * 1000 // exp_time + 1  # Store last 60s of data
    history_A = {label: [0] * frames_to_keep for label in channels_A}
    history_B = {label: [0] * frames_to_keep for label in channels_B}

    # Define line plots for channels
    lines_A = {
        label: ax2.plot(
            [],
            [],
            label=label,
            color="red" if label == "1" else "blue" if label == "2" else None,
        )[0]
        for label in channels_A
    }
    lines_B = {label: ax3.plot([], [], label=label)[0] for label in channels_B}

    ax2.set_xlim(0, frames_to_keep - 1)
    ax2.set_ylim(0, max(data) * 1.1 + 1)
    ax2.set_title("A Channel Counters Over Time")
    ax2.set_xlabel("Frames")
    ax2.set_ylabel("Counts")
    ax2.grid()
    ax2.legend()

    ax3.set_xlim(0, frames_to_keep - 1)
    ax3.set_ylim(0, max(data) * 1.1 + 1)
    ax3.set_title("B Channel Counters Over Time")
    ax3.set_xlabel("Frames")
    ax3.set_ylabel("Counts")
    ax3.grid()
    ax3.legend()

    if save:
        start_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        csv_file = open(f"coinc_counts_{start_time}.csv", "a", newline="")
        csv_writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            csv_file.write(
                f"# Exposure Time: {exp_time}ms\n# Coincidence Window: {coinc_win}TDC\n"
            )
            csv_writer.writerow(["timestamp"] + labels)

    def update(frame):
        nonlocal bars
        data, labels, _ = id801.get_last_coinc_counters(exp_time, coinc_win)

        ax1.set_ylim(0, max(data) * 1.1 + 1)

        for bar, height, text in zip(bars, data, ax1.texts):
            bar.set_height(height)
            text.set_text(f"{height}")
            text.set_position((bar.get_x() + bar.get_width() / 2, height))

        for channel in channels_A:
            if channel in labels:
                idx = labels.index(channel)
                history_A[channel].append(data[idx])
                history_A[channel].pop(0)
                lines_A[channel].set_data(range(len(history_A[channel])), history_A[channel])

        ax2.set_ylim(0, max(max(history_A.values(), default=[0])) * 1.1 + 1)

        for channel in channels_B:
            if channel in labels:
                idx = labels.index(channel)
                history_B[channel].append(data[idx])
                history_B[channel].pop(0)
                lines_B[channel].set_data(range(len(history_B[channel])), history_B[channel])

        ax3.set_ylim(0, max(max(history_B.values(), default=[0])) * 1.1 + 1)

        if save:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
            csv_writer.writerow([timestamp] + data)

        return []

    global ani
    ani = animation.FuncAnimation(fig, update, frames=1, interval=exp_time)
    plt.show()

    if save:
        csv_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exp_time", "-e", default=100, type=int, help="Set the exposure time (ms)"
    )
    parser.add_argument(
        "--coinc_win",
        "-w",
        default=500,
        type=int,
        help="Set the coincidence window (TDC Unit)",
    )
    parser.add_argument(
        "--channels_A",
        "-A",
        nargs="+",
        default=["1", "2"],
        type=str,
        help="A Channel labels to monitor",
    )
    parser.add_argument(
        "--channels_B",
        "-B",
        nargs="+",
        default=["1/2"],
        type=str,
        help="B Channel labels to monitor",
    )
    parser.add_argument(
        "--save", "-s", action="store_true", help="Save the data to a file"
    )
    args = parser.parse_args()

    # Try to use ID801_Subscriber  first if available
    # If not, fallback to claiming the device directly
    scriptname = os.path.basename(__file__)  # Gets just the scriptname
    try:
        print(f"{scriptname} : Trying to create ID801_Subscriber.")    
        id801 = ID801_Subscriber()
    except Exception as e:
        print(f"{scriptname} :  Error initializing ID801 ID801_Subscriber: {e}")
        print(f"{scriptname} : Trying to claim ID801 device...")
        try:
            id801 = ID801()
            id801.initialize()
        except Exception as e:
            raise e  # probably quit the program at this point.
    
    main(
        id801,
        args.exp_time,
        args.coinc_win,
        args.channels_A,
        args.channels_B,
        args.save,
    )
