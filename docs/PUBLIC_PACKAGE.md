# Public Package Boundary

The public PromoScout repository may contain:

- `app.py`
- `src/promoscout/`
- `prompts/`
- `tests/`
- `scripts/`
- `sample_data/synthetic_episode.txt`
- `README.md`
- `PLAN.md`
- `requirements.txt`
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `run_app.ps1`
- Non-confidential documentation under `docs/`

The following must remain private:

- `.env` and the Gemini API key.
- The Kuku screenplay ZIP and extracted screenplay text.
- The assignment PDF.
- `artifacts/`, including parsed screenplay excerpts and ranked outputs.
- `raw_outputs/`, including unedited Gemini responses.
- Local virtual environments, caches, and temporary files.

Before publishing, run:

```powershell
python scripts\audit_public_package.py
```

The audit checks the intended public file set for the configured API-key value and reports any disallowed private paths that would be included.

