import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google import genai

from ingestion import ingest_reports
from analytics import (
    add_quarter_column,
    county_kpis,
    billing_summary,
    collection_efficiency,
    subcounty_performance,
    ward_performance,
    ward_compliance,
    monthly_target_pace,
    historical_comparison,
    current_reporting_period,
    quarter_comparison,
    quarter_target,
    subcounty_quarter_comparison,
    ward_quarter_comparison,
    revenue_leakage,
    leakage_by_subcounty,
    revenue_by_activity,
    sector_concentration,
    unpaid_bills_register,
    aging_analysis,
    voided_cancelled_analysis,
    partpayment_tracking,
    get_financial_years,
    filter_by_fy,
)
from ai_analyst import build_data_context, chat_with_analyst, generate_executive_brief


genai_client = None

app = FastAPI(
    title="Revenue Intelligence MCP Server",
    description="A tool-backed MCP server for revenue analytics and AI-assisted insights.",
    version="0.1.0",
)


class ToolRequest(BaseModel):
    tool_name: str = Field(..., description="The tool to execute.")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    question: str = Field(..., description="The user question for the AI analyst.")
    session_history: Optional[List[Dict[str, str]]] = Field(
        default_factory=list,
        description="Optional prior chat messages in the format [{role: 'user'|'model', content: '...'}].",
    )
    financial_year: Optional[str] = Field(None, description="Optional financial year filter for the data context.")


class BriefRequest(BaseModel):
    financial_year: Optional[str] = Field(None, description="Optional financial year filter for the executive brief.")


class AgentRequest(BaseModel):
    question: str = Field(..., description="The user question for the agent.")
    financial_year: Optional[str] = Field(None, description="Optional financial year filter.")


def configure_server_gemini():
    global genai_client
    if genai_client is not None:
        return genai_client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
    genai_client = genai.Client(api_key=api_key)
    return genai_client


@lru_cache(maxsize=1)
def get_data():
    df = ingest_reports()
    if df.empty:
        raise RuntimeError("No revenue reports were loaded. Ensure data files exist in data/reports/")
    return df


def serializable_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: serializable_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serializable_value(v) for v in value]
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    try:
        json.dumps(value)
        return value
    except (TypeError, OverflowError):
        return str(value)


def serialize_dataframe(df):
    return [
        {k: serializable_value(v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


def build_context(financial_year: Optional[str] = None) -> str:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    billing = billing_summary(df)
    kpis = county_kpis(df)
    historical = historical_comparison(df)
    efficiency = collection_efficiency(df)
    return build_data_context(df, billing, kpis, efficiency, historical)


def tool_get_financial_years() -> Dict[str, Any]:
    return {"financial_years": get_financial_years(get_data())}


def tool_county_kpis(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "kpis": county_kpis(df)}


def tool_billing_summary(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "billing": billing_summary(df)}


def tool_collection_efficiency(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "efficiency": collection_efficiency(df)}


def tool_subcounty_performance(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "subcounty_performance": serialize_dataframe(subcounty_performance(df))}


def tool_ward_compliance(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "ward_compliance": serialize_dataframe(ward_compliance(df))}


def tool_monthly_target_pace(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "monthly_target_pace": serialize_dataframe(monthly_target_pace(df))}


def tool_historical_comparison() -> Dict[str, Any]:
    return {"historical_comparison": historical_comparison(get_data())}


def tool_revenue_by_activity(financial_year: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "revenue_by_activity": serialize_dataframe(revenue_by_activity(df, top_n=top_n))}


def tool_sector_concentration(financial_year: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "sector_concentration": serialize_dataframe(sector_concentration(df, top_n=top_n))}


def tool_unpaid_bills_register(financial_year: Optional[str] = None, subcounty: Optional[str] = None, ward: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {
        "financial_year": financial_year or "all",
        "unpaid_bills": serialize_dataframe(unpaid_bills_register(df, subcounty=subcounty, ward=ward)),
    }


def tool_aging_analysis(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "aging_analysis": serialize_dataframe(aging_analysis(df))}


def tool_partpayment_tracking(financial_year: Optional[str] = None) -> Dict[str, Any]:
    df = get_data()
    if financial_year:
        df = filter_by_fy(df, financial_year)
    return {"financial_year": financial_year or "all", "partpayment_tracking": serialize_dataframe(partpayment_tracking(df))}


def tool_revenue_leakage() -> Dict[str, Any]:
    result = revenue_leakage(get_data())
    if result is None:
        return {"revenue_leakage": None}
    leakage_df, total_lost = result
    return {
        "revenue_leakage": serialize_dataframe(leakage_df),
        "total_revenue_lost": total_lost,
    }


def tool_leakage_by_subcounty() -> Dict[str, Any]:
    return {"leakage_by_subcounty": serialize_dataframe(leakage_by_subcounty(get_data()))}


TOOL_REGISTRY = {
    "get_financial_years": {
        "description": "List available financial years in the loaded revenue dataset.",
        "function": tool_get_financial_years,
        "parameters": {},
    },
    "county_kpis": {
        "description": "Summarize county key performance indicators for an optional financial year.",
        "function": tool_county_kpis,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "billing_summary": {
        "description": "Return billing totals for an optional financial year.",
        "function": tool_billing_summary,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "collection_efficiency": {
        "description": "Return collection efficiency for an optional financial year.",
        "function": tool_collection_efficiency,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "subcounty_performance": {
        "description": "Return revenue and gap performance by subcounty.",
        "function": tool_subcounty_performance,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "ward_compliance": {
        "description": "Return ward-level compliance and collection rates.",
        "function": tool_ward_compliance,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "monthly_target_pace": {
        "description": "Return month-by-month revenue pace vs target for an optional financial year.",
        "function": tool_monthly_target_pace,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "historical_comparison": {
        "description": "Compare current and prior financial year revenue performance.",
        "function": tool_historical_comparison,
        "parameters": {},
    },
    "revenue_by_activity": {
        "description": "Return top revenue-generating activities.",
        "function": tool_revenue_by_activity,
        "parameters": {"financial_year": "Optional financial year string", "top_n": "Number of activities to return"},
    },
    "sector_concentration": {
        "description": "Return revenue concentration by business sector.",
        "function": tool_sector_concentration,
        "parameters": {"financial_year": "Optional financial year string", "top_n": "Number of sectors to return"},
    },
    "unpaid_bills_register": {
        "description": "Return unpaid or part-payment bills, optionally filtered by subcounty and ward.",
        "function": tool_unpaid_bills_register,
        "parameters": {"financial_year": "Optional financial year string", "subcounty": "Optional subcounty", "ward": "Optional ward"},
    },
    "aging_analysis": {
        "description": "Return outstanding bills aging buckets.",
        "function": tool_aging_analysis,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "partpayment_tracking": {
        "description": "Return part-payment tracking details.",
        "function": tool_partpayment_tracking,
        "parameters": {"financial_year": "Optional financial year string"},
    },
    "revenue_leakage": {
        "description": "Identify revenue leakage from businesses active in the prior year but not the current one.",
        "function": tool_revenue_leakage,
        "parameters": {},
    },
    "leakage_by_subcounty": {
        "description": "Summarize revenue leakage by subcounty.",
        "function": tool_leakage_by_subcounty,
        "parameters": {},
    },
}


@app.on_event("startup")
def startup_event():
    configure_server_gemini()
    get_data()


@app.get("/health")
def health_check():
    return {"status": "ok", "data_loaded": True, "tools": list(TOOL_REGISTRY.keys())}


@app.get("/tools")
def list_tools():
    return {
        "tools": {
            name: {"description": tool_info["description"], "parameters": tool_info["parameters"]}
            for name, tool_info in TOOL_REGISTRY.items()
        }
    }


@app.post("/run_tool")
def run_tool(request: ToolRequest):
    tool_info = TOOL_REGISTRY.get(request.tool_name)
    if tool_info is None:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found.")

    result = tool_info["function"](**(request.parameters or {}))
    return {"tool_name": request.tool_name, "result": result}


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required.")
    data_context = build_context(request.financial_year)
    response_text = chat_with_analyst(data_context, request.question, request.session_history)
    return {"question": request.question, "answer": response_text}


@app.post("/brief")
def brief(request: BriefRequest):
    data_context = build_context(request.financial_year)
    text = generate_executive_brief(data_context)
    return {"financial_year": request.financial_year or "all", "executive_brief": text}


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output.")
    return text[start : end + 1]


@app.post("/agent")
def agent(request: AgentRequest):
    model_client = configure_server_gemini()
    data_context = build_context(request.financial_year)
    tool_list = "\n".join(
        f"- {name}: {info['description']}" for name, info in TOOL_REGISTRY.items()
    )

    prompt = f"""
You are an AI revenue assistant. Use one of the available tools to answer the user question.

Available tools:
{tool_list}

User question: {request.question}

Respond with a JSON object containing:
- tool: the tool name to invoke
- parameters: a dictionary of parameters to pass to the tool

Example:
{{"tool": "county_kpis", "parameters": {{"financial_year": "2024/2025"}}}}

Only return valid JSON.
"""
    response = model_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
    )
    try:
        payload = json.loads(_extract_json_object(response.text))
    except ValueError:
        raise HTTPException(status_code=500, detail="Unable to parse tool selection from model response.")

    tool_name = payload.get("tool")
    parameters = payload.get("parameters", {})
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' is not available.")

    tool_result = TOOL_REGISTRY[tool_name]["function"](**parameters)
    return {
        "question": request.question,
        "selected_tool": tool_name,
        "parameters": parameters,
        "tool_result": tool_result,
    }
