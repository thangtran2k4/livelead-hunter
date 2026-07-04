# Live Stream Collection MVP

MVP Streamlit dashboard to discover, rank, and suggest engagement ideas for livestreams and online events.

## Run locally

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run app.py
```

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
