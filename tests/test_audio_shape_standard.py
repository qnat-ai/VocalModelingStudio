from __future__ import annotations

import numpy as np

from app.audio.format import ensure_audio_shape


def test_ensure_audio_shape_transposes_channel_first_stereo():
    channel_first = np.vstack(
        [
            np.linspace(0.0, 1.0, 100, endpoint=False),
            np.linspace(1.0, 0.0, 100, endpoint=False),
        ]
    )

    shaped = ensure_audio_shape(channel_first)

    assert shaped.shape == (100, 2)


def test_ensure_audio_shape_keeps_sample_first_stereo():
    sample_first = np.column_stack(
        [
            np.linspace(0.0, 1.0, 100, endpoint=False),
            np.linspace(1.0, 0.0, 100, endpoint=False),
        ]
    )

    shaped = ensure_audio_shape(sample_first)

    assert shaped.shape == (100, 2)

