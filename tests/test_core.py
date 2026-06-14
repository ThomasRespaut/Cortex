import importlib.util
import os
import subprocess
import sys
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

    def test_execute_tool_ignores_unexpected_arguments(self):
        result = execute_tool(
            "[add left=2 right=5 unused='ignored']",
            tools={"add": lambda left, right: left + right},
        )
        self.assertEqual(result, 7)

    def test_execute_tool_still_reports_missing_required_arguments(self):
        result = execute_tool(
            "[add left=2]",
            tools={"add": lambda left, right: left + right},
        )
        self.assertIn("Arguments invalides pour l'outil 'add'", result)

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


class RepositoryHygieneTests(unittest.TestCase):
    def test_generated_and_sensitive_files_are_not_tracked(self):
        result = subprocess.run(
            ["git", "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_files = [path.replace("\\", "/") for path in result.stdout.splitlines()]
        forbidden = []

        for path in tracked_files:
            path_with_slashes = f"/{path}"
            name = Path(path).name
            if (
                path == ".env"
                or path == ".cache"
                or path == "oauth2/.cache"
                or path == "output.wav"
                or path.startswith("logs/")
                or path.endswith("/token_info.json")
                or path == "token_info.json"
                or "/__pycache__/" in path_with_slashes
                or name.endswith((".pyc", ".pyo", ".log"))
            ):
                forbidden.append(path)

        self.assertEqual([], forbidden)

    def test_google_assistant_imports_without_openai_key(self):
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

        environment = os.environ.copy()
        environment["OPENAI_API_KEY"] = ""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import assistant.google.google_assistant as module; "
                "assert module.client is None",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual("", result.stderr)

    def test_apple_assistant_skips_login_without_credentials(self):
        if importlib.util.find_spec("pyicloud") is None:
            self.skipTest("Dépendance pyicloud absente.")

        environment = os.environ.copy()
        environment["apple_username"] = ""
        environment["apple_password"] = ""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from assistant.apple.iphone import AppleAssistant; "
                "assistant = AppleAssistant(); "
                "assert assistant.client is None; "
                "assert 'non configurés' in assistant.error_message",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual("", result.stderr)

    def test_idfm_assistant_reports_missing_api_key(self):
        if importlib.util.find_spec("requests") is None:
            self.skipTest("Dépendance requests absente.")

        environment = os.environ.copy()
        environment["IDFM_API_KEY"] = ""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from assistant.ratp.ratp_assistant import IDFMAssistant; "
                "assistant = IDFMAssistant(); "
                "assert assistant.get_coords('Paris') is None; "
                "assert assistant.calculate_route('Paris', 'Lyon') == assistant.error_message",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual("", result.stderr)


if __name__ == "__main__":
    unittest.main()
