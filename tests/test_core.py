import unittest
from pathlib import Path

from assistant.functions import generate_random_number
from function_calling import execute_tool, parse_tool_call
from tools import build_finetune_dataset, validate_finetune_dataset


class FunctionTests(unittest.TestCase):
    def test_random_number_accepts_string_bounds(self):
        result = generate_random_number("4", "4")
        self.assertEqual(result, 4)

    def test_random_number_rejects_inverted_bounds(self):
        with self.assertRaises(ValueError):
            generate_random_number(5, 1)


class ToolCallTests(unittest.TestCase):
    def test_parse_tool_call_preserves_spaces(self):
        parsed = parse_tool_call(
            "Je lance la musique [play_track track_name='Sois pas timide']"
        )
        self.assertEqual(
            parsed,
            ("play_track", {"track_name": "Sois pas timide"}),
        )

    def test_parse_tool_call_coerces_basic_types(self):
        parsed = parse_tool_call(
            "[demo count=3 ratio=0.5 enabled=true optional=null]"
        )
        self.assertEqual(
            parsed,
            (
                "demo",
                {
                    "count": 3,
                    "ratio": 0.5,
                    "enabled": True,
                    "optional": None,
                },
            ),
        )

    def test_execute_tool_uses_injected_registry(self):
        result = execute_tool(
            "[add left=2 right=5]",
            tools={"add": lambda left, right: left + right},
        )
        self.assertEqual(result, 7)

    def test_execute_tool_maps_legacy_music_alias(self):
        result = execute_tool(
            "[play_music genre='pop']",
            tools={
                "play_recommendations_track": lambda genre_name: (
                    f"genre:{genre_name}"
                )
            },
        )
        self.assertEqual(result, "genre:pop")

    def test_execute_tool_maps_legacy_task_alias(self):
        result = execute_tool(
            "[add_task list='Acheter du lait']",
            tools={
                "create_google_task": lambda task_title, task_notes="": (
                    f"{task_title}|{task_notes}"
                )
            },
        )
        self.assertEqual(result, "Acheter du lait|")

    def test_execute_tool_reports_unknown_tool(self):
        result = execute_tool("[missing]", tools={})
        self.assertEqual(result, "Outil 'missing' non reconnu.")


class InterfaceAssetTests(unittest.TestCase):
    def test_complete_v2_icon_set_exists(self):
        icon_dir = Path("app/Images/app_icons_v2")
        icons = list(icon_dir.glob("*.png"))
        self.assertEqual(len(icons), 22)
        self.assertTrue(all(icon.stat().st_size > 0 for icon in icons))


class ToolingDefaultsTests(unittest.TestCase):
    def test_finetune_tooling_defaults_to_v3_dataset(self):
        expected = Path("training/finetune_cortex_v3")
        self.assertEqual(
            build_finetune_dataset.DEFAULT_OUTPUT.relative_to(
                build_finetune_dataset.ROOT
            ),
            expected,
        )
        self.assertEqual(
            validate_finetune_dataset.DEFAULT_DATASET.relative_to(
                validate_finetune_dataset.ROOT
            ),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
