# Multimodal Construction Intelligence Platform
**Skill Wallet · Capstone Project 1**

A modular Streamlit demo with four modules: visual PPE/safety triage, concrete crack triage, planning/valuation estimates, and weather-aware daily assistance. It supports Gemini live mode when a key is configured and a clearly labelled demonstration mode without one.

## Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. To enable live Gemini analysis, paste a Google Gemini API key into the sidebar for the current session, or set the `GEMINI_API_KEY` environment variable. Do not commit API keys to source control.

### Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, select the repository and `app.py` as the main file.
3. Deploy. Add the key under **App settings → Secrets** if live AI is required:

```toml
GEMINI_API_KEY = "your-key-here"
```

You can also set `GEMINI_MODEL` as an environment variable if you need to switch to another model available to your API key. The app defaults to `gemini-2.5-flash`.

## Features

- **Site Safety & PPE Audit:** JPG/PNG upload, structured JSON from Gemini, PPE checklist, hazard severity/remedies, download report.
- **Crack Diagnostics:** visual defect triage, estimated width when possible, root-cause hypotheses, next-step/repair recommendations, urgency, JSON download.
- **Planning & Valuation:** editable square-foot rates, project-budget and pro-rata spend estimates, indicative steel/cement thumb rules, progress milestones, and a Pollinations AI concept-render prompt/link.
- **Daily Site Assistant:** weather-linked safety reminders and a multi-turn assistant using Gemini when configured, or fixed general demo responses otherwise.

## Engineering & security notes

- API key is entered in a password field and held only in the current Streamlit session; secrets/environment variables are supported. Do not display, log or commit secrets.
- No external database is required. Results/chat are kept only in Streamlit session state and will not be durable across sessions.
- Image upload size is capped at 12 MB. Accepted image types are JPG/JPEG and PNG.
- Demo outputs are labelled and explicitly state they are not based on uploaded imagery.
- Budget rates, valuation rates, steel and cement quantities are rough illustrative assumptions—not a bill of quantities or valuation. Update with local quantity-surveyor, engineer and valuer input.
- AI image interpretation cannot verify hidden PPE, establish exact crack width without a scale, or certify OSHA/Indian code compliance. IS 456 concerns plain and reinforced concrete design; it is not a PPE checklist. Use qualified on-site inspection for all safety-critical and structural issues.
- Pollinations integration generates a concept prompt URL. Availability, authentication and model access are controlled by the external service and may change.

## Project layout

```text
multimodal_construction_intelligence/
├── app.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```
