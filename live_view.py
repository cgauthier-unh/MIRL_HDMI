#!/usr/bin/env python3
"""
Live viewer for a 3-column text file that:
  - is continuously appended during the day
  - resets at midnight: time column goes back to 0 AND the file is overwritten/truncated
  - columns: time_seconds, x, y
  - fixed sampling rate: 10 Hz

Displays (over a trailing user window):
  - X and Y time series
  - X and Y spectrograms

Dependencies:
  pip install numpy matplotlib scipy

  How to run:
  python live_view.py /path/to/yourfile.txt --window 600 --poll 0.25 --fmax 5
"""

import argparse
import os
import time as time_module
from collections import deque

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram


FS = 10.0  # Hz (given)
DT = 1.0 / FS


def safe_float(s: str):
    try:
        return float(s)
    except Exception:
        return None


def read_new_lines(fp, carryover: str):
    """
    Read newly appended text from fp and return list of complete lines.
    carryover keeps partial line fragments between reads.
    """
    chunk = fp.read()
    if not chunk:
        return [], carryover

    text = carryover + chunk
    lines = text.splitlines(keepends=False)

    # If chunk didn't end in newline, last line might be partial
    if not (chunk.endswith("\n") or chunk.endswith("\r\n")):
        carryover = lines[-1] if lines else carryover
        lines = lines[:-1]
    else:
        carryover = ""

    return lines, carryover


def parse_rows(lines):
    """
    Parse lines into arrays (t, x, y). Skips blank/comment/malformed lines.
    """
    t_list, x_list, y_list = [], [], []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        t = safe_float(parts[0])
        x = safe_float(parts[1])
        y = safe_float(parts[2])
        if t is None or x is None or y is None:
            continue
        t_list.append(t)
        x_list.append(x)
        y_list.append(y)

    if not t_list:
        return None
    return np.asarray(t_list), np.asarray(x_list), np.asarray(y_list)


def compute_spec(sig, fs, nperseg, noverlap):
    f, tt, Sxx = spectrogram(
        sig,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        detrend=False,
        scaling="density",
        mode="psd",
    )
    Sxx_db = 10.0 * np.log10(Sxx + 1e-20)
    return f, tt, Sxx_db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="Path to the 3-column file being updated")
    ap.add_argument("--window", type=float, default=300.0, help="Trailing window to display (seconds)")
    ap.add_argument("--poll", type=float, default=0.25, help="Polling interval (seconds)")
    ap.add_argument("--nperseg", type=int, default=256, help="Spectrogram segment length (samples)")
    ap.add_argument("--overlap", type=float, default=0.75, help="Spectrogram overlap fraction (0-0.99)")
    ap.add_argument("--fmax", type=float, default=None, help="Max frequency to show (Hz)")
    ap.add_argument("--max-points", type=int, default=500000, help="Safety cap on stored points")
    ap.add_argument("--start-at-end", action="store_true",
                    help="If set, begin by tailing only new data appended after start.")
    args = ap.parse_args()

    path = args.file
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # Rolling buffers
    tbuf = deque()
    xbuf = deque()
    ybuf = deque()

    # For detecting truncation/overwrite + midnight reset
    last_inode = None
    last_size = None
    last_t_seen = None

    def open_file():
        fp_local = open(path, "r", encoding="utf-8", errors="replace")
        if args.start_at_end:
            fp_local.seek(0, os.SEEK_END)
        return fp_local

    fp = open_file()
    carry = ""

    # --- Plot setup ---
    plt.ion()
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.35, wspace=0.25)

    ax_tx = fig.add_subplot(gs[0, 0])
    ax_ty = fig.add_subplot(gs[0, 1])
    ax_sx = fig.add_subplot(gs[1, 0])
    ax_sy = fig.add_subplot(gs[1, 1])

    (ln_x,) = ax_tx.plot([], [], linewidth=1)
    (ln_y,) = ax_ty.plot([], [], linewidth=1)

    ax_tx.set_title("X time series (trailing window)")
    ax_ty.set_title("Y time series (trailing window)")
    ax_tx.set_xlabel("Time (s since midnight)")
    ax_ty.set_xlabel("Time (s since midnight)")
    ax_tx.set_ylabel("X")
    ax_ty.set_ylabel("Y")

    ax_sx.set_title("X spectrogram (dB)")
    ax_sy.set_title("Y spectrogram (dB)")
    ax_sx.set_xlabel("Time (s since midnight)")
    ax_sy.set_xlabel("Time (s since midnight)")
    ax_sx.set_ylabel("Frequency (Hz)")
    ax_sy.set_ylabel("Frequency (Hz)")

    im_sx = ax_sx.imshow(np.zeros((10, 10)), origin="lower", aspect="auto",
                         extent=[0, 1, 0, 1], interpolation="nearest")
    im_sy = ax_sy.imshow(np.zeros((10, 10)), origin="lower", aspect="auto",
                         extent=[0, 1, 0, 1], interpolation="nearest")

    cbar_sx = fig.colorbar(im_sx, ax=ax_sx, pad=0.01)
    cbar_sy = fig.colorbar(im_sy, ax=ax_sy, pad=0.01)
    cbar_sx.set_label("dB")
    cbar_sy.set_label("dB")

    def autoscale_y(ax, data):
        dmin = np.nanmin(data)
        dmax = np.nanmax(data)
        if not (np.isfinite(dmin) and np.isfinite(dmax)):
            return
        if dmin == dmax:
            pad = 1.0 if dmin == 0 else abs(dmin) * 0.1
        else:
            pad = (dmax - dmin) * 0.05
        ax.set_ylim(dmin - pad, dmax + pad)

    last_draw = 0.0

    try:
        while True:
            # --- Detect overwrite/truncate/rotation ---
            try:
                st = os.stat(path)
                inode = getattr(st, "st_ino", None)
                size = st.st_size
            except FileNotFoundError:
                # brief window during rewrite; retry
                time_module.sleep(args.poll)
                continue

            if last_inode is None:
                last_inode = inode
                last_size = size

            # If inode changes OR file shrinks: file replaced/overwritten/truncated -> reopen + reset buffers
            if (inode is not None and inode != last_inode) or (last_size is not None and size < last_size):
                fp.close()
                fp = open_file()
                carry = ""
                tbuf.clear(); xbuf.clear(); ybuf.clear()
                last_t_seen = None
                last_inode = inode
                last_size = size

            last_size = size

            # --- Read newly appended lines ---
            new_lines, carry = read_new_lines(fp, carry)
            parsed = parse_rows(new_lines) if new_lines else None

            if parsed is not None:
                t_new, x_new, y_new = parsed

                # Detect midnight reset even if file wasn't truncated (belt + suspenders):
                # If time drops sharply (e.g., from near 86400 to small), clear buffers.
                # We use the last parsed time token, not the last buffered (same idea).
                if last_t_seen is not None and len(t_new) > 0:
                    if t_new[0] < last_t_seen - 1.0:  # 1 second hysteresis
                        tbuf.clear(); xbuf.clear(); ybuf.clear()

                # Append
                for ti, xi, yi in zip(t_new, x_new, y_new):
                    tbuf.append(float(ti))
                    xbuf.append(float(xi))
                    ybuf.append(float(yi))
                    last_t_seen = float(ti)

                # Safety cap
                while len(tbuf) > args.max_points:
                    tbuf.popleft(); xbuf.popleft(); ybuf.popleft()

                # Keep only trailing window based on time since midnight
                if tbuf:
                    t_latest = tbuf[-1]
                    t_min = max(0.0, t_latest - args.window)
                    while tbuf and tbuf[0] < t_min:
                        tbuf.popleft(); xbuf.popleft(); ybuf.popleft()

            # --- Redraw ---
            now = time_module.time()
            if (now - last_draw) >= max(args.poll, 0.1) and len(tbuf) >= 8:
                t = np.asarray(tbuf, dtype=float)
                x = np.asarray(xbuf, dtype=float)
                y = np.asarray(ybuf, dtype=float)

                # In-case of occasional out-of-order writes: sort by time within window
                if np.any(np.diff(t) < 0):
                    idx = np.argsort(t)
                    t, x, y = t[idx], x[idx], y[idx]

                # Time series
                ln_x.set_data(t, x)
                ln_y.set_data(t, y)
                ax_tx.set_xlim(t[0], t[-1])
                ax_ty.set_xlim(t[0], t[-1])
                autoscale_y(ax_tx, x)
                autoscale_y(ax_ty, y)

                # Spectrograms use fixed FS (10 Hz) -> no estimation risk
                noverlap = int(args.nperseg * float(args.overlap))
                noverlap = max(0, min(noverlap, args.nperseg - 1))

                # Need enough samples for spectrogram window
                if len(x) >= args.nperseg:
                    fx, tx_rel, Sx = compute_spec(x, FS, args.nperseg, noverlap)
                    fy, ty_rel, Sy = compute_spec(y, FS, args.nperseg, noverlap)

                    # Convert spec time to absolute (seconds since midnight)
                    t0 = t[0]
                    tx_abs = t0 + tx_rel
                    ty_abs = t0 + ty_rel

                    # Optional fmax
                    def apply_fmax(f, S):
                        if args.fmax is None:
                            return f, S
                        m = f <= args.fmax
                        return f[m], S[m, :]

                    fx2, Sx2 = apply_fmax(fx, Sx)
                    fy2, Sy2 = apply_fmax(fy, Sy)

                    if tx_abs.size >= 2 and fx2.size >= 2:
                        im_sx.set_data(Sx2)
                        im_sx.set_extent([tx_abs[0], tx_abs[-1], fx2[0], fx2[-1]])
                        ax_sx.set_xlim(t[0], t[-1])
                        ax_sx.set_ylim(fx2[0], fx2[-1])
                        im_sx.autoscale()

                    if ty_abs.size >= 2 and fy2.size >= 2:
                        im_sy.set_data(Sy2)
                        im_sy.set_extent([ty_abs[0], ty_abs[-1], fy2[0], fy2[-1]])
                        ax_sy.set_xlim(t[0], t[-1])
                        ax_sy.set_ylim(fy2[0], fy2[-1])
                        im_sy.autoscale()

                fig.canvas.draw_idle()
                plt.pause(0.001)
                last_draw = now

            time_module.sleep(args.poll)

    except KeyboardInterrupt:
        pass
    finally:
        try:
            fp.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
