# Security policy

This project processes untrusted email and holds an LLM API key, so security reports are welcome.

Please report vulnerabilities privately via GitHub's "Report a vulnerability" (Security tab), not public issues.
Include steps to reproduce and impact. Expect an acknowledgement within a few days.

Design principles contributors should preserve:
- The agent service never sends mail or holds mailbox credentials; only n8n does, and only after human approval.
- Inbound text is untrusted data (prompt-injection aware). Do not give the agent action tools without an approval gate.
- Auth is deny-by-default; services bind to localhost by default.
