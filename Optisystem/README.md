# OptiSystem PAM4 Optical Link — Reproducible Q Estimation

**Simulation:** 25 Gb/s (12.5 Gbaud) PAM4 intensity-modulation/direct-detection optical link, modeled in OptiSystem 23.1.

**Purpose:** Analyze the effect of SMF length and receiver low-pass cutoff frequency on the *estimated minimum adjacent-level statistical Q* of a PAM4 waveform. This repository provides original exported time-amplitude traces, Python source, a Colab notebook, numeric results, and comparison figures.

> **Important limitation:** The Q values here are offline, reference-labelled, waveform-derived **statistical separation estimates**; they are **not OptiSystem's built-in Q-factor**, **not measured BER**, and **not an experimentally validated link error rate**. The record has 1024 bits and is too short to establish rare-error performance.

## Experiments and results

Each simulation uses a **25 Gb/s PAM4 (12.5 Gbaud)** sequence with **1024 bits** and **32 samples/bit** (32,768 waveform time samples). All runs retain **496 of 512 symbols** after excluding 8 on each edge. The receiver is a **4th-order Bessel low-pass filter**. The fiber sweep holds the cutoff at 7.5 GHz; the bandwidth sweep holds SMF length at 10 km. There are **nine distinct TX/RX pairs**, because 10 km at 7.5 GHz is shared by both sweeps.

| SMF length, km | Estimated minimum Q (7.5 GHz) |
|---:|---:|
| 0 | 36.441916 |
| 5 | 16.138439 |
| 10 | 10.065295 |
| 15 | 7.735377 |
| 20 | 6.222313 |

| Bessel cutoff, GHz | Estimated minimum Q (10 km) |
|---:|---:|
| 6.5 | 7.084370 |
| 7.0 | 9.142238 |
| 7.5 | 10.065295 |
| 8.0 | 8.494848 |
| 8.5 | 8.013745 |

At these tested settings, the highest estimated Q occurs at 7.5 GHz cutoff for the 10 km link. **This is not a universal optimum**, and the individual TX symbol sequences differ across several experimental runs. Results are therefore descriptive rather than a controlled estimate of statistical significance.

## Open in Google Colab

1. After this repository has been uploaded to GitHub, open `notebooks/PAM4_Q_Analysis_Colab.ipynb` in Google Colab (Colab → File → Open notebook → GitHub).
2. Run the cells in order. The first setup cell clones this repository (public GitHub access is assumed); the next cells verify SHA-256 hashes and regenerate all data tables and graphs.
3. The notebook displays both graphs and the calculated Q values.

Alternative, **before publishing on GitHub**: download the whole ZIP and run locally as shown below. The notebook itself can also extract a manually uploaded ZIP when `SOURCE_MODE='zip'` is selected in its first code cell.

## Run locally

Requires Python 3.10+ with pip:

```bash
python -m pip install -r requirements.txt
python scripts/reproduce_all.py
```

The command checks every original waveform SHA-256 digest and fails if any recomputed Q differs by more than 0.00002 from the documented value. It regenerates:

- `results/summary/all_runs.csv`: all 9 unique TX/RX pairs, timing offsets, adjacent Q values, training Q and held-out Q
- `results/summary/fiber_sweep.csv`, `results/summary/bandwidth_sweep.csv`
- `results/figures/fiber_sweep_Q.png`, `results/figures/bandwidth_sweep_Q.png`
- `results/per_run/*_levels.csv` and `results/per_run/*_Q.png`

## Statistical method

For each received PAM4 level k=0,1,2,3 at the selected receiver sampling phase, calculate its conditional sample mean (μₖ) and sample standard deviation (σₖ). The transmitted waveform is used as the known reference to label the received symbols, not as a measured-error detector.

**Adjacent-level statistical Q:**

```text
Q_k = (mu[k+1] - mu[k]) / (sigma[k+1] + sigma[k]), k = 0, 1, 2
Q_min = min(Q_0, Q_1, Q_2)
```

**Receiver timing:** The 80 ps PAM4 symbol lasts 64 samples (1.25 ps/sample). The first and last 8 symbols are excluded. Candidate sampling offsets cover 0 to 127 samples (two symbol durations). The offset maximizing **minimum training-half Q** is selected using the first half of the retained symbols. The same offset is then used to report all-symbol Q and second-half (*held-out*) Q. This mitigates, but does not eliminate, selection bias. The primary tables report **all-symbol minimum Q**, matching the previously reported analysis; held-out values are separately disclosed.

**Limitations:** A short pattern, finite level sample counts, choice of timing search, variation in transmitted patterns, and noise/ISI together contribute to sampling spread. A high ratio does not prove low BER; no BER or confidence intervals were measured. PAM4 has three eyes; this analysis reports the **worst adjacent-level separation**, not a binary eye-diagram Q reported by an OptiSystem analyzer.

## Data provenance

`data/manifest.csv` maps each run to its original uploaded TX/RX filename and SHA-256 checksum. Each TXT file has **two numeric columns: time (s), amplitude (export native units)**. The original OptiSystem GUI export paths were:

- TX oscilloscope: `Signal → Signal Amplitude → Single Pair`
- RX oscilloscope: `Signal+Noise → Signal+Noise Amplitude → Single Pair`

The RX and TX files must be taken from the **same OptiSystem calculation** for the transmitted symbol sequence to label the received sequence. All nine archived pairings reproduce the recorded Q values. Filenames are normalized to `TX.txt` / `RX.txt` for clarity; original names are in the manifest. This repository does not itself contain an editable OptiSystem project/circuit file unless you add one separately.

## Suggested paper acknowledgement

> Data and analysis code: [repository URL]. PAM4 statistical Q estimates were computed offline in Python from exported OptiSystem transmitter and receiver waveforms. No BER measurement or built-in OptiSystem Q-factor measurement was performed.

The GitHub repository is **not** an online publication until its files have actually been uploaded.
