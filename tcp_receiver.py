# tcp_receiver.py

# CS60 25F
# Thomas Bousaleh and Edward Kim
# Final Project
# Citations: Class notes slideshows generally, Lab 4 instructions and work,
# as well as an LLM, ChatGPT 5.1

# Important Note: 
# This is a Quick TCP baseline script used only for performance comparison with our UDP RDT.
# NOT part of the main project; just raw TCP send/receive for our reference.

import sys
import socket
import time

def tcp_receiver(listen_port: int, output_file: str):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("", listen_port))
    srv.listen(1)
    print(f"[TCP RECV] Listening on TCP port {listen_port}")

    conn, addr = srv.accept()
    print(f"[TCP RECV] Connection from {addr}")

    start_time = time.time()
    total_bytes = 0

    with open(output_file, "wb") as f_out:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            f_out.write(data)
            total_bytes += len(data)

    end_time = time.time()
    elapsed = end_time - start_time
    conn.close()
    srv.close()

    print(f"[TCP RECV] Received {total_bytes} bytes")
    print(f"[TCP RECV] Elapsed time (s): {elapsed:.6f}")
    if elapsed > 0:
        mbps = (total_bytes * 8) / (elapsed * 1_000_000)
        print(f"[TCP RECV] Throughput: {mbps:.3f} Mbit/s")

def main():
    if len(sys.argv) != 3:
        print("Usage: python tcp_receiver.py <listen_port> <output_file>")
        sys.exit(1)
    listen_port = int(sys.argv[1])
    output_file = sys.argv[2]
    tcp_receiver(listen_port, output_file)

if __name__ == "__main__":
    main()