# Revenue Intelligence

This repo contains a Streamlit dashboard for county revenue analytics and a new MCP server scaffold for tool-enabled AI assistance.

## New MCP server

The MCP server exposes analytics tools and AI chat/brief endpoints using Gemini.

### Run the MCP server

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Start the MCP server:

```bash
GEMINI_API_KEY=your_key_here uvicorn mcp_server:app --host 0.0.0.0 --port 8000 --reload
```

3. Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Server endpoints

- `GET /health`
- `GET /tools`
- `POST /run_tool`
- `POST /chat`
- `POST /brief`
- `POST /agent`

### Example tool request

```bash
curl -X POST http://127.0.0.1:8000/run_tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "county_kpis", "parameters": {"financial_year": "2024/2025"}}'
```

### Example chat request

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our collection efficiency for the current year?"}'
```
