# VocalModelingStudio - lekki cleanup sciezki wokalnej

Ten etap dotyczy workflow standaryzacji wokalu wzgledem instrumentalu.

Zasada projektu:

```text
instrumental = referencja
vocal_processed.wav = glowny wynik VMS
preview_mix.wav = tylko odsluch kontrolny
```

## Co robi cleanup

Cleanup to lekki etap przygotowawczy przed dopasowaniem gain:

1. basic numeric cleanup,
2. remove DC offset,
3. high-pass,
4. opcjonalny de-esser (pasmo sybilantow, attack/release, soft-knee),
5. fade safety,
6. opcjonalny trim ciszy,
7. opcjonalny noise gate,
8. opcjonalny gain staging RMS.

Domyslnie wlaczone sa kroki bezpieczne (`enabled`, `remove_dc_offset`, `high_pass_enabled`, `fade_ms`).
De-esser jest domyslnie wylaczony i przeznaczony do korekty sybilantow, gdy wokal jest zbyt ostry.
Noise gate dziala jako lagodny gate adaptacyjny (floor/hold/attack/release), a nie twarde wycinanie pojedynczych probek.

## Raport cleanup

Raport standaryzacji zawiera sekcje cleanup:

- aktywny: tak/nie,
- peak przed/po,
- RMS przed/po,
- lista zastosowanych krokow,
- ostrzezenia.

## Ustawienia

Fragment `configs/default.yaml`:

```yaml
audio:
  cleanup:
    enabled: true
    remove_dc_offset: true
    high_pass_enabled: true
    high_pass_hz: 80.0
    high_pass_order: 2
    de_esser_enabled: false
    de_esser_threshold_db: -28.0
    de_esser_ratio: 3.0
    de_esser_max_reduction_db: 8.0
    de_esser_band_low_hz: 4500.0
    de_esser_band_high_hz: 9500.0
    de_esser_attack_ms: 4.0
    de_esser_release_ms: 90.0
    de_esser_knee_db: 6.0
    de_esser_stereo_link: true
    fade_ms: 5.0
    noise_gate_enabled: false
    noise_gate_db: -55.0
    noise_gate_floor_db: -24.0
    noise_gate_attack_ms: 4.0
    noise_gate_release_ms: 80.0
    noise_gate_hold_ms: 20.0
    trim_silence_enabled: false
```

