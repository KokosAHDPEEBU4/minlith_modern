# Lene Project Context

## Recent Bug Fixes (2026-07-23)

### 14 Bugs Fixed (14 high/medium/low)
- calculator.py: division by zero (k1=0), apatite coeff 3.33→3.36, negative clamping, carbon wt% conversion
- coefficients.py: range 4/5 negative k1 clamped to 0
- constants.py: SO molar mass 80.066→48.064
- cli.py: cached results deserialization, operator precedence fix
- calculation_worker.py: formula/weight deserialization separated
- history_page.py: delete_sample(sample_id) instead of name
- csv_handler.py: first_line unbound variable
- config.py: reset() preserves recent_files/window_state
- settings_page.py: float() ValueError guard
- repository.py: .get() deprecated → .filter().first()
- All 58 tests passing
