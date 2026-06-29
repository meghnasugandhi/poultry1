"""Extended API smoke test."""

import asyncio
import os
import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        login = await client.post("/auth/login/json", json={"email": "test@farm.com", "password": "testpass123"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Report PDF
        rpt = await client.post("/reports/generate", headers=headers, json={
            "report_type": "inventory", "export_format": "pdf",
        })
        rpt.raise_for_status()
        assert len(rpt.content) > 100
        print("Report PDF: OK")

        # Document upload with text file
        os.makedirs("uploads", exist_ok=True)
        test_file = "uploads/test_invoice.txt"
        with open(test_file, "w") as f:
            f.write("Suguna Feeds Pvt Ltd\nInvoice No: INV-2024-001\nTotal: Rs. 15,000\nQty: 500 kg\n10 bags\nSupplier: Suguna")
        with open(test_file, "rb") as f:
            doc = await client.post("/documents/upload", headers=headers, files={"file": ("invoice.txt", f, "text/plain")}, data={"document_type": "feed_bill"})
        doc.raise_for_status()
        d = doc.json()
        print(f"Document OCR: confidence={d.get('ocr_confidence')}, company={d.get('company_name')}")

        # Notifications (triggered via dashboard)
        await client.get("/dashboard/", headers=headers)
        notifs = await client.get("/notifications/", headers=headers)
        notifs.raise_for_status()
        print(f"Notifications: {len(notifs.json())} items")

        # Voice parse
        voice = await client.post("/voice/parse-command", headers=headers, json={"text": "add 25 kg layer feed"})
        voice.raise_for_status()
        print(f"Voice parse: {voice.json()}")

        # Inventory voice entry
        ventry = await client.post("/inventory/voice-entry", headers=headers, json={"text": "add 25 kg layer feed"})
        ventry.raise_for_status()
        print(f"Voice inventory entry: {ventry.json()['product_name']}")

        # Settings update
        settings = await client.put("/auth/settings", headers=headers, json={"preferred_language": "kn", "voice_enabled": True})
        settings.raise_for_status()
        print(f"Settings: language={settings.json()['preferred_language']}")

        # Profile update
        prof = await client.put("/auth/me", headers=headers, json={"current_bird_count": 5000, "total_capacity": 10000})
        prof.raise_for_status()
        print(f"Profile: birds={prof.json()['current_bird_count']}")

        print("\nExtended tests passed!")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
