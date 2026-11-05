"""Normalized Gray-coded baseband modem and AWGN experiments."""
import math
import numpy as np

MODES = ('BPSK', 'QPSK', '16QAM')


def constellation(mode):
    k = {'BPSK': 1, 'QPSK': 2, '16QAM': 4}[mode]
    labels = ((np.arange(2 ** k)[:, None] >> np.arange(k - 1, -1, -1)) & 1).astype(np.uint8)
    if mode == 'BPSK':
        points = (1 - 2 * labels[:, 0].astype(float)).astype(complex)
    elif mode == 'QPSK':
        points = ((1 - 2 * labels[:, 0].astype(float)) + 1j * (1 - 2 * labels[:, 1].astype(float))) / np.sqrt(2)
    else:
        levels = np.array([-3, -1, 3, 1])
        points = (levels[labels[:, 0] * 2 + labels[:, 1]] + 1j * levels[labels[:, 2] * 2 + labels[:, 3]]) / np.sqrt(10)
    return points, labels


def modulate(bits, mode):
    points, labels = constellation(mode)
    k = labels.shape[1]
    padded = np.pad(np.asarray(bits, dtype=np.uint8), (0, (-len(bits)) % k), 'constant')
    indices = padded.reshape(-1, k).dot(2 ** np.arange(k - 1, -1, -1))
    return points[indices]


def demodulate(symbols, mode):
    points, labels = constellation(mode)
    # Bounded temporary storage for large Monte Carlo experiments.
    chunks = []
    for start in range(0, len(symbols), 16384):
        nearest = np.abs(symbols[start:start + 16384, None] - points[None, :]).argmin(axis=1)
        chunks.append(labels[nearest].reshape(-1))
    return np.concatenate(chunks) if chunks else np.array([], dtype=np.uint8)


def transmit(bits, mode, ebn0_db, rng):
    tx = modulate(bits, mode)
    k = constellation(mode)[1].shape[1]
    # Es=1; Eb=Es/k; each complex noise component has variance N0/2.
    sigma = np.sqrt(1.0 / (2 * k * 10 ** (ebn0_db / 10.0)))
    rx = tx + sigma * (rng.normal(size=len(tx)) + 1j * rng.normal(size=len(tx)))
    recovered = demodulate(rx, mode)[:len(bits)]
    errors = int(np.count_nonzero(recovered != bits))
    return {'tx': tx, 'rx': rx, 'bits': recovered, 'errors': errors,
            'ber': errors / float(len(bits)), 'count': len(bits)}


def text_bits(text):
    return np.unpackbits(np.frombuffer(text.encode('utf-8'), dtype=np.uint8))


def bits_text(bits):
    return np.packbits(bits).tobytes().decode('utf-8', errors='replace')


def theoretical_ber(mode, ebn0_db):
    x = 10 ** (np.asarray(ebn0_db, dtype=float) / 10)
    q = np.vectorize(lambda t: 0.5 * math.erfc(t / math.sqrt(2)))
    if mode in ('BPSK', 'QPSK'):
        return q(np.sqrt(2 * x))
    # Gray 16QAM high-SNR approximation.
    return 0.75 * q(np.sqrt(0.8 * x))


def calibrate(target=0.001):
    grid = np.arange(-5, 25.01, 0.05)
    thresholds = {}
    for mode in MODES:
        thresholds[mode] = float(grid[np.flatnonzero(theoretical_ber(mode, grid) <= target)[0]])
    return thresholds


def choose_mode(ebn0_db, thresholds):
    eligible = [m for m in MODES if ebn0_db >= thresholds[m]]
    return (eligible[-1], True) if eligible else ('BPSK', False)


def sweep(count=100000, seed=42):
    rng = np.random.RandomState(seed)
    bits = rng.randint(0, 2, count).astype(np.uint8)
    rows = []
    for db in range(0, 15, 2):
        for mode in MODES:
            result = transmit(bits, mode, db, rng)
            rows.append((db, mode, result['errors'], count, result['ber']))
    return rows
