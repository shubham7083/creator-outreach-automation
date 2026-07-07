# Development

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m creator_outreach_automation.database.migrations
```

## Run UI

```powershell
streamlit run app/streamlit_app.py
```

## Install Playwright Browsers

```powershell
playwright install chromium
```

## Conventions

- Keep modules small and typed.
- Add business logic behind service boundaries.
- Keep API-specific details inside `creator_outreach_automation/api`.
- Keep database access inside repositories.
- Add tests before implementing non-trivial workflows.
