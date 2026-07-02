from app.services.rag_service import RAGService


def test_build_context_prompt_uses_retrieved_chunks():
    service = RAGService()
    chunks = [
        {"title": "Feed Manual", "content": "Feed usage increased 12% this week."},
        {"title": "Medicine Report", "content": "Medicine expenses are unusually high."},
    ]

    prompt = service.build_context_prompt("Give me an AI summary", chunks)

    assert "Feed Manual" in prompt
    assert "Feed usage increased 12% this week." in prompt
    assert "Medicine Report" in prompt


def test_build_insight_summary_creates_actionable_points():
    service = RAGService()
    payload = {
        "feed_stock": 80,
        "medicine_stock": 5,
        "pending_bills": 3,
        "recent_expenses": 24000,
        "low_stock_items": ["Layer Feed"],
        "vaccination_alerts": ["Vaccinate flock A"],
        "mortality_alerts": ["Mortality rose above threshold"],
    }

    summary = service.build_dashboard_insights(payload)

    assert any("Feed stock" in item for item in summary["insights"])
    assert any("Medicine" in item for item in summary["insights"])
    assert any("Action" in item for item in summary["suggested_actions"])
