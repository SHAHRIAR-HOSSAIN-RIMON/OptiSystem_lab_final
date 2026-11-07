# Statistical Q-Factor Evaluation of a 25-Gb/s PAM4 Optical Link

This repository provides the **OptiSystem 23.1 waveform exports**, Python analysis code, and numerical results for a 25-Gb/s (12.5-Gbaud) four-level pulse-amplitude-modulation (PAM4) intensity-modulation/direct-detection (IM–DD) optical link. Two parameter sweeps are evaluated: single-mode fiber (SMF) length and electrical receiver low-pass cutoff frequency.

**Research scope.** The reported metric is an **offline, reference-labelled adjacent-level statistical Q estimate** derived from transmitted and received time-domain waveforms. It is not the OptiSystem BER analyzer's Q factor, a measured bit-error rate, or an estimate of extremely low error probabilities. The work does not implement machine learning.

## Experimental conditions

| Parameter | Configuration |
|---|---|
| Modulation | PAM4, 2 bits/symbol |
| Information rate | 25 Gb/s (12.5 Gbaud) |
| Optical carrier | 1550 nm, 0 dBm |
| Transmitter | PRBS/PAM4 source and analytical Mach–Zehnder modulator |
| Fiber | Single-mode, 0.2 dB/km attenuation, 16.75 ps/(nm·km) dispersion |
| Receiver | PIN photodiode and 4th-order Bessel electrical low-pass filter |
| Simulation record | 1024 bits, 32 samples/bit (32,768 time samples) |
| Evaluated symbols | 496 of 512; eight symbols excluded at each record edge |

The fiber-length sweep uses **0, 5, 10, 15, and 20 km** at a fixed **7.5-GHz** filter cutoff. The filter-cutoff sweep uses **6.5, 7.0, 7.5, 8.0, and 8.5 GHz** at a fixed **10-km** fiber length. The 10-km/7.5-GHz condition is shared; there are nine unique TX/RX waveform pairs.

## Numerical results

| Fiber length (km), 7.5 GHz cutoff | Minimum statistical Q |
|---:|---:|
| 0 | 36.441916 |
| 5 | 16.138439 |
| 10 | 10.065295 |
| 15 | 7.735377 |
| 20 | 6.222313 |

| Bessel cutoff (GHz), 10 km SMF | Minimum statistical Q |
|---:|---:|
| 6.5 | 7.084370 |
| 7.0 | 9.142238 |
| 7.5 | 10.065295 |
| 8.0 | 8.494848 |
| 8.5 | 8.013745 |

The minimum statistical Q decreases with increasing fiber length in the evaluated sweep. Among the *tested* receiver cutoffs, 7.5 GHz yields the largest estimated Q at 10 km. These comparisons do not establish a globally optimal filter cutoff.

## Reproduce in Google Colab

[**Open the analysis notebook in Google Colab**](https://colab.research.google.com/github/SHAHRIAR-HOSSAIN-RIMON/OptiSystem_lab_final/blob/main/Optisystem/notebooks/PAM4_Q_Analysis_Colab_FIXED.ipynb)

Select **Runtime → Run all**. The notebook loads the repository once per Colab session, locates the nested `Optisystem/` project directory, checks all source-file SHA-256 hashes, recomputes the Q estimates, and displays the numerical tables and figures. Re-running the notebook within the same session reuses the existing checkout; it does not attempt to clone over it.

Requirements: Python 3.10+, NumPy and Matplotlib. These libraries are normally available in Colab. For a local installation, use the package versions in `Optisystem/requirements.txt`.

## Reproduce locally

```bash
git clone https://github.com/SHAHRIAR-HOSSAIN-RIMON/OptiSystem_lab_final.git
cd OptiSystem_lab_final/Optisystem
python -m pip install -r requirements.txt
python scripts/reproduce_all.py
```

The verification fails if an input file's checksum differs from `data/manifest.csv` or if a recomputed full-record Q differs from the archived value by more than `2 × 10⁻⁵`.

## Analysis method

For each transmitted PAM4 level \(k \in \{0,1,2,3\}\), the synchronized received samples are grouped using the known transmitted reference symbols. The conditional mean \(\mu_k\) and sample standard deviation \(\sigma_k\) are computed. Adjacent-level separation is quantified by

\[
Q_k = \frac{\mu_{k+1}-\mu_k}{\sigma_{k+1}+\sigma_k}, \quad k=0,1,2, \qquad
Q_{\min}=\min(Q_0,Q_1,Q_2).
\]

The symbol duration is 80 ps (64 waveform samples). Eight edge symbols are excluded at each end. A receiver sampling offset within two symbol durations is selected by maximizing the minimum Q **on the first half** of the remaining symbols. The same offset is used to compute full-record Q and second-half (held-out) Q. The principal reported values use the complete 496-symbol analysis record; held-out estimates are provided as a sensitivity check.

Only 1024 transmitted bits are simulated per condition; the sequences vary between several of the runs, and no repeated-run uncertainty or independently validated BER is reported. The sampled level spread combines modeled noise, intersymbol interference, and waveform distortions. Consequently, the results should be interpreted as **descriptive, simulation-specific statistical separation estimates**.

## Repository structure

```text
README.md
Optisystem/
  notebooks/PAM4_Q_Analysis_Colab_FIXED.ipynb
  src/pam4_q.py
  scripts/reproduce_all.py
  requirements.txt
  data/manifest.csv
  data/waveforms/<run-id>/{TX,RX}.txt
  results/summary/{all_runs,fiber_sweep,bandwidth_sweep}.csv
  results/figures/{fiber_sweep_Q,bandwidth_sweep_Q}.png
  results/per_run/*
```

The `data/manifest.csv` file records the experimental configuration, original export filenames, and SHA-256 hashes for the nine TX/RX pairs. Individual waveforms contain time in seconds and amplitude in the units exported by OptiSystem.

The project includes waveform exports and offline analysis software; it does **not** include the editable OptiSystem schematic file. An independent reproduction of the original optical simulation requires that OptiSystem model and its parameter configuration.
