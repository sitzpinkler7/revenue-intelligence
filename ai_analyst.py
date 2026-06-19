from google import genai


_client = None


def configure_gemini(api_key):
    global _client
    _client = genai.Client(api_key=api_key)


def build_data_context(df, billing, kpis, efficiency, historical):
    total_records = len(df)
    subcounties = df["Subcounty"].unique().tolist()
    wards = df["Ward"].nunique()

    sc_revenue = (
        df.groupby("Subcounty")["AmountPaid"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    status_counts = df["BillStatus"].value_counts().to_dict()

    date_min = df["Bill Date"].min().strftime("%d %b %Y")
    date_max = df["Bill Date"].max().strftime("%d %b %Y")

    context = f"""
You are the AI Revenue Analyst for the County Government of Uasin Gishu.
You have access to the following revenue data from Single Business Permits:

PERIOD: {date_min} to {date_max}
TOTAL RECORDS: {total_records:,}
SUBCOUNTIES: {', '.join(subcounties)}
TOTAL WARDS: {wards}

KEY PERFORMANCE INDICATORS:
- Total Collected: KES {kpis['total_collected']:,.0f}
- Target Revenue: KES {kpis['target']:,.0f}
- Progress: {kpis['progress_percent']:.0f}%
- Remaining: KES {kpis['remaining_revenue']:,.0f}
- Collection Efficiency: {efficiency:.0f}%
- YoY Growth: {historical['growth']:.0f}%

BILLING SUMMARY:
- Paid: KES {billing['paid']:,.0f}
- Unpaid: KES {billing['unpaid']:,.0f}
- Part-Payments: KES {billing['partpaid']:,.0f}
- Part-Payment Remaining: KES {billing['partpaid_remaining']:,.0f}
- Voided: KES {billing['voided']:,.0f}
- Cancelled: KES {billing['cancelled']:,.0f}
- Total Billed: KES {billing['total_billed']:,.0f}

REVENUE BY SUBCOUNTY:
"""
    for sc, rev in sc_revenue.items():
        context += f"- {sc}: KES {rev:,.0f}\n"

    context += f"\nBILL STATUS BREAKDOWN:\n"
    for status, count in status_counts.items():
        context += f"- {status}: {count:,}\n"

    if "activity_description" in df.columns:
        top_activities = (
            df.groupby("activity_description")["AmountPaid"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )
        context += "\nTOP 10 REVENUE ACTIVITIES:\n"
        for act, rev in top_activities.items():
            context += f"- {act}: KES {rev:,.0f}\n"

    context += """
INSTRUCTIONS:
- Always respond with specific numbers from the data above.
- Format all currency as KES with thousand separators and no decimal places.
- Be concise and actionable in your responses.
- When asked about trends or comparisons, reference the actual figures.
- If asked something not answerable from this data, say so clearly.
- You are speaking to county government officials — be professional but accessible.
"""
    return context


def chat_with_analyst(data_context, user_question, chat_history=None):
    contents = []

    if chat_history:
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    if not contents:
        prompt = data_context + "\n\nUser question: " + user_question
    else:
        prompt = user_question

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
    )
    return response.text


def generate_executive_brief(data_context):
    prompt = data_context + """

Generate a professional Executive Revenue Brief for the County Government of Uasin Gishu.

Structure it as follows:

1. REVENUE PERFORMANCE OVERVIEW
   - Overall collection vs target with percentage
   - Collection efficiency assessment

2. SUBCOUNTY PERFORMANCE HIGHLIGHTS
   - Top performing subcounties
   - Underperforming subcounties requiring attention

3. KEY CONCERNS
   - Unpaid revenue analysis
   - Voided/cancelled bills assessment
   - Any revenue leakage indicators

4. STRATEGIC RECOMMENDATIONS
   - 3-5 specific, actionable recommendations for improving revenue collection
   - Priority areas for the next quarter

5. OUTLOOK
   - Revenue projection based on current trends
   - Risk factors to monitor

Format the brief professionally. Use specific numbers from the data.
Keep it under 800 words. Use KES with thousand separators and no decimal places for all figures.
"""

    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text
