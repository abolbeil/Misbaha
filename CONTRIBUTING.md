# Contributing to Misbaha

Thank you for helping! Bug reports, translations, new adhkar and code are all welcome.

## Reporting a bug

Please include:
- Windows version, Misbaha version (*menu → About*), and whether you run the exe or from source.
- Your mouse and any mouse software (Logitech Options+, G HUB, Razer Synapse, X-Mouse Button Control, AutoHotkey…).
- Whether the program you were working in runs as administrator.
- `%APPDATA%\Misbaha\error.log` and `crash.log` (if present).

## Adding adhkar

Edit `misbaha/data.py`. Every entry needs a unique `id`, a category, the Arabic text with tashkeel, a recommended count, its virtue (`fadl`) and an **authentic source** (`src`). Entries without a reliable source can't be accepted.

## Translations

Interface strings are written in Arabic in the code and translated through the `EN` table in `misbaha/i18n.py`. To add a language, add a table like `EN`, then register it in `LANGS` and `TABLES`.

## Development

```bat
python -m pip install -r requirements.txt pyflakes
python Misbaha.pyw                          :: run (use python, not pythonw, to see errors)
python -m pyflakes misbaha tests
python -m unittest discover -s tests -v
```

Guidelines:
- The mouse-hook callback (`InputHook._callback`) runs for every mouse event on the system: keep it tiny and never block in it.
- All Win32 calls go through `misbaha/winapi.py` with explicit `argtypes`/`restype` (64-bit safe) and must never raise.
- Don't add timers that run continuously; start them only while needed.
- Keep `state.json` backward compatible: new settings need a default in `DEFAULT_SETTINGS` and validation in `_sanitize_settings`.
