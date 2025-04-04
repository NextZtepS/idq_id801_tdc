import argparse
import socket
import json
import time
from id801 import ID801

# Server settings
HOST = "localhost"
PORT = 8010
LABELS =  [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "1/2",
    "1/3",
    "1/4",
    "2/3",
    "2/4",
    "3/4",
    "1/2/3",
    "1/2/4",
    "1/3/4",
    "2/3/4",
    "1/2/3/4",
]


def main(id801: ID801 | None, exp_time: int, coinc_win: int, test_mode: bool = False):
    """Main function to handle subscribers and broadcast data."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        server_socket.setblocking(False)  # Non-blocking accept
        print(f"Publisher listening on {HOST}:{PORT}")
        print("(Test Mode)") if test_mode else None

        connections: list[socket.socket] = []

        while True:
            # Handle new connections
            try:
                conn, addr = server_socket.accept()
                conn.setblocking(False)  # Make it non-blocking
                connections.append(conn)
                print(f"New subscriber: {addr}")
            except BlockingIOError:
                pass  # No new connection, continue broadcasting

            # Retrieve coincidence counter data
            if id801:
                coinc_data, labels, updates = id801.get_last_coinc_counters(
                    exp_time, coinc_win
                )
            elif test_mode:
                coinc_data = [1] * 19
                labels = LABELS
                updates = 1
                time.sleep(exp_time / 1000)  # Simulate data retrieval delay
            else:
                coinc_data = [None] * 19
                labels = LABELS
                updates = 0
                time.sleep(exp_time / 1000)  # Simulate data retrieval delay

            message = json.dumps(
                {
                    "coinc_data": coinc_data,
                    "labels": labels,
                    "updates": updates,
                    "exp_time_ms": exp_time,
                    "coinc_win": coinc_win,
                }
            )

            # Send message to all connected clients
            for conn in connections:
                try:
                    conn.sendall(message.encode())
                except (BrokenPipeError, ConnectionResetError):
                    print("Removing disconnected client")
                    connections.remove(conn)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode with simulated data"
    )
    parser.add_argument(
        "--exp_time", "-e", type=int, default=100, help="Exposure time in milliseconds"
    )
    parser.add_argument(
        "--coinc_win",
        "-w",
        type=int,
        default=500,
        help="Coincidence window in TDC units",
    )
    args = parser.parse_args()

    id801 = ID801() if not args.test else None

    main(id801, args.exp_time, args.coinc_win, args.test)
