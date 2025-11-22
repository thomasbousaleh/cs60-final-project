# rdt_receiver.py
import sys
import socket
import random
from typing import Optional

from common import (
    build_packet,
    parse_packet,
    FLAG_DATA,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_FIN_ACK,
)

RECV_BUFFER = 4096


def maybe_send(sock: socket.socket, packet: bytes, addr, loss_prob: float, label: str):
    """
    Simulate packet loss by randomly dropping packets instead of sending.
    loss_prob: probability in [0,1] that the packet is DROPPED.
    """
    if random.random() < loss_prob:
        print(f"[RECV] *** Simulated DROP of {label} ***")
        return
    sock.sendto(packet, addr)


def receiver(listen_port: int, output_file: str, loss_prob: float):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", listen_port))
    print(f"[RECV] Listening on UDP port {listen_port}")

    expected_seq = 0     # next in-order seq we expect
    last_acked: Optional[int] = None
    sender_addr = None

    # Statistics
    total_rcvd = 0
    total_delivered = 0
    total_corrupt = 0
    total_dups = 0

    done = False

    with open(output_file, "wb") as f_out:
        while not done:
            raw, addr = sock.recvfrom(RECV_BUFFER)
            if sender_addr is None:
                sender_addr = addr

            total_rcvd += 1

            # Attempt to parse/check checksum
            try:
                seq, flags, payload = parse_packet(raw)
            except ValueError as e:
                print(f"[RECV] Corrupt packet: {e}")
                total_corrupt += 1
                # Can't ACK what we don't know, but we can re-ACK last good packet
                if last_acked is not None:
                    ack_pkt = build_packet(last_acked, FLAG_ACK, b"")
                    maybe_send(sock, ack_pkt, sender_addr, loss_prob, "ACK(re-ACK)")
                continue

            if flags == FLAG_DATA:
                print(f"[RECV] Got DATA seq={seq}, len={len(payload)} bytes")

                if seq == expected_seq:
                    # In-order packet
                    f_out.write(payload)
                    total_delivered += 1

                    last_acked = seq
                    expected_seq += 1

                    ack_pkt = build_packet(seq, FLAG_ACK, b"")
                    maybe_send(sock, ack_pkt, sender_addr, loss_prob, f"ACK(seq={seq})")
                    print(f"[RECV] Sent ACK for seq={seq}")

                elif seq < expected_seq:
                    # Duplicate
                    total_dups += 1
                    print(f"[RECV] Duplicate seq={seq}, expected={expected_seq}")
                    if last_acked is not None:
                        ack_pkt = build_packet(last_acked, FLAG_ACK, b"")
                        maybe_send(sock, ack_pkt, sender_addr, loss_prob, f"ACK(dup seq={last_acked})")
                else:
                    # seq > expected_seq -> out-of-order for Go-Back-N
                    print(f"[RECV] Out-of-order seq={seq}, expected={expected_seq}. Discard.")
                    if last_acked is not None:
                        ack_pkt = build_packet(last_acked, FLAG_ACK, b"")
                        maybe_send(sock, ack_pkt, sender_addr, loss_prob, f"ACK(out-of-order seq={last_acked})")

            elif flags == FLAG_FIN:
                print("[RECV] Received FIN, sending FIN-ACK and closing.")
                fin_ack = build_packet(0, FLAG_FIN_ACK, b"")
                maybe_send(sock, fin_ack, sender_addr, loss_prob, "FIN-ACK")
                done = True

            else:
                print(f"[RECV] Unknown flag={flags}, ignoring.")

    sock.close()

    print("\n[RECV] Receiver stats:")
    print(f"  Total packets received:   {total_rcvd}")
    print(f"  Delivered in-order:       {total_delivered}")
    print(f"  Corrupt packets:          {total_corrupt}")
    print(f"  Duplicate packets:        {total_dups}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python rdt_receiver.py <listen_port> <output_file> [loss_prob]")
        print("Example: python rdt_receiver.py 9000 output.bin 0.1")
        sys.exit(1)

    listen_port = int(sys.argv[1])
    output_file = sys.argv[2]
    loss_prob = float(sys.argv[3]) if len(sys.argv) >= 4 else 0.0

    random.seed()
    receiver(listen_port, output_file, loss_prob)


if __name__ == "__main__":
    main()