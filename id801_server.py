import asyncio
from datetime import datetime
import json
from id801 import ID801


# Server settings
HOST: str = "localhost"
PORT: int = 8010

# Initialize the ID801 device
id801 = ID801()
id801_lock = asyncio.Lock()


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    global id801, id801_lock

    client = writer.get_extra_info("peername")
    print(f"New connection from {client}")

    while True:
        try:
            req: bytes = await reader.read(1024)
            if not req:
                break  # Client disconnected

            request: str = req.decode().strip()
            print(f"Received: {request} from {client}")

            # Process the request
            async with id801_lock:
                request_params = request.split()
                match request_params:
                    case ["set_coincidence_window", coinc_win]:
                        coinc_win = int(coinc_win)
                        id801.set_coincidence_window(coinc_win)
                        res = {
                            "timestamp": datetime.now().isoformat(),
                            "status": f"Coincidence window set to {coinc_win} TDC units",
                        }

                    case ["set_exposure_time", exp_time]:
                        exp_time = int(exp_time)
                        id801.set_exposure_time(exp_time)
                        res = {
                            "timestamp": datetime.now().isoformat(),
                            "status": f"Exposure time set to {exp_time} ms",
                        }

                    case ["get_coinc_counters"]:
                        coinc_data, channels, updates = id801.get_coinc_counters()
                        res = {
                            "timestamp": datetime.now().isoformat(),
                            "coinc_data": coinc_data,
                            "channels": channels,
                            "updates": updates,
                        }

                    case ["get_last_coinc_counters", exp_time, coinc_win]:
                        exp_time = int(exp_time)
                        coinc_win = int(coinc_win)
                        coinc_data, channels, updates = id801.get_last_coinc_counters(exp_time, coinc_win)
                        res = {
                            "timestamp": datetime.now().isoformat(),
                            "coinc_data": coinc_data,
                            "channels": channels,
                            "updates": updates,
                        }

                    case _:
                        res = {
                            "timestamp": datetime.now().isoformat(),
                            "error": "Unknown command",
                        }

            response = json.dumps(res)
            writer.write(response.encode())
            await writer.drain()

        except ConnectionResetError:
            break

    print(f"Connection closed: {client}")
    writer.close()
    await writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle_client, HOST, PORT)
    client = server.sockets[0].getsockname()
    print(f"Server listening on {client}")

    async with server:
        await server.serve_forever()


# Run the async server
asyncio.run(main())
