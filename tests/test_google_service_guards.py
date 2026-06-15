import importlib.util
import unittest
from unittest import mock


class GoogleServiceGuardTests(unittest.TestCase):
    def require_google_modules(self):
        required_modules = [
            "google_auth_oauthlib",
            "googleapiclient",
            "mistralai",
            "openai",
        ]
        missing_modules = [
            name for name in required_modules
            if importlib.util.find_spec(name) is None
        ]
        if missing_modules:
            self.skipTest(
                "Dépendances Google/OpenAI absentes: "
                + ", ".join(missing_modules)
            )

    def test_google_service_build_failure_returns_none(self):
        self.require_google_modules()

        import assistant.google.google_assistant as google_assistant

        assistant = google_assistant.GoogleAssistant.__new__(
            google_assistant.GoogleAssistant
        )
        assistant.error_message = ""
        assistant.creds = mock.Mock(valid=True)
        response = mock.Mock(status=503, reason="backendError")
        error = google_assistant.HttpError(response, b"backendError")

        with mock.patch.object(
            google_assistant,
            "build",
            side_effect=error,
        ):
            service = assistant.get_service("gmail", "v1")

        self.assertIsNone(service)
        self.assertIn("service gmail", assistant.error_message)

    def test_google_operations_report_missing_service(self):
        self.require_google_modules()

        import assistant.google.google_assistant as google_assistant

        assistant = google_assistant.GoogleAssistant.__new__(
            google_assistant.GoogleAssistant
        )
        assistant.error_message = (
            "Authentification Google interactive indisponible."
        )
        assistant.gmail_service = None
        assistant.calendar_service = None
        assistant.tasks_service = None

        self.assertEqual({}, assistant.collect_emails())
        self.assertEqual(
            "Authentification Google interactive indisponible.",
            assistant.create_google_task("Acheter du lait", ""),
        )
        self.assertEqual(
            "Authentification Google interactive indisponible.",
            assistant.create_calendar_event(
                "Réunion",
                "30 minutes",
                ["alice@example.test"],
                "2026-01-01",
                "09:00-09:30",
                "Paris",
            ),
        )
        with mock.patch.object(
            google_assistant,
            "create_chat_completion",
        ) as create_chat_completion:
            self.assertEqual(
                ["Authentification Google interactive indisponible."],
                assistant.create_email(
                    "alice@example.test",
                    "Sujet",
                ),
            )
        create_chat_completion.assert_not_called()


if __name__ == "__main__":
    unittest.main()
