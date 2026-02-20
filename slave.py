#!/usr/bin/env python3
"""
RSE3204 Wireless Localisation - SLAVE (Pi B)
=============================================
Run this on Pi B.
Waits for a request from master over UART, then prompts
operator to enter dXB and sends it back over UART.

Usage:
    sudo python3 slave.py

Requirements:
    pip install pyserial
"""

import serial
import json

# ── UART Configuration ─────────────────────────────────────────────────────────
UART_PORT     = "/dev/serial0"
UART_BAUDRATE = 9600
UART_TIMEOUT  = 30        # seconds to wait for a message

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_distance_from_user() -> float:
    """Prompt the operator to enter dXB manually."""
    while True:
        try:
            val = float(input("[Slave] Enter distance from Pi B to Bluetooth device (metres): "))
            if val < 0:
                print("  Distance cannot be negative. Try again.")
                continue
            return val
        except ValueError:
            print("  Invalid input. Please enter a number.")


def run_slave():
    print("=" * 50)
    print("  RSE3204 Wireless Localisation — SLAVE (Pi B)")
    print("=" * 50)
    print(f"[Slave] Opening UART on {UART_PORT} at {UART_BAUDRATE} baud …")

    with serial.Serial(UART_PORT, UART_BAUDRATE, timeout=UART_TIMEOUT) as uart:
        print("[Slave] UART ready. Waiting for master request …\n")

        while True:
            # ── Wait for a line from master ────────────────────────────────────
            raw = uart.readline()           # blocks until '\n' or timeout
            if not raw:
                print("[Slave] Timeout waiting for master. Still waiting …")
                continue

            try:
                request = json.loads(raw.decode().strip())
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"[Slave] Bad data received: {e}. Ignoring.")
                continue

            print(f"[Slave] Request received: {request}")

            if request.get("cmd") == "GET_DISTANCE":
                # ── Get dXB from operator ──────────────────────────────────────
                dxb = get_distance_from_user()

                # ── Send response back to master ───────────────────────────────
                response = json.dumps({"dxb": dxb}) + "\n"
                uart.write(response.encode())
                uart.flush()
                print(f"[Slave] Sent dXB = {dxb:.3f} m to master.\n")
                print("[Slave] Waiting for next request …\n")

            else:
                error = json.dumps({"error": "unknown command"}) + "\n"
                uart.write(error.encode())
                uart.flush()
                print("[Slave] Unknown command. Sent error to master.")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run_slave()
    except KeyboardInterrupt:
        print("\n[Slave] Stopped.")
    except serial.SerialException as e:
        print(f"\n[Slave] UART error: {e}")
        print("  Make sure UART is enabled (raspi-config) and you are running with sudo.")