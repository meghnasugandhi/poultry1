import hashlib
import json
import re
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import ChatMessage, ChatSession
from app.models.document import Document
from app.models.finance import Transaction, TransactionType
from app.models.inventory import InventoryCategory, InventoryItem
from app.models.rag_chunk import RAGChunk
from app.services.translation_service import translate_text


def sanitize_ai_text(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"Gemini_Generated_Image_[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp)", "Generated image", value, flags=re.I)
    cleaned = re.sub(r"\.(png|jpg|jpeg|webp)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"[_-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or value


class RAGService:
    EMBEDDING_DIMENSION = 1536

    def __init__(self) -> None:
        self._fallback_embedding = self._build_fallback_embedding()
        embedding_column = RAGChunk.__table__.c.get("embedding")
        self._pgvector_available = (
            embedding_column is not None
            and embedding_column.type.__class__.__module__.startswith("pgvector")
        )

    def _build_fallback_embedding(self) -> list[float]:
        return [0.0] * self.EMBEDDING_DIMENSION

    def build_context_prompt(self, question: str, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return f"User question: {question}\nAnswer using the available farm data and be concise."
        context_lines = []
        for idx, chunk in enumerate(chunks, start=1):
            title = chunk.get("title") or f"Source {idx}"
            content = chunk.get("content") or ""
            context_lines.append(f"[{idx}] {title}: {content}")
        return (
            "You are an AI assistant for a poultry ERP platform. "
            "Use the retrieved context below to answer the user's question.\n"
            f"User question: {question}\n\nRetrieved context:\n" + "\n\n".join(context_lines)
        )

    def build_dashboard_insights(self, payload: dict[str, Any], language: str = "en") -> dict[str, Any]:
        insights: list[str] = []
        suggested_actions: list[str] = []

        feed_stock = float(payload.get("feed_stock", 0) or 0)
        medicine_stock = float(payload.get("medicine_stock", 0) or 0)
        pending_bills = int(payload.get("pending_bills", 0) or 0)
        recent_expenses = float(payload.get("recent_expenses", 0) or 0)
        low_stock_items = payload.get("low_stock_items") or []
        vaccination_alerts = payload.get("vaccination_alerts") or []
        mortality_alerts = payload.get("mortality_alerts") or []

        if feed_stock <= 100:
            insights.append(sanitize_ai_text(f"Feed stock is low at {feed_stock:.0f} units; stock may last only a few days."))
            suggested_actions.append("Action: Reorder feed immediately and review recent consumption.")
        elif feed_stock <= 250:
            insights.append(f"Feed stock is moderate at {feed_stock:.0f} units; monitor usage closely.")

        if medicine_stock <= 10:
            insights.append(sanitize_ai_text(f"Medicine stock is critically low at {medicine_stock:.0f} units."))
            suggested_actions.append("Action: Restock medical supplies and check expiry dates.")

        if pending_bills > 0:
            insights.append(sanitize_ai_text(f"{pending_bills} pending bills need attention."))
            suggested_actions.append("Action: Review unpaid bills and prioritize payments.")

        if recent_expenses > 20000:
            insights.append(sanitize_ai_text("Medicine expenses are unusually high this period."))
            suggested_actions.append("Action: Compare recent medicine purchases with the last cycle and verify vendor costs.")

        if low_stock_items:
            insights.append(sanitize_ai_text(f"Low stock alert: {', '.join(low_stock_items[:3])}."))

        if vaccination_alerts:
            insights.append("Vaccination schedule reminders are pending.")
            suggested_actions.append("Action: Follow the vaccination schedule and mark the next batch as completed.")

        if mortality_alerts:
            insights.append("Mortality alerts require attention.")
            suggested_actions.append("Action: Inspect flock conditions and review recent feed and medicine changes.")

        translated_insights = [sanitize_ai_text(translate_text(item, language)) for item in (insights or ["Operations look steady. No urgent issues detected."])]
        translated_actions = [sanitize_ai_text(translate_text(item, language)) for item in (suggested_actions or ["Keep monitoring feed consumption and expense trends."])]
        translated_summary = sanitize_ai_text(translate_text("AI summary ready.", language))
        return {
            "insights": translated_insights,
            "suggested_actions": translated_actions,
            "summary": translated_summary,
        }

    def create_embedding(self, text: str) -> list[float]:
        if not text:
            return self._fallback_embedding
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        if not normalized:
            return self._fallback_embedding
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        values = []
        for i in range(self.EMBEDDING_DIMENSION):
            byte_idx = i % len(digest)
            values.append(round(digest[byte_idx] / 255.0, 6))
        return values

    def serialize_embedding(self, embedding: list[float]) -> str:
        return json.dumps([round(float(value), 6) for value in embedding])

    async def index_user_content(
        self, db: AsyncSession, user_id: int, content: str, title: str, source_type: str, source_id: int | None = None
    ) -> int:
        chunk_data: dict[str, Any] = {
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "content": content,
        }
        if self._pgvector_available:
            chunk_data["embedding"] = self.create_embedding(content)

        chunk = RAGChunk(**chunk_data)
        db.add(chunk)
        await db.flush()
        return chunk.id

    async def retrieve_context(self, db: AsyncSession, user_id: int, question: str, limit: int = 5) -> list[dict[str, Any]]:
        query_embedding = self.create_embedding(question)

        if self._pgvector_available:
            rows = await db.execute(
                select(RAGChunk)
                .where(RAGChunk.user_id == user_id)
                .order_by(func.rag_chunks.embedding.op('<->')(query_embedding))
                .limit(limit)
            )
            chunks = [{"title": r.title, "content": r.content} for r in rows.scalars().all()]
        else:
            rows = await db.execute(
                select(Document).where(Document.user_id == user_id).limit(limit * 3)
            )
            documents = rows.scalars().all()
            chunks = []
            for document in documents:
                content = " ".join(
                    filter(None, [document.original_filename, document.product_name, document.supplier_name, document.raw_ocr_text])
                )
                if content:
                    chunks.append({"title": document.original_filename, "content": content[:2000]})

        if not chunks:
            chunks = [
                {"title": "Farm knowledge", "content": "Use the farm's expense and inventory records to formulate an answer."}
            ]
        return chunks[:limit]

    async def augment_prompt(self, db: AsyncSession, user_id: int, question: str) -> str:
        chunks = await self.retrieve_context(db, user_id, question)
        return self.build_context_prompt(question, chunks)
