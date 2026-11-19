import pytest
from audio import time_stretch as mod

CASES = [
    ("window", 'm.window_size(2, 1024) == 512'),
    ("pitch", 'm.pitch_preserve(2, 440) == 440'),
    ("transient", 'm.transient_gain(1, 2) == approx(4.0)'),
    ("phase", 'm.phase_continuity(2, 5) == 3'),
    ("latency", 'm.latency(2, 0.5) == approx(1.0)'),
    ("duration", 'm.duration(48000, 48000) == approx(1.0)'),
    ("ratio", 'm.resample_ratio(44100, 48000) == approx(1.0884, rel=1e-4)'),
    ("formant", 'm.formant_shift(2, 1) == 2'),
    ("fade", 'm.crossfade(2, 4) == approx(0.5)'),
    ("energy", 'm.energy_normalize(2, 4) == approx(2.0)'),
    ("boundary", 'm.block_boundary(7, 4) == 3'),
    ("speed", 'm.speed_from_tempo(120, 60) == approx(2.0)'),
    ("align", 'm.align_tracks(2, 0.5) == approx(1.0)'),
    ("hop", 'm.window_hop(1024, 0.5) == 512'),
    ("gain", 'm.smooth_gain(0, 1, 0.2) == approx(0.2)')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
