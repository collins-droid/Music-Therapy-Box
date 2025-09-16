"""
synthesize_hr_eda_dataset.py

Generates synthetic, physiologically plausible 60-second windows of:
 - HR (1 Hz, instantaneous bpm series)
 - EDA (eda_fs Hz, microsiemens)
Computes 15 features per window (your requested list) and outputs a CSV.

Requirements:
  pip install numpy scipy pandas tqdm

Optional (better SCR detection/EDA cleaning):
  pip install neurokit2
"""

import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.ndimage import gaussian_filter1d
from tqdm import tqdm

# ---------- PARAMETERS you can tweak ----------
N_WINDOWS = 1000            # total windows to generate
EDA_FS = 4                  # EDA sampling frequency (Hz)
WINDOW_SEC = 60
HR_FS = 1                   # we produce instantaneous HR at 1 Hz (bpm)
STRESS_RATIO = 0.5          # fraction windows labeled 'stress' (balanced by default)

# Physiological distributions (tweak to match your probe)
HR_BASE_MEAN = 68.0         # mean resting HR population (bpm)
HR_BASE_SD   = 6.0          # inter-subject baseline spread
HR_WITHIN_SD = 2.5          # within-window HR variability std (non-stress)
HRV_REDUCTION_ON_STRESS = 0.6  # multiply within-window variability by this under stress (HRV often reduces)
HR_STRESS_MEAN_INC = 8.0    # mean HR increase (bpm) under stress
HR_STRESS_SD_INC = 5.0      # SD of HR increase under stress

SCL_BASE_MEAN = 3.0         # baseline SCL mean population (µS)
SCL_BASE_SD = 1.2
SCL_WITHIN_SD = 0.05        # small tonic fluctuations (µS)
SCL_DELTA_ON_STRESS_MEAN = 0.6   # mean tonic increase under stress (µS)
SCL_DELTA_ON_STRESS_SD = 0.4

SCR_RATE_BASE = 0.5         # non-stress SCRs per 60s on avg (events/min)
SCR_RATE_STRESS = 2.5       # SCRs per 60s under stress
SCR_AMP_BASE_mean = 0.05    # mean SCR amplitude (µS), conservative for toy sensors
SCR_AMP_STRESS_mean = 0.2
SCR_AMP_sd = 0.05
SCR_WIDTH_SEC_mean = 1.2    # width of SCR pulse (s)
SCR_WIDTH_sd = 0.3

# noise
EDA_NOISE_SD = 0.02         # measurement noise (µS)
HR_NOISE_SD = 0.5           # jitter in instantaneous HR (bpm)

# ---------- utilities ----------
def simulate_hr_1hz(hr_base, hr_within_sd, stress_increase=0.0, reduce_hrv=1.0, rng=None):
    """
    Simulate 60-s instantaneous HR (1 Hz) time series.
    Model: baseline hr + stress_increase, plus colored noise to mimic HRV.
    We'll use an Ornstein-Uhlenbeck-like process (lowpass filtered white noise).
    """
    if rng is None:
        rng = np.random.default_rng()
    t = np.arange(0, WINDOW_SEC, 1.0/HR_FS)
    # generate white noise
    wn = rng.normal(0, hr_within_sd * reduce_hrv, size=t.shape)
    # lowpass filter to produce smooth HRV (cut ~0.1-0.25 Hz)
    b, a = signal.butter(2, 0.08, btype='low', fs=HR_FS)
    smooth = signal.filtfilt(b, a, wn)
    hr = hr_base + stress_increase + smooth
    # add small measurement jitter
    hr += rng.normal(0, HR_NOISE_SD, size=hr.shape)
    # clip to physiologic bounds
    hr = np.clip(hr, 40, 200)
    return hr

def synthesize_scr_train(eda_fs, scr_count, rng):
    """
    Generate SCR events as gaussian-shaped pulses in time.
    returns signal at eda_fs Hz for WINDOW_SEC seconds.
    """
    n_samples = int(WINDOW_SEC * eda_fs)
    t = np.arange(n_samples) / eda_fs
    eda = np.zeros_like(t)
    # sample SCR amplitudes and widths
    for i in range(scr_count):
        onset = rng.uniform(0, WINDOW_SEC - 0.5)
        width = max(0.3, rng.normal(SCR_WIDTH_SEC_mean, SCR_WIDTH_sd))
        amp = max(0.005, rng.normal(SCR_AMP_BASE_mean, SCR_AMP_sd))  # amplitude baseline; caller can scale
        # gaussian pulse centered at onset + width/2
        sigma = width / 2.355  # convert FWHM-like to sigma approx
        pulse = amp * np.exp(-0.5 * ((t - onset) / sigma)**2)
        eda += pulse
    return eda

def compute_features(hr_window, eda_window, eda_fs):
    """Compute the 15 requested features from 60s windows"""
    feats = {}
    # HR features (hr_window is 1Hz instantaneous bpm)
    feats['hr_mean'] = float(np.nanmean(hr_window))
    feats['hr_std']  = float(np.nanstd(hr_window, ddof=1))
    feats['hr_min']  = float(np.nanmin(hr_window))
    feats['hr_max']  = float(np.nanmax(hr_window))
    feats['hr_range']= feats['hr_max'] - feats['hr_min']
    feats['hr_skew'] = float(stats.skew(hr_window))
    feats['hr_kurtosis'] = float(stats.kurtosis(hr_window))
    # EDA features (tonic+phasic signal; units µS)
    feats['eda_mean'] = float(np.nanmean(eda_window))
    feats['eda_std']  = float(np.nanstd(eda_window, ddof=1))
    feats['eda_min']  = float(np.nanmin(eda_window))
    feats['eda_max']  = float(np.nanmax(eda_window))
    feats['eda_range']= feats['eda_max'] - feats['eda_min']
    feats['eda_skew'] = float(stats.skew(eda_window))
    feats['eda_kurtosis'] = float(stats.kurtosis(eda_window))
    # slope: linear fit over window -> slope per second (µS / s)
    x = np.arange(len(eda_window)) / eda_fs
    if len(x) >= 2:
        a, b = np.polyfit(x, eda_window, 1)
        feats['eda_slope'] = float(a)   # µS per second
    else:
        feats['eda_slope'] = 0.0
    return feats

# ---------- main generation ----------
def generate_dataset(n_windows=N_WINDOWS, stress_ratio=STRESS_RATIO, rng_seed=42):
    rng = np.random.default_rng(rng_seed)
    rows = []
    for i in tqdm(range(n_windows)):
        is_stress = rng.random() < stress_ratio
        # sample a subject-level baseline HR and SCL (simulate inter-subject variance)
        hr_base = max(45.0, rng.normal(HR_BASE_MEAN, HR_BASE_SD))
        scl_base = max(0.5, rng.normal(SCL_BASE_MEAN, SCL_BASE_SD))
        # within-window variability (HRV)
        hr_within_sigma = max(0.5, HR_WITHIN_SD)
        reduce_hrv = HRV_REDUCTION_ON_STRESS if is_stress else 1.0
        stress_increase = float(max(0.0, rng.normal(HR_STRESS_MEAN_INC, HR_STRESS_SD_INC))) if is_stress else 0.0
        # simulated HR 1Hz (60 samples)
        hr_window = simulate_hr_1hz(hr_base, hr_within_sigma, stress_increase=stress_increase, reduce_hrv=reduce_hrv, rng=rng)
        # create EDA: tonic + phasic + noise
        n_eda_samples = int(WINDOW_SEC * EDA_FS)
        t = np.arange(n_eda_samples) / EDA_FS
        # tonic component: slow drift around scl_base
        tonic = scl_base + rng.normal(0, SCL_WITHIN_SD, size=n_eda_samples)
        tonic = gaussian_filter1d(tonic, sigma=EDA_FS*3)  # make it slow
        # SCR events: sample rate (count) depends on stress
        scr_rate = SCR_RATE_STRESS if is_stress else SCR_RATE_BASE
        # sample actual SCR count from poisson with mean scr_rate
        scr_count = rng.poisson(scr_rate)
        scr_signal = synthesize_scr_train(EDA_FS, scr_count, rng=rng)
        # adjust SCR amplitude distribution for stress vs non-stress
        if is_stress:
            # scale SCR amplitudes upward
            # we generated SCRs with baseline amplitude constant inside function; scale by multiplier
            scr_signal *= (SCR_AMP_STRESS_mean / max(0.0001, SCR_AMP_BASE_mean))
        else:
            scr_signal *= (SCR_AMP_BASE_mean / max(0.0001, SCR_AMP_BASE_mean))
        # combine and add noise
        eda_window = tonic + scr_signal + rng.normal(0, EDA_NOISE_SD, size=n_eda_samples)
        # clip (physiologic)
        eda_window = np.clip(eda_window, 0.0, 60.0)
        # compute features
        feats = compute_features(hr_window, eda_window, EDA_FS)
        feats['label'] = int(is_stress)
        feats['scr_count'] = int(scr_count)   # extra column for debugging
        feats['hr_base'] = hr_base
        feats['scl_base'] = scl_base
        rows.append(feats)
    df = pd.DataFrame(rows)
    # drop helper cols from features if you want, but keep for analysis
    return df

if __name__ == "__main__":
    df = generate_dataset(n_windows=N_WINDOWS, stress_ratio=STRESS_RATIO, rng_seed=123)
    print("Generated dataset shape:", df.shape)
    # show some summary
    print(df.groupby('label')[['hr_mean','eda_mean','scr_count']].describe().T)
    # save
    df.to_csv("synthetic_hr_eda_windows.csv", index=False)
    print("Saved synthetic_hr_eda_windows.csv")
