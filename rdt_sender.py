# rdt_sender.py
import sys
import socket
import time
import random
from typing import List

from common import (
    build_packet,
    parse_packet,
    FLAG_DATA,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_FIN_ACK,
    MAX_DATA_SIZE,
)

# --- Tunable parameters ---
WINDOW_SIZE = 10        # sliding window size (you can tweak)
TIMEOUT_SEC = 0.2       # retransmission timeout (seconds)
RECV_BUFFER = 4096      # recv buffer size (bytes)


def maybe_send(sock: socket.socket, packet: bytes, addr, loss_prob: float):
    """
    Simulate packet loss by randomly dropping packets instead of sending.
    loss_prob: probability in [0,1] that the packet is DROPPED.
    """
    if random.random() < loss_prob:
        # simulate loss: do not send
        print("[SENDER] *** Simulated DROP of packet ***")
        return
    sock.sendto(packet, addr)


def load_file_chunks(filename: str) -> List[bytes]:
    """Read file and split into <= MAX_DATA_SIZE chunks."""
    chunks = []
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(MAX_DATA_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
    return chunks


def sender(host: str, port: int, filename: str, loss_prob: float):
    addr = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.01)  # short poll timeout for ACKs

    data_chunks = load_file_chunks(filename)
    num_packets = len(data_chunks)
    print(f"[SENDER] Loaded {num_packets} data packets from {filename}")

    # Pre-build all data packets with sequence numbers 0..num_packets-1
    packets = [build_packet(i, FLAG_DATA, data_chunks[i]) for i in range(num_packets)]

    base = 0           # oldest unACKed packet
    next_seq = 0       # next packet to send
    timer_start = None # start time of timer (for 'base')

    # Statistics
    total_sent = 0
    total_retrans = 0
    total_acks = 0

    # Go-Back-N main loop
    while base < num_packets:
        # Fill the window
        while next_seq < num_packets and next_seq < base + WINDOW_SIZE:
            maybe_send(sock, packets[next_seq], addr, loss_prob)
            total_sent += 1
            print(f"[SENDER] Sent packet seq={next_seq}")
            if base == next_seq:
                timer_start = time.time()
            next_seq += 1

        # Try to receive ACKs
        try:
            raw, _ = sock.recvfrom(RECV_BUFFER)
            try:
                ack_seq, flags, _ = parse_packet(raw)
            except ValueError as e:
                print(f"[SENDER] Ignoring bad ACK packet: {e}")
                continue

            if flags == FLAG_ACK:
                total_acks += 1
                print(f"[SENDER] Received ACK for seq={ack_seq}")
                if ack_seq >= base:
                    base = ack_seq + 1
                    if base == next_seq:
                        # window empty
                        timer_start = None
                    else:
                        timer_start = time.time()
        except socket.timeout:
            pass  # no ACKs this poll

        # Check for timeout on base packet
        if timer_start is not None and (time.time() - timer_start) >= TIMEOUT_SEC:
            print(f"[SENDER] TIMEOUT: resending window base={base}, next_seq={next_seq}")
            # Retransmit all unACKed packets
            for seq in range(base, next_seq):
                maybe_send(sock, packets[seq], addr, loss_prob)
                total_sent += 1
                total_retrans += 1
                print(f"[SENDER] Retransmitted seq={seq}")
            timer_start = time.time()

    # All data ACKed, now send FIN to indicate completion
    print("[SENDER] All data acknowledged, sending FIN")
    fin_packet = build_packet(0, FLAG_FIN, b"")
    fin_acked = False
    fin_retries = 0

    while not fin_acked and fin_retries < 10:
        maybe_send(sock, fin_packet, addr, loss_prob)
        total_sent += 1           # count FIN as a sent packet
        fin_retries += 1
        try:
            raw, _ = sock.recvfrom(RECV_BUFFER)
            try:
                seq, flags, _ = parse_packet(raw)
            except ValueError:
                continue
            if flags == FLAG_FIN_ACK:
                print("[SENDER] Received FIN-ACK, closing")
                fin_acked = True
                break
        except socket.timeout:
            print("[SENDER] No FIN-ACK, retrying FIN...")

    sock.close()

    print("\n[SENDER] Transmission stats:")
    print(f"  Total packets sent:        {total_sent}")
    print(f"  Total retransmissions:     {total_retrans}")
    print(f"  Unique data packets:       {num_packets}")
    print(f"  ACKs received:             {total_acks}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python rdt_sender.py <receiver_host> <receiver_port> <input_file> [loss_prob]")
        print("Example: python rdt_sender.py 127.0.0.1 9000 input.bin 0.1")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    filename = sys.argv[3]
    loss_prob = float(sys.argv[4]) if len(sys.argv) >= 5 else 0.0

    random.seed()
    sender(host, port, filename, loss_prob)


if __name__ == "__main__":
    main()