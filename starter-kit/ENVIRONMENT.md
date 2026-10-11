# Environment

The backend centrally loads the root `.env`; exported process environment overrides it. The CLI helper reads only exported environment variables. Never send secret values to the frontend or commit `.env`.

| Variable | Default | Required |
|---|---|---|
| RAG_MODE | extractive | `extractive` or `dify`; live mode never silently falls back |
| DIFY_API_BASE_URL | http://localhost/v1 | Local Dify endpoint for native commands |
| DIFY_DOCKER_API_BASE_URL | http://host.docker.internal/v1 | Compose overrides DIFY_API_BASE_URL with this host-accessible endpoint |
| DIFY_APP_API_KEY | empty | For `RAG_MODE=dify`, the published Workflow's app key |
| DIFY_INPUT_NAME | ticket_text | Workflow ticket input name |
| DIFY_KNOWLEDGE_API_KEY | empty | Only for separate toolkit knowledge commands |
| DIFY_USER | local-ticket-assistant | Toolkit generation identifier; runtime uses fixed local-ticket user |
| DIFY_TIMEOUT | 100 | Toolkit timeout; runtime fixed 100 seconds |
| EVAL_MODE | offline | `offline` or `decisions` |
| OPENAI_API_KEY | empty | For `EVAL_MODE=decisions` |
| HOST | 127.0.0.1 | Native binds loopback; Docker overrides to 0.0.0.0 internally |
| PORT | 8080 | Local backend port; Docker uses 8080 |
| LOCAL_UID | 10001 | Docker bind-mount owner; use host `id -u` |
| LOCAL_GID | 10001 | Docker bind-mount group; use host `id -g` |

Dify Workflow outputs must include `answer`, `category`, `disposition`, `evidence` and `citations`. Evidence entries require `evidence_id`, `source_id`, `section_id`, `excerpt`, `source_revision`; every excerpt must occur in a matching approved source revision. Citations identify returned evidence and must match any repeated evidence fields. The adapter accepts JSON arrays or JSON-serialized arrays. The `answered` disposition requires evidence and citations. If supporting evidence is unavailable, return `needs_clarification` or `escalated`.

The optional `evaluation_feedback` Workflow input carries corrective feedback on the single allowed generation retry. The ticket text stays unchanged. Set up this input before enabling live corrective generation.

The selected Dify service is self-hosted locally, separate from the ticket demo on port 8080. If Dify publishes another port (for example 8081), set both URLs to that port: `http://localhost:8081/v1` and `http://host.docker.internal:8081/v1`. Compose adds the host gateway alias for container access. Cloud credentials do not carry over to a local workspace; create a local Workflow app key. See [local Dify setup](../docs/DIFY_LOCAL_SETUP.md).
