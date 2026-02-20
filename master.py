#!/usr/bin/env python3
"""
RSE3204 Wireless Localisation - MASTER (Pi A)
=============================================
Run this on Pi A.
It:
  1. Asks the operator to enter dXA (Pi A → Bluetooth device distance)
  2. Asks the operator to enter dAB (Pi A → Pi B baseline distance)
  3. Sends a GET_DISTANCE request to Slave (Pi B) over UART
  4. Receives dXB from Pi B over UART
  5. Computes θAB using the Law of Cosines
  6. Prints a formatted summary table

Usage:
    sudo python3 master.py

Requirements:
    pip install pyserial
"""

import serial
import json
import math

# ── UART Configuration ─────────────────────────────────────────────────────────
UART_PORT     = "/dev/serial0"
UART_BAUDRATE = 9600
UART_TIMEOUT  = 60        # seconds to wait for slave response

# ── Distance helpers ───────────────────────────────────────────────────────────

def prompt_distance(label: str) -> float:
    """Prompt operator for a distance value."""
    while True:
        try:
            val = float(input(f"[Master] Enter {label} (metres): "))
            if val < 0:
                print("  Distance cannot be negative. Try again.")
                continue
            return val
        except ValueError:
            print("  Invalid input. Please enter a number.")


# ── UART communication ─────────────────────────────────────────────────────────

def fetch_dxb_from_slave(uart: serial.Serial) -> float:
    """Send GET_DISTANCE request over UART and wait for dXB response."""
    request = json.dumps({"cmd": "GET_DISTANCE"}) + "\n"
    print("[Master] Sending GET_DISTANCE request to slave over UART …")
    uart.write(request.encode())
    uart.flush()

    print("[Master] Waiting for slave response …")
    raw = uart.readline()

    if not raw:
        raise TimeoutError("No response from slave. Check UART wiring and that slave.py is running.")

    response = json.loads(raw.decode().strip())

    if "error" in response:
        raise RuntimeError(f"Slave returned error: {response['error']}")

    dxb = float(response["dxb"])
    print(f"[Master] Received dXB = {dxb:.3f} m from slave.")
    return dxb


# ── Geometry ───────────────────────────────────────────────────────────────────

def compute_angle(dxa: float, dxb: float, dab: float):
    """
    Compute θAB (angle at vertex X) using the Law of Cosines:

        cos(θAB) = (dXA² + dXB² - dAB²) / (2 · dXA · dXB)

    Returns angle in degrees, or None if degenerate.
    """
    if dxa == 0 or dxb == 0:
        return None

    cos_theta = (dxa**2 + dxb**2 - dab**2) / (2 * dxa * dxb)
    cos_theta = max(-1.0, min(1.0, cos_theta))   # clamp for floating-point safety
    return math.degrees(math.acos(cos_theta))


def validate_triangle(dxa: float, dxb: float, dab: float) -> bool:
    """Triangle inequality check."""
    return (dxa + dxb > dab) and (dxa + dab > dxb) and (dxb + dab > dxa)


# ── Display ────────────────────────────────────────────────────────────────────

def print_results(dxa: float, dxb: float, dab: float, theta):
    sep = "═" * 46
    print(f"\n  ╔{sep}╗")
    print(f"  ║{'RSE3204 — Localisation Results':^46}║")
    print(f"  ╠{sep}╣")
    print(f"  ║  {'dXA  (Pi A → Bluetooth device)':<38} {dxa:>5.3f} m  ║")
    print(f"  ║  {'dXB  (Pi B → Bluetooth device)':<38} {dxb:>5.3f} m  ║")
    print(f"  ║  {'dAB  (Pi A → Pi B baseline)':<38} {dab:>5.3f} m  ║")
    print(f"  ╠{sep}╣")
    if theta is not None:
        print(f"  ║  {'θAB  (angle at device X)':<38} {theta:>5.2f} °  ║")
    else:
        print(f"  ║  {'θAB  (angle at device X)':<38} {'N/A':>7}  ║")
    print(f"  ╚{sep}╝")

    # ASCII triangle diagram
    print("\n  Triangle layout (not to scale):\n")
    print("        Pi A")
    print("         |\\")
    print(f"   dXA={dxa:.2f}m |  \\ dAB={dab:.2f}m")
    print("         |    \\")
    print("    device X----Pi B")
    print(f"        dXB={dxb:.2f}m")
    if theta is not None:
        print(f"\n  θAB (angle at device X) = {theta:.2f}°")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def run_master():
    print("=" * 50)
    print("  RSE3204 Wireless Localisation — MASTER (Pi A)")
    print("=" * 50)

    # Step 1: Get local distances from operator
    dxa = prompt_distance("dXA  [Pi A → Bluetooth device]")
    dab = prompt_distance("dAB  [Pi A → Pi B baseline]")

    # Step 2: Open UART and fetch dXB from slave
    print(f"\n[Master] Opening UART on {UART_PORT} at {UART_BAUDRATE} baud …")
    with serial.Serial(UART_PORT, UART_BAUDRATE, timeout=UART_TIMEOUT) as uart:
        dxb = fetch_dxb_from_slave(uart)

    # Step 3: Validate triangle
    if not validate_triangle(dxa, dxb, dab):
        print("\n  ⚠  WARNING: Distances do not form a valid triangle.")
        print("     θAB cannot be computed. Check your measurements.\n")
        theta = None
    else:
        theta = compute_angle(dxa, dxb, dab)

    # Step 4: Display results
    print_results(dxa, dxb, dab, theta)


if __name__ == "__main__":
    try:
        run_master()
    except KeyboardInterrupt:
        print("\n[Master] Stopped.")
    except serial.SerialException as e:
        print(f"\n[Master] UART error: {e}")
        print("  Make sure UART is enabled (raspi-config) and you are running with sudo.")
    except TimeoutError as e:
        print(f"\n[Master] Timeout: {e}")
    except Exception as e:
        print(f"\n[Master] Error: {e}")