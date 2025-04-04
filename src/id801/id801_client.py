import json
import time
import socket


HOST: str = "localhost"
PORT: int = 8010

class ID801_Client:
    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        """
        Initialize the ID801 client and connect to the ID801 server.

        Args:
            host (str, optional): The address of the ID801 server. Defaults to "localhost".
            port (int, optional): The port number of the ID801 server. Defaults to 8010.
        """
        self.host = host
        self.port = port
    
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print("Connected to server.")
        except Exception as e:
            print(f"Fail to connect to ID801 server: {e}")
            raise e
    
    def __del__(self):
        """Close the connection when the object is deleted (automatic garbage collection)."""
        if self.client_socket:
            self.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Also close the connection when exiting (used with with statement)."""
        if self.client_socket:
            self.close()
        
    def send_request(self, request: str) -> dict:
        """
        Send a request to the server and receive the response.

        Args:
            request (str): The request string to send to the server.

        Returns:
            dict: The response from the server, parsed as a JSON object.
            This includes timestamp (ISO-timestamp) and status (str).
        """
        try:
            self.client_socket.sendall(request.encode())
            response: bytes = self.client_socket.recv(1024)
            if not response:
                print('if801_client.py send_request() got empty reply from server.')
            return json.loads(response.decode())
        except Exception as e:
            return {"error": e}
        
    def set_coincidence_window(self, coinc_window: int) -> dict:
        """
        Set the coincidence window for the ID801 device.

        Args:
            coinc_window (int): The coincidence window in TDC units.

        Returns:
            dict: The response from the server, parsed as a JSON object.
            This includes timestamp (ISO-timestamp str) and status (str).
        """
        request = f"set_coincidence_window {coinc_window}"
        return self.send_request(request)
        
    def set_exposure_time(self, exposure: int) -> dict:
        """
        Set the exposure time for the ID801 device.

        Args:
            exposure (int): The exposure time in milliseconds.

        Returns:
            dict: The response from the server, parsed as a JSON object.
            This includes timestamp (ISO-timestamp str) and status (str).
        """
        request = f"set_exposure_time {exposure}"
        return self.send_request(request)

    def get_coinc_counters(self) -> tuple[list[int], list[str], int]:
        """
        Get the coincidence counters from the ID801 device.


        Returns:
            tuple:
            - data (list[int]): List of 19 integers representing the counter values.
            - labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            - updates (int): Number of data updates by the device since the last
        """
        res = self.send_request("get_coinc_counters")
        return res["coinc_data"], res["channels"], res["updates"]
    
    def wait_to_get_coinc_counters_for(self, exposure: int, coinc_win: int) -> tuple[list[int], list[str], int]:
        """
        Wait for the exposure time to finish and then get the coincidence counters.

        Note:
            This function is altered to return the same tuple as ID801 instances while the other functions return json

        Args:
            exposure (int): The exposure time in milliseconds.
            coinc_win (int): The coincidence window in TDC units (81ps).

        Returns:
           tuple:
            - data (list[int]): List of 19 integers representing the counter values.
            - labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            - updates (int): Number of data updates by the device since the last call.
        """
        self.set_exposure_time(exposure)
        self.set_coincidence_window(coinc_win)
        time.sleep(exposure / 1000)
        return self.get_coinc_counters()
    
    def get_last_coinc_counters(self, exposure: int, coinc_win: int) -> tuple[list[int], list[str], int]:
        """
        Get the coincidence counters for the last exposure time.

        Args:
            exposure (int): The exposure time in milliseconds.
            coinc_win (int): The coincidence window in TDC units (81ps).

        Returns:
            tuple:
            - data (list[int]): List of 19 integers representing the counter values.
            - labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            - updates (int): Number of data updates by the device since the last call.
        """
        request = f"get_last_coinc_counters {exposure} {coinc_win}"
        res = self.send_request(request)
        return res["coinc_data"], res["channels"], res["updates"]

    def close(self) -> None:
        """Close the socket connection."""
        if self.client_socket:
            self.client_socket.close()
            print("Connection closed.")


if __name__ == "__main__":
    client = ID801_Client()
    try:
        while True:
            data, labels, updates = client.get_last_coinc_counters(100, 100)
            print(f"Data: {data}")
            print(f"Labels: {labels}")
            print(f"Updates: {updates}")            

    except KeyboardInterrupt:
        print("Shutting down client.")
