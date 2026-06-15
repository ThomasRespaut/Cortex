import unittest

from function_calling import execute_tool, parse_tool_call


class FunctionCallingGuardTests(unittest.TestCase):
    def test_parse_tool_call_supports_list_arguments(self):
        parsed = parse_tool_call(
            "[create_calendar_event name='Réunion' "
            "participants=['alice@example.com', 'bob@example.com'] "
            "duration='1h']"
        )

        self.assertEqual(
            parsed,
            (
                "create_calendar_event",
                {
                    "name": "Réunion",
                    "participants": [
                        "alice@example.com",
                        "bob@example.com",
                    ],
                    "duration": "1h",
                },
            ),
        )

    def test_parse_tool_call_supports_brackets_inside_text_values(self):
        parsed = parse_tool_call(
            "[create_google_task task_title='Lire [RFC] parser' task_notes='']"
        )

        self.assertEqual(
            parsed,
            (
                "create_google_task",
                {
                    "task_title": "Lire [RFC] parser",
                    "task_notes": "",
                },
            ),
        )

    def test_parse_tool_call_rejects_duplicate_arguments(self):
        with self.assertRaisesRegex(ValueError, "Argument dupliqué: title"):
            parse_tool_call(
                "[create_calendar_event title='Standup' title='Retro']"
            )

    def test_execute_tool_reports_duplicate_arguments_as_invalid_command(self):
        result = execute_tool(
            "[create_google_task title='Courses' title='Doublon']",
            tools={"create_google_task": lambda title: title},
        )

        self.assertIn("Commande invalide:", result)
        self.assertIn("Argument dupliqué: title", result)

    def test_execute_tool_passes_list_arguments_to_tool(self):
        result = execute_tool(
            "[create_calendar_event name='Réunion' "
            "participants=['alice@example.com', 'bob@example.com'] "
            "duration='1h']",
            tools={
                "create_calendar_event": (
                    lambda name, participants, duration: (
                        f"{name}|{len(participants)}|{duration}"
                    )
                )
            },
        )

        self.assertEqual("Réunion|2|1h", result)


if __name__ == "__main__":
    unittest.main()
