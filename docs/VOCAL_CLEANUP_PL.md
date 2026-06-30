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
4. fade safety,
5. opcjonalny trim ciszy,
6. opcjonalny noise gate,
7. opcjonalny gain staging RMS.

Domyslnie wlaczone sa kroki bezpieczne (`enabled`, `remove_dc_offset`, `high_pass_enabled`, `fade_ms`).

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
    fade_ms: 5.0
    noise_gate_enabled: false
    trim_silence_enabled: false
```

