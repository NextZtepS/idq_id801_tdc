import argparse
import csv
from datetime import datetime
import os
from queue import Queue
from threading import Thread, Lock

from src.id801.id801 import ID801


def write_data_to_csv(file_name: str, data_queue: Queue, lock: Lock, batch_size: int):
    buffer = []
    while True:
        batch_data = data_queue.get()
        if batch_data is None:  # Sentinel value to end the thread
            break
        buffer.extend(batch_data)
        if len(buffer) >= batch_size:
            write_to_csv(file_name, buffer, lock)
            buffer.clear()
    # Write any remaining data in the buffer
    if buffer:
        write_to_csv(file_name, buffer, lock)


def write_to_csv(file_name: str, data: list, lock: Lock):
    with lock:
        with open(file_name, "a", newline='', buffering=8192) as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(data)


def collect_data(id801: ID801, exp_time: int = 100, batch_size: int = 100_000):
    batch_data = []
    timestamps, channels = id801.get_timestamps(exp_time)
    for timestamp, channel in zip(timestamps, channels):
        batch_data.append([timestamp, channel])
    return batch_data


def main(id801: ID801, file_name: str, exp_time: int = 100, batch_size: int = 100_000):
    data_queue = Queue()
    lock = Lock()

    # Start the writer thread
    writer_thread = Thread(target=write_data_to_csv, args=(file_name, data_queue, lock, batch_size))
    writer_thread.start()

    # Write the header if the file is empty
    if not os.path.isfile(file_name) or os.path.getsize(file_name) == 0:
        write_to_csv(file_name, [["Timestamp", "Channel"]], lock)

    try:
        while True:
            batch_data = collect_data(id801, exp_time, batch_size)
            data_queue.put(batch_data)
    except KeyboardInterrupt:
        # Stop the writer thread
        data_queue.put(None)
        writer_thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp_time", "-e", default=100, type=int, help="Set the exposure time (ms)")
    parser.add_argument("--batch_size", "-b", default=100_000, type=int, help="Set the batch size for writing to CSV (Default: 100,000 which 10% of 1MHz)")
    args = parser.parse_args()
    exp_time = args.exp_time
    batch_size = args.batch_size

    id801 = ID801()
    id801.switch_termination(False)
    start_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    main(id801, f"timestamps_{start_time}.csv", exp_time, batch_size)
