import socket
import json
import time
import select

HOST = "localhost"
PORT = 8010


class ID801_Subscriber:
    def __init__(self, host: str = HOST, port: int = PORT):
        """Initialize the subscriber."""
        self._host = host
        self._port = port
        self._socket = None
        self._connect()

    def _connect(self):
        """Establish a connection to the publisher with a retry mechanism."""
        while True:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.connect((self._host, self._port))
                print("Connected to publisher.")
                self._socket.setblocking(False)  # Set non-blocking mode
                break
            except (ConnectionRefusedError, OSError):
                print("Publisher not available. Retrying in 2 seconds...")
                time.sleep(2)

    def retrieve_data(self):
        """Retrieve the latest coincidence counter data from the publisher using select."""
        buffer = ""  # Buffer to store JSON data
        while True:
            if self._socket is None:
                self._connect()
            else:
                try:
                    readable, _, _ = select.select([self._socket], [], [], 5.0)
                    if readable:
                        response = self._socket.recv(1024).decode()
                        if not response:
                            raise ConnectionResetError
                        
                        buffer += response
                        
                        # Try to extract valid JSON objects
                        messages = []
                        while True:
                            try:
                                message, index = json.JSONDecoder().raw_decode(buffer)
                                messages.append(message)
                                buffer = buffer[index:].lstrip()  # Remove parsed JSON
                            except json.JSONDecodeError:
                                break  # Incomplete JSON, wait for more data
                        
                        # there is an error here that only occurs when running real-time_plotter.py, not id801_subscriber.py
                        # When running real-time_plotter.py the subscriber will sometimes run retrieve_data and return messages[-1] instead of the actual data
                        # not sure why id801_subscriber.py runs correctly while real-time_plotter.py does not since the implementation looks the same in both files
                        return messages[-1] if messages else None 
                    
                    return None

                except (ConnectionResetError, BrokenPipeError):
                    print("Connection lost. Reconnecting...")
                    self._connect()

    def get_last_coinc_counters(self, exp_time: int, coinc_win: int):
        """
        Retrieve the last coincidence counters from the publisher.

        Args:
            exp_time (int): exposure time in milliseconds (must be a multiple of 100)
            coinc_win (int): coincidence window in TDC units (ignored in this function)

        Returns:
            tuple:
                - coinc_data (list): List of coincidence data counts.
                - labels (list): List of labels for the coincidence data.
                - updates (int): Number of updates received.
        """
        assert exp_time % 100 == 0, "exp_time must be a multiple of 100"

        coinc_data = [0] * 19
        updates = 0
        for _ in range(exp_time // 100):
            data = self.retrieve_data()
            if data:
                coinc_data = [sum(x) for x in zip(coinc_data, data.get("coinc_data", [0] * 19))]
                updates += data.get("updates", 0)

        labels = [
            "1", "2", "3", "4", "5", "6", "7", "8", "1/2", "1/3", "1/4",
            "2/3", "2/4", "3/4", "1/2/3", "1/2/4", "1/3/4", "2/3/4", "1/2/3/4",
        ]
        return coinc_data, labels, updates


if __name__ == "__main__":
    subscriber = ID801_Subscriber()
    coinc_data, labels, _ = subscriber.get_last_coinc_counters(1000, 500)
    print(labels)
    print(coinc_data)
    try:
        while True:
            coinc_data, _, _ = subscriber.get_last_coinc_counters(1000, 500)
            print(coinc_data)
    except KeyboardInterrupt:
        print("Exiting...")
