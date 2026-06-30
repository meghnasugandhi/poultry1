"""End-to-end API smoke test for Poultry ERP."""

import asyncio
import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        email = "test@farm.com"
        password = "testpass123"

        # Register (ignore if exists)
        reg = await client.post("/auth/register", json={
            "email": email, "password": password,
            "owner_name": "Test Farmer", "farm_name": "Test Farm",
            "mobile_number": "9876543210", "state": "Karnataka",
            "district": "Bangalore", "address": "Test Address",
        })
        print("Register:", reg.status_code)

        login = await client.post("/auth/login/json", json={"email": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login: OK")

        # Inventory
        inv = await client.post("/inventory/", headers=headers, json={
            "category": "feed", "product_name": "Broiler Feed", "quantity": 100, "unit": "kg", "reorder_level": 20,
        })
        inv.raise_for_status()
        print("Inventory add: OK")

        # Finance
        tx = await client.post("/finance/transactions", headers=headers, json={
            "transaction_type": "expense", "expense_category": "feed", "amount": 5000, "description": "Feed purchase",
        })
        tx.raise_for_status()
        print("Finance add: OK")

        # Dashboard
        dash = await client.get("/dashboard/", headers=headers)
        dash.raise_for_status()
        d = dash.json()
        print(f"Dashboard: birds={d['total_birds']}, feed={d['feed_stock']}, P/L={d['profit_loss']}")

        # Calculator
        calc = await client.post("/calculator/calculate", headers=headers, json={
            "calculation_type": "fcr", "inputs": {"feed_consumed": 500, "weight_gain": 200},
        })
        calc.raise_for_status()
        print(f"Calculator FCR: {calc.json()['result']}")

        # Assistant
        chat = await client.post("/assistant/chat", headers=headers, json={"message": "How much feed stock remains?"})
        chat.raise_for_status()
        print(f"Assistant: {chat.json()['message'][:80]}...")

        chat_add = await client.post("/assistant/chat", headers=headers, json={"message": "Add 200 kg broiler feed"})
        chat_add.raise_for_status()
        print(f"Assistant add stock: {chat_add.json()['message']}")

        chat_remove = await client.post("/assistant/chat", headers=headers, json={"message": "Remove 50 kg broiler feed"})
        chat_remove.raise_for_status()
        print(f"Assistant remove stock: {chat_remove.json()['message']}")

        # Translations
        tr = await client.get("/translations/ui", headers=headers)
        tr.raise_for_status()
        print(f"Translations: {len(tr.json()['labels'])} labels")

        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
