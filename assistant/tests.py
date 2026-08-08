from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from .models import MessTiming
from .graph import route_query, grade_documents, generate
from datetime import time


def mock_cohere_response(text):
    """Builds a fake Cohere v2 response object matching the shape our code expects
    (response.message.content[0].text), without hitting the real API."""
    mock_response = MagicMock()
    mock_response.message.content = [MagicMock(text=text)]
    return mock_response


class RouterTests(TestCase):
    @patch("assistant.graph.chat_with_retry")
    def test_routes_to_structured_db(self, mock_chat):
        mock_chat.return_value = mock_cohere_response("structured_db")

        state = {"question": "What time is breakfast?", "route": None}
        result = route_query(state)

        self.assertEqual(result["route"], "structured_db")

    @patch("assistant.graph.chat_with_retry")
    def test_invalid_route_falls_back_safely(self, mock_chat):
        # simulates the LLM returning something unexpected/malformed
        mock_chat.return_value = mock_cohere_response("some nonsense response")

        state = {"question": "anything", "route": None}
        result = route_query(state)

        self.assertEqual(result["route"], "llm_fallback")


class GradeDocumentsTests(TestCase):
    def test_structured_db_skips_grading(self):
        # confirms the cost-optimization fix — structured_db should never call the LLM
        state = {"route": "structured_db", "documents": ["some fact"], "question": "q"}
        with patch("assistant.graph.chat_with_retry") as mock_chat:
            result = grade_documents(state)
            mock_chat.assert_not_called()
        self.assertEqual(result["documents"], ["some fact"])

    @patch("assistant.graph.chat_with_retry")
    def test_vector_retrieve_filters_irrelevant_docs(self, mock_chat):
        mock_chat.return_value = mock_cohere_response("0")  # only doc 0 is relevant

        state = {
            "route": "vector_retrieve",
            "documents": ["relevant doc", "irrelevant doc"],
            "question": "q",
        }
        result = grade_documents(state)

        self.assertEqual(result["documents"], ["relevant doc"])


class StructuredDataTests(TestCase):
    def test_mess_timing_str(self):
        mt = MessTiming.objects.create(
            hall="Test Hall", meal="breakfast", start_time=time(7, 30), end_time=time(9, 30)
        )
        self.assertIn("Test Hall", str(mt))
        self.assertIn("Breakfast", str(mt))


class ChatViewAuthTests(TestCase):
    def test_chat_page_requires_login(self):
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 302)  # redirects to login, not accessible anonymously

    def test_chat_page_loads_when_logged_in(self):
        User.objects.create_user(username="chatuser", password="TestPass123!")
        self.client.login(username="chatuser", password="TestPass123!")
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)