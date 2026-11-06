"""Reproducible PAM4 adjacent-level statistical Q estimates from OptiSystem exports.

Usage (requires numpy, matplotlib):
    python PAM4_analyze_waveforms.py data.txt recieved.txt --fiber-km 5 --cutoff-ghz 7.5

Both files must be exported from the SAME OptiSystem calculation:
    TX oscilloscope (PAM Pulse Generator): Signal > Signal Amplitude > Single Pair
    RX oscilloscope (after Bessel filter): Signal+Noise > Signal + Noise Amplitude > Single Pair

The resulting Q values are dimensionless, reference-labelled adjacent-level
statistical separation estimates, NOT BER and NOT OptiSystem built-in eye Q.
The time-series is short, so results are preliminary. TX and RX timestamps
must be identical, and a record of simulation parameters must be saved separately.
"""
from pathlib import Path
import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt

BIT_RATE = 25e9
BITS_PER_SYMBOL = 2
EDGE_SYMBOLS = 8


def analyze(txfile, rxfile):
    tx = np.loadtxt(txfile)
    rx = np.loadtxt(rxfile)
    if tx.ndim != 2 or rx.ndim != 2 or tx.shape != rx.shape or tx.shape[1] != 2:
        raise ValueError('TX and RX must be two-column time/amplitude exports of equal shape')
    if not np.allclose(tx[:, 0], rx[:, 0], atol=1e-16, rtol=1e-9):
        raise ValueError('TX and RX have mismatched time coordinates. Export from the same run.')
    if not np.all(np.isfinite(tx)) or not np.all(np.isfinite(rx)):
        raise ValueError('Non-finite waveform value')

    dt = float(np.median(np.diff(tx[:, 0])))
    if dt <= 0 or not np.allclose(np.diff(tx[:, 0]), dt, atol=1e-17, rtol=2e-4):
        raise ValueError('Time samples must be uniformly spaced')
    sps = round((BITS_PER_SYMBOL / BIT_RATE) / dt)
    if abs(sps * dt - BITS_PER_SYMBOL / BIT_RATE) > 0.001 * BITS_PER_SYMBOL / BIT_RATE:
        raise ValueError('Unrecognized symbol duration / sample rate')
    nsym = len(tx) // sps
    symbols = np.arange(EDGE_SYMBOLS, nsym - EDGE_SYMBOLS)
    if len(symbols) < 64:
        raise ValueError('Not enough PAM4 symbols for analysis')
    ideal = tx[symbols * sps + sps//2, 1]
    labels = np.rint(3 * ideal).astype(int)
    if not np.all(np.isin(labels, [0,1,2,3])) or not np.allclose(ideal, labels / 3, atol=1e-4):
        raise ValueError('TX file is not the expected PAM4 mapping 0,1/3,2/3,1')
    train = symbols < nsym // 2
    val = ~train

    def stats(samples, mask):
        m, sd, counts = [], [], []
        for level in range(4):
            x = samples[mask & (labels == level)]
            if len(x) < 2:
                raise ValueError(f'Too few observations at level {level}')
            m.append(x.mean()); sd.append(x.std(ddof=1)); counts.append(len(x))
        m = np.array(m); sd = np.array(sd)
        q = np.diff(m)/(sd[:-1] + sd[1:])
        return m, sd, q, counts

    # The same deterministic calibration rule is used for ALL experimental runs.
    # Optimize the minimum training-half Q over 0 to <2 symbol durations,
    # then evaluate this chosen timing on the unseen second half.
    trials = []
    for ofs in range(2*sps):
        inds = symbols*sps + ofs
        if inds.max() >= len(rx):
            continue
        _,_,q,_ = stats(rx[inds,1],train)
        trials.append((float(q.min()),-ofs, ofs))
    if not trials:
        raise ValueError('Cannot find a valid receive timing offset')
    offset = max(trials)[2]
    sampled = rx[symbols*sps + offset,1]
    all_mask = np.ones(len(symbols),bool)
    mu, sd, qs, count = stats(sampled,all_mask)
    _, _, vqs, _ = stats(sampled,val)
    _, _, tqs, _ = stats(sampled,train)
    return dict(mu=mu,sd=sd,qs=qs,counts=count,tqs=tqs,vqs=vqs,offset=offset,
                samples=len(tx),symbols=len(symbols),sps=sps,dt=dt,
                train_count=int(train.sum()),validation_count=int(val.sum()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('txfile',type=Path)
    p.add_argument('rxfile',type=Path)
    p.add_argument('--fiber-km',type=float,required=True)
    p.add_argument('--cutoff-ghz',type=float,required=True)
    p.add_argument('--output-dir',type=Path,default=Path('.'))
    args=p.parse_args()
    r=analyze(args.txfile,args.rxfile)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    tag=f'{args.fiber_km:g}km_{args.cutoff_ghz:g}GHz'
    csvpath=args.output_dir/f'{tag}_PAM4_Q_statistics.csv'
    with csvpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['Fiber_km','Cutoff_GHz','PAM4_level','Number_of_symbols','Mean_amplitude_micro_au','Std_amplitude_micro_au','Q_to_next_level'])
        for i in range(4):
            w.writerow([args.fiber_km,args.cutoff_ghz,i,r['counts'][i],
                        f'{r["mu"][i]*1e6:.9f}',f'{r["sd"][i]*1e6:.9f}',
                        f'{r["qs"][i]:.6f}' if i<3 else ''])
    pngpath=args.output_dir/f'{tag}_PAM4_Q_figure.png'
    fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(['Lower','Middle','Upper'],r['qs'])
    for i,v in enumerate(r['qs']):
        ax.text(i,float(v)+float(r['qs'].max())*.02,f'{v:.2f}',ha='center',va='bottom')
    ax.set_ylim(0,float(r['qs'].max())*1.16)
    ax.set_ylabel('Statistical adjacent-level Q (dimensionless)')
    ax.set_xlabel('Adjacent PAM4 levels')
    ax.set_title(f'PAM4: fiber {args.fiber_km:g} km, Bessel cutoff {args.cutoff_ghz:g} GHz')
    ax.grid(axis='y',alpha=.2)
    fig.tight_layout()
    fig.savefig(pngpath,dpi=180)
    plt.close(fig)
    print(f'TX file: {args.txfile}\nRX file: {args.rxfile}')
    print(f'Samples: {r["samples"]:,} | Symbols retained: {r["symbols"]} | Samples/symbol: {r["sps"]}')
    print(f'RX timing offset: {r["offset"]} samples ({r["offset"]*r["dt"]*1e12:.2f} ps)')
    for i in range(4):
        print(f'Level {i}: N={r["counts"][i]}, mean={r["mu"][i]*1e6:.4f} µa.u., std={r["sd"][i]*1e6:.4f} µa.u.')
    print('Adjacent Q:',*[f'{x:.4f}' for x in r['qs']])
    print(f'Minimum Q (all): {r["qs"].min():.5f} | train: {r["tqs"].min():.5f} | held out: {r["vqs"].min():.5f}')
    print('CAUTION: Statistical Q estimate only; not BER, not built-in Q; needs longer/repeated trials.')
    print('Saved:',csvpath,pngpath)

if __name__ == '__main__':
    main()
