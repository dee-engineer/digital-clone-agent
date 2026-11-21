# Contributing

Thanks for helping. Good first contributions: new built-in skills (YAML in agent/app/builtin_skills), new LangGraph workflows,
n8n workflow examples, a Telegram/Slack approval channel, other LLM providers behind `app/llm.py`, docs.

```bash
cd agent
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Rules: keep tests passing (they mock the LLM, no API key needed), keep the approval gate in front of any outward action,
never commit secrets, personal persona files or real emails. Open an issue before large changes.
