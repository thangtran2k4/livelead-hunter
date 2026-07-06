# Live Stream Collection MVP

MVP Streamlit dashboard to discover, rank, and suggest engagement ideas for livestreams and online events.

## Run locally

### Prerequisites

- Python installed on your machine.
- A terminal or command prompt.

### First-time setup

1. Clone the repository and open the project folder.
2. Create and activate a Python virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the app:

```bash
streamlit run app.py
```

5. Open the local URL shown in the terminal, usually http://localhost:8501.

Notes for new users:

- The app uses the local SQLite database in data/live_leads.sqlite3.
- The database and demo data are created automatically on first run.
- You do not need API keys to explore the dashboard locally.

## Current scope

- Mock event ingestion for YouTube Live, LinkedIn Events, Meetup, and Eventbrite.
- Lead scoring based on industry fit, persona fit, speaker quality, and engagement potential.
- Suggested questions and follow-up messages.
- Filterable dashboard for prioritizing events.

## Crawl plan

Phase 1 uses only stable and low-friction sources first.

- YouTube Live: use official API where possible, otherwise crawl public event metadata only.
- Eventbrite and Meetup: prefer public pages and API endpoints if available.
- LinkedIn Events: treat as a later source because of stricter access and anti-bot controls.

Recommended pipeline:

1. Discover candidate events from each source.
2. Normalize the raw payload into one common event schema.
3. Deduplicate by source plus URL or external event id.
4. Enrich with AI classification and lead scoring.
5. Persist raw events and scored snapshots in SQLite.
6. Re-run on a schedule and only alert on newly high-scoring events.

Practical crawl rules:

- Prefer official APIs before browser automation.
- Use Playwright only when the source has no usable API or public feed.
- Throttle requests and respect rate limits.
- Do not collect private or sensitive personal data without a clear legal basis.
- Keep raw payloads and derived scores separate so the scoring model can change later without losing history.

## Optional environment variables

- `OPENAI_API_KEY`: enables AI-backed scoring and content suggestions.
- `OPENAI_MODEL`: overrides the default model name used for scoring.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: enable Telegram alerts.
- `SLACK_WEBHOOK_URL`: enables Slack alerts.
- `ALERT_SCORE_THRESHOLD`: score threshold for notifications in the UI.

## Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Run on Google Colab

Yes, you can run this project in Google Colab for a quick demo, but only through a tunnel because Colab cannot expose Streamlit directly the same way as a local machine.

### What to expect

- This is suitable for a temporary demo or quick testing.
- Colab sessions can disconnect, so the SQLite database and uploaded files are not persistent.
- The app still uses the local SQLite file in `data/live_leads.sqlite3` inside the Colab runtime.

### Colab steps

1. Open a new Colab notebook.
2. Clone the repository:

```bash
!git clone <YOUR_REPO_URL>
%cd live-stream_collection
```

3. Install dependencies:

```bash
!pip install -r requirements.txt
!pip install pyngrok
```

4. Start Streamlit in the background:

```bash
!streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

5. Open a tunnel to port 8501. One simple option is `pyngrok`:

```python
from pyngrok import ngrok

public_url = ngrok.connect(8501)
print(public_url)
```

6. Open the printed URL in your browser.

### Notes

- If the tunnel URL stops working, restart the Colab runtime and run the cells again.
- If you want a stable deployment, use Streamlit Cloud or a small VPS instead of Colab.
- You do not need API keys just to open the dashboard with the included mock data.
