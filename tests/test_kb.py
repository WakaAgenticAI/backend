from __future__ import annotations
from unittest.mock import patch, MagicMock

from app.kb import service as kb_service


def test_kb_upsert_and_query():
    coll = MagicMock()
    with patch("app.kb.service.get_collection", return_value=coll):
        n = kb_service.kb_upsert(
            "faq",
            [
                {"id": "1", "text": "What is WakaAgent?", "metadata": {"tag": "faq"}},
                {"id": "2", "text": "How to create order?", "metadata": {"tag": "orders"}},
            ],
        )
        assert n == 2
        coll.upsert.assert_called_once()

        coll.query.return_value = {
            "ids": [["2"]],
            "documents": [["How to create order?"]],
            "metadatas": [[{"tag": "orders"}]],
        }
        res = kb_service.kb_query("faq", "create order", k=1)
        assert res == [
            {"id": "2", "text": "How to create order?", "metadata": {"tag": "orders"}}
        ]
