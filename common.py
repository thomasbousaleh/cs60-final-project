# common.py

# CS60 25F
# Thomas Bousaleh and Edward Kim
# Final Project
# Citations: Class notes slideshows generally, Lab 4 instructions and work,
# as well as an LLM, ChatGPT 5.1

# Shared packet format and checksum utilities for our reliable UDP protocol;
# Defines header layout, flags, max payload size, packet buider, and parser.

import struct
from typing import Tuple

# --- Protocol constants ---

HEADER_FORMAT = "!IBH"   # seq: uint32, flags: uint8, checksum: uint16
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

FLAG_DATA    = 0
FLAG_ACK     = 1
FLAG_FIN     = 2
FLAG_FIN_ACK = 3

# MTU sort of: 1500 - IP(20) - UDP(8) ≈ 1472 bytes
MAX_UDP_PAYLOAD = 1472
MAX_DATA_SIZE = MAX_UDP_PAYLOAD - HEADER_SIZE


# --- Checksum utilities (simple 16-bit Internet-style checksum) ---

def _checksum16(data: bytes) -> int:
    """Compute a 16-bit checksum over the given bytes."""
    if len(data) % 2 == 1:
        data += b"\x00"

    s = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        s += word
        s = (s & 0xFFFF) + (s >> 16)  # fold carry

    # one's complement
    return (~s) & 0xFFFF


def build_packet(seq: int, flags: int, payload: bytes) -> bytes:
    """
    Build a packet with header + payload.
    seq: sequennee number (or ACK number for ACK packets)
    flags: one of FLAG_DATA/FLAG_ACK/FLAG_FIN/FLAG_FIN_ACK
    payload: bytes payload (empty for ACKs, FINs, etc.)
    """
    header_wo_checksum = struct.pack(HEADER_FORMAT, seq, flags, 0)
    checksum = _checksum16(header_wo_checksum + payload)
    header = struct.pack(HEADER_FORMAT, seq, flags, checksum)
    return header + payload


def parse_packet(raw: bytes) -> Tuple[int, int, bytes]:
    """
    Parse a raw UDP payoad into (seq, flags, payload).
    Raises ValueError if checksum is invalid or packet too short.
    """
    if len(raw) < HEADER_SIZE:
        raise ValueError("Packet too short")

    seq, flags, recv_checksum = struct.unpack(HEADER_FORMAT, raw[:HEADER_SIZE])
    payload = raw[HEADER_SIZE:]

    header_wo_checksum = struct.pack(HEADER_FORMAT, seq, flags, 0)
    calc_checksum = _checksum16(header_wo_checksum + payload)

    if calc_checksum != recv_checksum:
        raise ValueError("Bad checksum")

    return seq, flags, payload