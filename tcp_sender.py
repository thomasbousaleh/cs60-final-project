# tcp_sender.py

# CS60 25F
# Thomas Bousaleh and Edward Kim
# Final Project
# Citations: Class notes slideshows generally, Lab 4 instructions and work,
# as well as an LLM, ChatGPT 5.1

# Important Note: 
# This is a Quick TCP baseline script used only for performance comparison with our UDP RDT.
# Not part of the main project; just raw TCP send/receive for our reference.

import sys
import socket
import time
import os

# Important Note: 
# This is a Quick TCP baseline script used only for performance comparison with our UDP RDT.
# Not part of the main project; just raw TCP send/receive for our reference.

def tcp_sender(host: str, port: int, filename: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    file_size = os.path.getsize(filename)

    start_time = time.time()
    total_sent = 0

    with open(filename, "rb") as f_in:
        while True:
            chunk = f_in.read(4096)
            if not chunk:
                break
            sock.sendall(chunk)
            total_sent += len(chunk)

    sock.shutdown(socket.SHUT_WR)
    sock.close()

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"[TCP SEND] Sent {total_sent} bytes")
    print(f"[TCP SEND] Elapsed time (s): {elapsed:.6f}")
    if elapsed > 0:
        mbps = (file_size * 8) / (elapsed * 1_000_000)
        print(f"[TCP SEND] Throughput: {mbps:.3f} Mbit/s")

def main():
    if len(sys.argv) != 4:
        print("Usage: python tcp_sender.py <receiver_host> <receiver_port> <input_file>")
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    filename = sys.argv[3]
    tcp_sender(host, port, filename)

if __name__ == "__main__":
    main()