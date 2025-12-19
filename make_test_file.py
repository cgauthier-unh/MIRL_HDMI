#!/usr/bin/env python3
"""
Test data generator for the live viewer.

Creates/overwrites an output file and then continuously appends 3-column rows:
  time_seconds_since_midnight   x   y

- Fixed sample rate (default 10 Hz)
- Optional "midnight" reset simulation: periodically truncates the file and resets time to 0

Run this in one terminal, and the live viewer in another.

python make_test_file.py /tmp/live_test.txt --fs 10 --noise 0.08 --reset-every 120 --flush
"""

import argparse
import math
import os
import random
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outfile", help="Path to write the test file")
    ap.add_argument("--fs", type=float, default=10.0, help="Sampling rate (Hz)")
    ap.add_argument("--noise", type=float, default=0.05, help="Gaussian noise std dev")
    ap.add_argument("--reset-every", type=float, default=0.0,
                    help="If >0, simulate midnight reset by truncating file every N seconds")
    ap.add_argument("--flush", action="store_true",
                    help="Flush and fsync each write (slower, but closer to crash-safe logging)")
    ap.add_argument("--seed", type=int, default=0, help="Random seed (0 -> time-based)")
    args = ap.parse_args()

    fs = float(args.fs)
    if fs <= 0:
        raise ValueError("--fs must be > 0")
    dt = 1.0 / fs

    if args.seed == 0:
        random.seed()
    else:
        random.seed(args.seed)

    # Some changing tones to make the spectrogram interesting
    f1x, f2x = 0.6, 1.8   # Hz
    f1y, f2y = 0.9, 2.4   # Hz

    # Start fresh
    os.makedirs(os.path.dirname(os.path.abspath(args.outfile)), exist_ok=True)
    with open(args.outfile, "w", encoding="utf-8") as f:
        f.write("# t_sec  x  y\n")

    t0_wall = time.time()
    last_reset_wall = t0_wall
    t_sec = 0.0

    # Open once and keep appending (more like a real logger)
    f = open(args.outfile, "a", encoding="utf-8")

    try:
        while True:
            now_wall = time.time()

            # Simulate "midnight" reset (truncate + restart time)
            if args.reset_every and (now_wall - last_reset_wall) >= args.reset_every:
                f.close()
                with open(args.outfile, "w", encoding="utf-8") as g:
                    g.write("# t_sec  x  y\n")
                f = open(args.outfile, "a", encoding="utf-8")
                t_sec = 0.0
                last_reset_wall = now_wall

            # Slowly sweep between two frequencies to create bands in spectrogram
            sweep = 0.5 * (1.0 + math.sin(2.0 * math.pi * 0.01 * t_sec))  # very slow 0.01 Hz sweep
            fx = f1x * (1.0 - sweep) + f2x * sweep
            fy = f1y * (1.0 - sweep) + f2y * sweep

            x = math.sin(2.0 * math.pi * fx * t_sec) + 0.4 * math.sin(2.0 * math.pi * 0.2 * t_sec)
            y = math.cos(2.0 * math.pi * fy * t_sec) + 0.3 * math.sin(2.0 * math.pi * 0.35 * t_sec)

            # Add noise
            x += random.gauss(0.0, args.noise)
            y += random.gauss(0.0, args.noise)

            f.write(f"{t_sec:.3f} {x:.6f} {y:.6f}\n")

            if args.flush:
                f.flush()
                os.fsync(f.fileno())

            # Advance "sensor time" at fs
            t_sec += dt

            # Sleep to approximate real-time production
            # Use dt, but don't assume perfect scheduling
            time.sleep(dt)

    except KeyboardInterrupt:
        pass
    finally:
        try:
            f.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
