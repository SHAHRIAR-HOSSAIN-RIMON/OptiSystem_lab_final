#!/usr/bin/env python3
"""Verify the archived OptiSystem TX/RX pairs and regenerate all Q statistics.

Usage:
    python scripts/reproduce_all.py
    python scripts/reproduce_all.py --root /path/to/repository

All Q values are waveform-derived statistical adjacent-level estimates.
They are not BER, and are not OptiSystem's built-in eye Q.
"""

from __future__ import annotations
import argparse
import csv
import hashlib
from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pam4_q import analyze  # noqa: E402


def write_csv(path: Path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def plot_sweep(rows, x_key, title, x_label, outfile):
    xs = [float(r[x_key]) for r in rows]
    ys = [float(r['q_min']) for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(xs, ys, marker='o', linewidth=1.8)
    for x, y in zip(xs, ys):
        ax.annotate(f'{y:.2f}', (x, y), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel('Estimated minimum PAM4 adjacent-level Q (dimensionless)')
    ax.set_xticks(xs)
    ax.grid(alpha=0.25)
    ax.margins(y=0.16)
    fig.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def run_all(root: Path = ROOT):
    root = Path(root).resolve()
    with (root / 'data' / 'manifest.csv').open(newline='', encoding='utf-8') as f:
        manifest = list(csv.DictReader(f))

    if len(manifest) != 9:
        raise ValueError(f'Expected 9 unique runs; manifest has {len(manifest)}')

    result_rows = []
    for row in manifest:
        run_id = row['run_id']
        tx = root / row['tx_path']
        rx = root / row['rx_path']
        for fp, key in [(tx, 'tx_sha256'), (rx, 'rx_sha256')]:
            observed = hashlib.sha256(fp.read_bytes()).hexdigest()
            if observed != row[key]:
                raise ValueError(f'Input checksum mismatch: {fp.relative_to(root)}')

        result = analyze(tx, rx)
        q = result['qs']
        q_min = float(np.min(q))
        expected = float(row['expected_min_Q'])
        if abs(q_min - expected) > 0.00002:
            raise AssertionError(f'{run_id}: recomputed Q={q_min:.6f}, recorded Q={expected:.6f}')

        output = dict(
            run_id=run_id, sweep=row['sweep'], fiber_km=row['fiber_km'], cutoff_GHz=row['cutoff_GHz'],
            tx_sha256=row['tx_sha256'], rx_sha256=row['rx_sha256'],
            tx_samples=result['samples'], symbols_retained=result['symbols'],
            rx_offset_samples=result['offset'], rx_offset_ps=f"{result['offset'] * result['dt'] * 1e12:.6f}",
            q_0_1=f'{q[0]:.6f}', q_1_2=f'{q[1]:.6f}', q_2_3=f'{q[2]:.6f}',
            q_min=f'{q_min:.6f}', q_min_training=f"{float(result['tqs'].min()):.6f}",
            q_min_holdout=f"{float(result['vqs'].min()):.6f}",
        )
        result_rows.append(output)

        level_csv = []
        for i in range(4):
            level_csv.append({
                'PAM4_level':i,'n':int(result['counts'][i]),
                'mean_received_amplitude_input_units':f"{result['mu'][i]:.15g}",
                'std_received_amplitude_input_units':f"{result['sd'][i]:.15g}",
                'q_to_next_level':f'{q[i]:.6f}' if i < 3 else '',
            })
        write_csv(root / 'results' / 'per_run' / f'{run_id}_levels.csv',
                  level_csv, list(level_csv[0]))

        fig, ax = plt.subplots(figsize=(6.5,4))
        ax.bar(['Level 0–1','Level 1–2','Level 2–3'], q)
        ax.set_title(f'{row["fiber_km"]} km SMF, {row["cutoff_GHz"]} GHz Bessel cutoff')
        ax.set_ylabel('Adjacent-level Q estimate (dimensionless)')
        ax.grid(axis='y', alpha=0.22)
        for i, v in enumerate(q):
            ax.annotate(f'{v:.2f}', (i, float(v)), xytext=(0,3), textcoords='offset points', ha='center')
        ax.set_ylim(0, max(q)*1.15)
        fig.tight_layout()
        fig.savefig(root / 'results' / 'per_run' / f'{run_id}_Q.png', dpi=170)
        plt.close(fig)
        print(f'{run_id}: Q_min={q_min:.6f}; verified against recorded value')

    cols = list(result_rows[0])
    write_csv(root / 'results' / 'summary' / 'all_runs.csv', result_rows, cols)
    fiber = sorted([r for r in result_rows if r['sweep']=='fiber'],key=lambda r:float(r['fiber_km']))
    bandwidth = sorted([r for r in result_rows if r['sweep']=='bandwidth'],key=lambda r:float(r['cutoff_GHz']))
    shared = next(r for r in fiber if float(r['fiber_km'])==10)
    bandwidth.append(dict(shared, sweep='bandwidth'))
    bandwidth.sort(key=lambda r:float(r['cutoff_GHz']))

    write_csv(root / 'results' / 'summary' / 'fiber_sweep.csv', fiber, cols)
    write_csv(root / 'results' / 'summary' / 'bandwidth_sweep.csv', bandwidth, cols)
    plot_sweep(fiber, 'fiber_km', 'PAM4 at 7.5 GHz: Fiber-Length Sweep',
               'Single-mode fiber length (km)', root / 'results' / 'figures' / 'fiber_sweep_Q.png')
    plot_sweep(bandwidth, 'cutoff_GHz', 'PAM4 at 10 km: Receiver-Bandwidth Sweep',
               '4th-order Bessel low-pass cutoff (GHz)',root / 'results' / 'figures' / 'bandwidth_sweep_Q.png')
    print('\nAll 9 unique raw-data pairs reproduced. Five points per comparison graph.')
    return result_rows

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    args = p.parse_args()
    run_all(args.root)
