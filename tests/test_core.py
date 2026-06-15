import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

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

    def test_missing_icon_uses_pygame_fallback_surface(self):
        import pygame
        from app.screen_assets import load_icon_or_fallback

        pygame.font.init()
        with mock.patch("builtins.print"):
            icon = load_icon_or_fallback("tests/missing-icon.png", "Cortex", size=64)

        self.assertEqual((64, 64), icon.get_size())
        self.assertGreater(icon.get_bounding_rect().width, 0)

    def test_icon_fallback_works_without_display(self):
        import pygame
        from app.screen_assets import make_icon_fallback

        pygame.font.init()
        icon = make_icon_fallback("Réglages", size=48)

        self.assertEqual((48, 48), icon.get_size())
        self.assertGreater(icon.get_bounding_rect().height, 0)

    def test_pygame_asset_path_uses_linux_case(self):
        from app.screen_assets import asset_path

        path = Path(asset_path("backgrounds", "horloge.png"))

        self.assertEqual(Path("app/Images/backgrounds/horloge.png"), path)
        self.assertTrue(path.is_file())

    def test_legacy_pygame_modules_do_not_use_lowercase_image_dir(self):
        modules = [
            Path("app/app_calendrier.py"),
            Path("app/app_horloge.py"),
            Path("app/app_jeu.py"),
            Path("app/app_message.py"),
            Path("app/app_musique.py"),
            Path("app/app_reglage.py"),
            Path("app/app_sante.py"),
            Path("app/app_transport.py"),
        ]

        for module in modules:
            content = module.read_text(encoding="utf-8")
            self.assertNotIn('"images"', content, module)
            self.assertNotIn("'images'", content, module)
            self.assertNotIn("app/images", content.lower(), module)

    def test_legacy_pygame_modules_use_shared_pointer_helper(self):
        modules = [
            Path("app/app_calendrier.py"),
            Path("app/app_horloge.py"),
            Path("app/app_jeu.py"),
            Path("app/app_message.py"),
            Path("app/app_musique.py"),
            Path("app/app_reglage.py"),
            Path("app/app_sante.py"),
            Path("app/app_transport.py"),
        ]

        for module in modules:
            content = module.read_text(encoding="utf-8")
            self.assertIn("pointer_down_position", content, module)
            self.assertIn("circular_menu_layout", content, module)
            self.assertIn("screen.get_size()", content, module)
            self.assertNotIn("event.pos", content, module)
            self.assertNotIn("pygame.display.Info", content, module)
            self.assertNotIn("screen_width/2-200", content, module)
            self.assertNotIn("500, 400", content, module)

    def test_legacy_pygame_modules_can_exit_after_one_frame(self):
        modules = [
            Path("app/app_calendrier.py"),
            Path("app/app_horloge.py"),
            Path("app/app_jeu.py"),
            Path("app/app_message.py"),
            Path("app/app_musique.py"),
            Path("app/app_reglage.py"),
            Path("app/app_sante.py"),
            Path("app/app_transport.py"),
        ]

        for module in modules:
            content = module.read_text(encoding="utf-8")
            self.assertIn("env_bool", content, module)
            self.assertIn("CORTEX_EXIT_AFTER_FRAME", content, module)

    def test_bdd_screen_uses_responsive_touch_layout(self):
        content = Path("app/app_bdd.py").read_text(encoding="utf-8")

        self.assertIn("import math", content)
        self.assertIn("from database.database import Neo4jDatabase", content)
        self.assertIn("circular_menu_layout", content)
        self.assertIn("pointer_down_position", content)
        self.assertIn("screen.get_size()", content)
        self.assertIn("CORTEX_EXIT_AFTER_FRAME", content)
        self.assertIn("selection_pointer", content)
        self.assertIn("moved_fingers", content)
        self.assertNotIn("event.pos", content)
        self.assertNotIn("sub_event.pos", content)
        self.assertNotIn("exit()", content)
        self.assertNotIn("pygame.quit()", content)
        self.assertNotIn("+ 400 + offset_x", content)
        self.assertNotIn("+ 300 + offset_y", content)
        self.assertNotIn("pygame.Rect(50, 500", content)

    def test_circular_menu_layout_keeps_controls_inside_round_viewport(self):
        import pygame
        from app.screen_config import circular_menu_layout

        quit_rect, item_rects = circular_menu_layout(480, 480)
        center = pygame.Vector2(240, 240)
        radius = 240

        self.assertEqual(4, len(item_rects))
        for rect in [quit_rect, *item_rects]:
            self.assertGreaterEqual(rect.left, 0)
            self.assertGreaterEqual(rect.top, 0)
            self.assertLessEqual(rect.right, 480)
            self.assertLessEqual(rect.bottom, 480)
            for point in (rect.topleft, rect.topright, rect.bottomleft, rect.bottomright):
                self.assertLessEqual(
                    pygame.Vector2(point).distance_to(center),
                    radius,
                    rect,
                )

    def test_touch_rotation_maps_circular_screen_coordinates(self):
        from app.screen_config import rotated_touch_position

        width = 400
        height = 400
        self.assertEqual(
            (100.0, 300.0),
            rotated_touch_position(0.25, 0.75, width, height, 0),
        )
        self.assertEqual(
            (100.0, 100.0),
            rotated_touch_position(0.25, 0.75, width, height, 90),
        )
        self.assertEqual(
            (300.0, 100.0),
            rotated_touch_position(0.25, 0.75, width, height, 180),
        )
        self.assertEqual(
            (300.0, 300.0),
            rotated_touch_position(0.25, 0.75, width, height, 270),
        )

    def test_screen_config_parses_environment_defaults(self):
        from app import screen_config

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_TEST_TRUE": "oui",
                "CORTEX_TEST_FALSE": "off",
                "CORTEX_TEST_INT": "abc",
                "CORTEX_TOUCH_ROTATION": "180",
                "CORTEX_SCREEN_SIZE": "480x480",
            },
        ):
            self.assertTrue(screen_config.env_bool("CORTEX_TEST_TRUE"))
            self.assertFalse(screen_config.env_bool("CORTEX_TEST_FALSE", True))
            self.assertEqual(7, screen_config.env_int("CORTEX_TEST_INT", 7))
            self.assertEqual(
                (480, 480),
                screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
            )
            self.assertEqual(
                (300.0, 100.0),
                screen_config.rotated_touch_position(0.25, 0.75, 400, 400),
            )

    def test_screen_config_rejects_invalid_screen_size(self):
        from app import screen_config

        for value in ("large", "480", "0x480", "480x0", "480xabc"):
            with mock.patch.dict(os.environ, {"CORTEX_SCREEN_SIZE": value}):
                self.assertEqual(
                    (900, 900),
                    screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
                )

    def test_pointer_helpers_support_mouse_and_rotated_touch(self):
        import pygame
        from app.screen_config import (
            pointer_down_position,
            pointer_move_position,
            pointer_up_position,
        )

        mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (12, 34)},
        )
        mouse_motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (56, 78)},
        )
        mouse_up_event = pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (90, 123)},
        )
        touch_event = pygame.event.Event(
            pygame.FINGERDOWN,
            {"x": 0.25, "y": 0.75},
        )
        touch_motion_event = pygame.event.Event(
            pygame.FINGERMOTION,
            {"x": 0.5, "y": 0.25},
        )
        touch_up_event = pygame.event.Event(
            pygame.FINGERUP,
            {"x": 0.75, "y": 0.5},
        )
        ignored_mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 2, "pos": (12, 34)},
        )

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_ROTATION": "180"}):
            self.assertEqual((12, 34), pointer_down_position(mouse_event, 400, 400))
            self.assertIsNone(pointer_down_position(ignored_mouse_event, 400, 400))
            self.assertEqual((56, 78), pointer_move_position(mouse_motion_event, 400, 400))
            self.assertEqual((90, 123), pointer_up_position(mouse_up_event, 400, 400))
            self.assertEqual(
                (300.0, 100.0),
                pointer_down_position(touch_event, 400, 400),
            )
            self.assertEqual(
                (200.0, 300.0),
                pointer_move_position(touch_motion_event, 400, 400),
            )
            self.assertEqual(
                (100.0, 200.0),
                pointer_up_position(touch_up_event, 400, 400),
            )

    def test_prepare_screenshot_path_creates_parent_directory(self):
        from app.screen_config import prepare_screenshot_path

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "screen.png"

            self.assertEqual(str(target), prepare_screenshot_path(target))
            self.assertTrue(target.parent.is_dir())

    def test_cortex_view_activation_supports_touch_suggestions(self):
        import pygame
        from app.app_cortex import CortexView

        view = CortexView.__new__(CortexView)
        view.running = True
        prompts = []
        view.run_query = lambda prompt=None: prompts.append(prompt)
        suggestions = [(pygame.Rect(20, 20, 80, 40), "Résumé du jour")]

        view.activate_at(
            (40, 40),
            back_center=(200, 200),
            back_radius=20,
            orb_center=(300, 300),
            orb_radius=20,
            suggestion_rects=suggestions,
        )

        self.assertEqual(["Résumé du jour"], prompts)
        self.assertTrue(view.running)

    def test_cortex_view_activation_supports_touch_back_button(self):
        from app.app_cortex import CortexView

        view = CortexView.__new__(CortexView)
        view.running = True
        view.run_query = lambda prompt=None: self.fail("query should not run")

        view.activate_at(
            (10, 10),
            back_center=(10, 10),
            back_radius=20,
            orb_center=(300, 300),
            orb_radius=20,
            suggestion_rects=[],
        )

        self.assertFalse(view.running)

    def test_feature_activation_supports_touch_settings_toggle(self):
        import pygame
        from app.feature_shell import activate_feature_at

        class CortexState:
            local_mode = True

        cards = ["Mode de calcul"]
        running = activate_feature_at(
            CortexState,
            "Réglages",
            position=(25, 25),
            back_center=(200, 200),
            back_radius=20,
            card_rects=[pygame.Rect(0, 0, 80, 50)],
            cards=cards,
        )

        self.assertTrue(running)
        self.assertFalse(CortexState.local_mode)
        self.assertEqual("Mode en ligne", cards[0])


class ToolingDefaultsTests(unittest.TestCase):
    def test_raspberry_pi_launcher_defaults_to_screen_kiosk(self):
        launcher = Path("scripts/launch_raspberry_pi.sh")
        content = launcher.read_text(encoding="utf-8")

        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", content)
        self.assertIn("exec \"$PYTHON_BIN\" Screen.py", content)
        self.assertIn("CORTEX_FULLSCREEN=\"${CORTEX_FULLSCREEN:-true}\"", content)
        self.assertIn("CORTEX_HIDE_CURSOR=\"${CORTEX_HIDE_CURSOR:-true}\"", content)
        self.assertIn("SDL_VIDEODRIVER=\"${SDL_VIDEODRIVER:-kmsdrm}\"", content)
        self.assertNotIn(". \".env\"", content)
        self.assertNotIn("source .env", content)
        self.assertNotIn("OPENAI_API_KEY=", content)
        self.assertNotIn("MISTRAL_API_KEY=", content)

    def test_obsolete_pygame_entrypoints_are_removed(self):
        self.assertFalse(Path("app/Screen3.py").exists())
        self.assertFalse(Path("app/main_screen.py").exists())

    def test_raspberry_pi_launcher_uses_lf_line_endings(self):
        content = Path("scripts/launch_raspberry_pi.sh").read_bytes()

        self.assertNotIn(b"\r\n", content)

    def test_raspberry_pi_setup_script_uses_base_requirements(self):
        script = Path("scripts/setup_raspberry_pi.sh")
        content = script.read_text(encoding="utf-8")

        self.assertTrue(script.is_file())
        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", content)
        self.assertIn("requirements-raspberry-pi.txt", content)
        self.assertIn("tools/raspberry_pi_preflight.py", content)
        self.assertIn("CORTEX_SCREENSHOT_PATH=artifacts/screen-smoke.png", content)
        self.assertIn("tools/smoke_legacy_pygame_screens.py", content)

    def test_github_actions_runs_pygame_smokes(self):
        workflow = Path(".github/workflows/core-checks.yml")
        content = workflow.read_text(encoding="utf-8")

        self.assertIn("python Screen.py", content)
        self.assertIn("tools/verify_screen_smoke.py", content)
        self.assertIn("tools/raspberry_pi_preflight.py", content)
        self.assertIn("tools/smoke_legacy_pygame_screens.py", content)

    def test_raspberry_pi_requirements_exclude_heavy_local_model_stack(self):
        requirements = Path("requirements-raspberry-pi.txt").read_text(encoding="utf-8")

        self.assertIn("pygame==2.6.1", requirements)
        self.assertIn("python-dotenv==1.0.1", requirements)
        self.assertNotIn("torch==", requirements)
        self.assertNotIn("transformers==", requirements)
        self.assertNotIn("peft==", requirements)

    def test_raspberry_pi_systemd_service_uses_launcher(self):
        service = Path("deploy/raspberry-pi/cortex.service.example")
        content = service.read_text(encoding="utf-8")

        self.assertIn("WorkingDirectory=/home/pi/Cortex", content)
        self.assertIn(
            "ExecStart=/home/pi/Cortex/scripts/launch_raspberry_pi.sh",
            content,
        )
        self.assertIn("Restart=on-failure", content)

    def test_raspberry_pi_service_installer_generates_systemd_unit(self):
        installer = Path("deploy/raspberry-pi/install_service.sh")
        content = installer.read_text(encoding="utf-8")

        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", content)
        self.assertIn("CORTEX_PROJECT_DIR", content)
        self.assertIn("CORTEX_SERVICE_USER", content)
        self.assertIn("scripts/launch_raspberry_pi.sh", content)
        self.assertIn("systemctl daemon-reload", content)
        self.assertIn("CORTEX_START_SERVICE:-false", content)
        self.assertNotIn("OPENAI_API_KEY=", content)
        self.assertNotIn("MISTRAL_API_KEY=", content)

    def test_raspberry_pi_service_installer_uses_lf_line_endings(self):
        content = Path("deploy/raspberry-pi/install_service.sh").read_bytes()

        self.assertNotIn(b"\r\n", content)

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

    def test_dataset_validator_reports_malformed_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_dir = Path(temp_dir)
            (dataset_dir / "train.jsonl").write_text(
                "{invalid json\n",
                encoding="utf-8",
            )
            (dataset_dir / "eval.jsonl").write_text(
                '{"text": 123}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/validate_finetune_dataset.py",
                    "--dataset-dir",
                    str(dataset_dir),
                ],
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("JSON invalide", result.stdout)
        self.assertIn("champ text invalide", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_screen_smoke_validator_accepts_rich_capture(self):
        import pygame
        from tools.verify_screen_smoke import validate_screen_image

        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "screen.png"
                surface = pygame.Surface((320, 320))
                surface.fill((6, 10, 28))
                for index in range(10):
                    pygame.draw.circle(
                        surface,
                        (40 + index * 20, 90 + index * 9, 180),
                        (32 + index * 28, 160),
                        18,
                    )
                pygame.image.save(surface, target)

                stats = validate_screen_image(target, min_width=300, min_height=300)
        finally:
            pygame.quit()

        self.assertGreaterEqual(stats["unique_colors"], 8)
        self.assertGreaterEqual(stats["bright_pixels"], 12)

    def test_screen_smoke_validator_rejects_blank_capture(self):
        import pygame
        from tools.verify_screen_smoke import validate_screen_image

        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "blank.png"
                surface = pygame.Surface((320, 320))
                surface.fill((0, 0, 0))
                pygame.image.save(surface, target)

                with self.assertRaises(ValueError):
                    validate_screen_image(target, min_width=300, min_height=300)
        finally:
            pygame.quit()

    def test_raspberry_pi_preflight_accepts_repo_layout(self):
        from tools.raspberry_pi_preflight import collect_preflight_errors

        errors = collect_preflight_errors(
            ".",
            check_pygame=False,
            require_executable=False,
        )

        self.assertEqual([], errors)

    def test_env_example_documents_raspberry_pi_screen_settings(self):
        content = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("CORTEX_FULLSCREEN=true", content)
        self.assertIn("CORTEX_HIDE_CURSOR=true", content)
        self.assertIn("CORTEX_SCREEN_SIZE=", content)
        self.assertIn("CORTEX_TOUCH_ROTATION=0", content)

    def test_env_example_documents_oauth_token_overrides(self):
        content = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("SPOTIFY_TOKEN_FILE=", content)
        self.assertIn("GOOGLE_CREDENTIALS_FILE=", content)
        self.assertIn("GOOGLE_TOKEN_FILE=", content)

    def test_raspberry_pi_preflight_reports_missing_assets(self):
        from tools.raspberry_pi_preflight import collect_preflight_errors

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative_path in (
                ".env.example",
                "Screen.py",
                "requirements-raspberry-pi.txt",
                "scripts/launch_raspberry_pi.sh",
                "scripts/setup_raspberry_pi.sh",
                "deploy/raspberry-pi/install_service.sh",
                "deploy/raspberry-pi/cortex.service.example",
            ):
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# placeholder\n", encoding="utf-8")

            errors = collect_preflight_errors(
                root,
                check_pygame=False,
                require_executable=False,
            )

        self.assertTrue(any("Asset manquant" in error for error in errors))


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

    def test_google_assistant_skips_oauth_without_client_secret(self):
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

        import assistant.google.google_assistant as google_assistant

        with (
            mock.patch.object(
                google_assistant,
                "CREDENTIALS_FILE",
                "tests/missing_google_secret.json",
            ),
            mock.patch.object(
                google_assistant,
                "TOKEN_FILE",
                "tests/missing_token_google.json",
            ),
            mock.patch.object(
                google_assistant.InstalledAppFlow,
                "from_client_secrets_file",
            ) as from_client_secrets_file,
        ):
            assistant = google_assistant.GoogleAssistant()

        self.assertIsNone(assistant.creds)
        self.assertIsNone(assistant.gmail_service)
        self.assertIsNone(assistant.calendar_service)
        self.assertIsNone(assistant.tasks_service)
        self.assertIn("google_secret", assistant.error_message)
        from_client_secrets_file.assert_not_called()

    def test_google_assistant_skips_oauth_when_non_interactive(self):
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

        import assistant.google.google_assistant as google_assistant

        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_file = Path(temp_dir) / "google_secret.json"
            credentials_file.write_text("{}", encoding="utf-8")
            with (
                mock.patch.object(
                    google_assistant,
                    "CREDENTIALS_FILE",
                    str(credentials_file),
                ),
                mock.patch.object(
                    google_assistant,
                    "TOKEN_FILE",
                    "tests/missing_token_google.json",
                ),
                mock.patch.object(
                    google_assistant.sys.stdin,
                    "isatty",
                    return_value=False,
                ),
                mock.patch.object(
                    google_assistant.InstalledAppFlow,
                    "from_client_secrets_file",
                ) as from_client_secrets_file,
            ):
                assistant = google_assistant.GoogleAssistant()

        self.assertIsNone(assistant.creds)
        self.assertIsNone(assistant.gmail_service)
        self.assertIn("interactive indisponible", assistant.error_message)
        from_client_secrets_file.assert_not_called()

    def test_google_assistant_handles_invalid_token_file(self):
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

        import assistant.google.google_assistant as google_assistant

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token_google.json"
            token_file.write_text("{invalid json", encoding="utf-8")
            with (
                mock.patch.object(
                    google_assistant,
                    "TOKEN_FILE",
                    str(token_file),
                ),
                mock.patch.object(
                    google_assistant,
                    "CREDENTIALS_FILE",
                    "tests/missing_google_secret.json",
                ),
                mock.patch.object(
                    google_assistant.InstalledAppFlow,
                    "from_client_secrets_file",
                ) as from_client_secrets_file,
            ):
                assistant = google_assistant.GoogleAssistant()

        self.assertIsNone(assistant.creds)
        self.assertIsNone(assistant.gmail_service)
        self.assertIn("google_secret", assistant.error_message)
        from_client_secrets_file.assert_not_called()

    def test_google_assistant_save_token_creates_parent_directory(self):
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

        import assistant.google.google_assistant as google_assistant

        class FakeCredentials:
            def to_json(self):
                return '{"token": "google-token"}'

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "nested" / "token_google.json"
            assistant = google_assistant.GoogleAssistant.__new__(
                google_assistant.GoogleAssistant
            )
            assistant.error_message = ""
            with mock.patch.object(
                google_assistant,
                "TOKEN_FILE",
                str(token_file),
            ):
                self.assertTrue(assistant.save_token(FakeCredentials()))
                self.assertTrue(token_file.is_file())
                self.assertEqual(
                    '{"token": "google-token"}',
                    token_file.read_text(encoding="utf-8"),
                )
        self.assertEqual("", assistant.error_message)

    def test_google_assistant_refresh_keeps_credentials_if_save_fails(self):
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

        import assistant.google.google_assistant as google_assistant

        class FakeCredentials:
            expired = True
            valid = False
            refresh_token = "refresh-placeholder"

            def refresh(self, request):
                self.expired = False
                self.valid = True

            def to_json(self):
                return '{"token": "google-token"}'

        assistant = google_assistant.GoogleAssistant.__new__(
            google_assistant.GoogleAssistant
        )
        assistant.error_message = ""
        assistant.load_token = lambda: FakeCredentials()

        with mock.patch.object(
            google_assistant.Path,
            "write_text",
            side_effect=OSError("disk full"),
        ):
            creds = assistant.get_google_token()

        self.assertIsNotNone(creds)
        self.assertTrue(creds.valid)
        self.assertIn(
            "Impossible d'enregistrer le token Google",
            assistant.error_message,
        )

    def test_google_decode_message_body_ignores_invalid_base64(self):
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

        import assistant.google.google_assistant as google_assistant

        assistant = google_assistant.GoogleAssistant.__new__(
            google_assistant.GoogleAssistant
        )

        self.assertIsNone(assistant.decode_message_body("***", "text/plain"))
        self.assertIsNone(
            assistant.decode_message_body("__8=", "text/plain")
        )
        self.assertIsNone(assistant.decode_message_body("PGI+", "text/html"))

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

    def test_apple_assistant_skips_2fa_prompt_when_non_interactive(self):
        if importlib.util.find_spec("pyicloud") is None:
            self.skipTest("Dépendance pyicloud absente.")

        import assistant.apple.iphone as iphone

        class FakePyiCloudService:
            requires_2fa = True

            def __init__(self, username, password):
                self.username = username
                self.password = password

        with (
            mock.patch.object(iphone, "PyiCloudService", FakePyiCloudService),
            mock.patch.object(iphone.sys.stdin, "isatty", return_value=False),
            mock.patch.dict(
                os.environ,
                {
                    "apple_username": "user@example.test",
                    "apple_password": "password-placeholder",
                },
            ),
            mock.patch("builtins.input") as input_prompt,
        ):
            assistant = iphone.AppleAssistant()

        self.assertIsNone(assistant.client)
        self.assertIn("2FA interactive indisponible", assistant.error_message)
        input_prompt.assert_not_called()

    def test_apple_location_skips_maps_without_api_key(self):
        if importlib.util.find_spec("pyicloud") is None:
            self.skipTest("Dépendance pyicloud absente.")

        from assistant.apple.iphone import AppleAssistant

        class FakePhone:
            def location(self):
                return {"latitude": 48.8566, "longitude": 2.3522}

        class FakeClient:
            iphone = FakePhone()

        assistant = AppleAssistant.__new__(AppleAssistant)
        assistant.client = FakeClient()
        assistant.maps_api_key = ""
        result = assistant.get_location()
        self.assertEqual("success", result["status"])
        self.assertEqual("MAPS_API_KEY n'est pas configurée.", result["address"])

    def test_apple_weather_reports_missing_api_key(self):
        if importlib.util.find_spec("pyicloud") is None:
            self.skipTest("Dépendance pyicloud absente.")

        from assistant.apple.iphone import AppleAssistant

        assistant = AppleAssistant.__new__(AppleAssistant)
        assistant.openweathermap_api_key = ""
        assistant.get_location = lambda: {
            "status": "success",
            "latitude": 48.8566,
            "longitude": 2.3522,
        }
        result = assistant.get_weather()
        self.assertEqual("error", result["status"])
        self.assertEqual(
            "OPENWEATHERMAP_API_KEY n'est pas configurée.",
            result["message"],
        )

    def test_apple_location_request_uses_timeout(self):
        if importlib.util.find_spec("pyicloud") is None:
            self.skipTest("Dépendance pyicloud absente.")

        from assistant.apple import iphone

        class FakePhone:
            def location(self):
                return {"latitude": 48.8566, "longitude": 2.3522}

        class FakeClient:
            iphone = FakePhone()

        class FakeResponse:
            def json(self):
                return {
                    "status": "OK",
                    "results": [{"formatted_address": "Paris, France"}],
                }

        assistant = iphone.AppleAssistant.__new__(iphone.AppleAssistant)
        assistant.client = FakeClient()
        assistant.maps_api_key = "maps-key"
        with mock.patch.object(iphone.requests, "get", return_value=FakeResponse()) as get:
            result = assistant.get_location()

        self.assertEqual("success", result["status"])
        self.assertEqual(iphone.DEFAULT_REQUEST_TIMEOUT, get.call_args.kwargs["timeout"])

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

    def test_idfm_places_request_uses_timeout(self):
        if importlib.util.find_spec("requests") is None:
            self.skipTest("Dépendance requests absente.")

        from assistant.ratp import ratp_assistant

        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "places": [
                        {
                            "name": "Paris",
                            "embedded_type": "address",
                            "coord": {"lat": "48.8566", "lon": "2.3522"},
                        }
                    ]
                }

        assistant = ratp_assistant.IDFMAssistant()
        assistant.idfm_api_key = "idfm-key"
        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            return_value=FakeResponse(),
        ) as get:
            coords = assistant.get_coords("Paris")

        self.assertEqual({"lat": "48.8566", "lon": "2.3522"}, coords)
        self.assertEqual(
            ratp_assistant.DEFAULT_REQUEST_TIMEOUT,
            get.call_args.kwargs["timeout"],
        )

    def test_idfm_places_handles_network_and_json_errors(self):
        if importlib.util.find_spec("requests") is None:
            self.skipTest("Dépendance requests absente.")

        from assistant.ratp import ratp_assistant

        class InvalidJsonResponse:
            status_code = 200

            def json(self):
                raise ValueError("invalid json")

        assistant = ratp_assistant.IDFMAssistant()
        assistant.idfm_api_key = "idfm-key"
        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            side_effect=ratp_assistant.requests.RequestException("offline"),
        ):
            self.assertIsNone(assistant.get_coords("Paris"))

        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            return_value=InvalidJsonResponse(),
        ):
            self.assertIsNone(assistant.get_coords("Paris"))

    def test_idfm_route_handles_network_and_json_errors(self):
        if importlib.util.find_spec("requests") is None:
            self.skipTest("Dépendance requests absente.")

        from assistant.ratp import ratp_assistant

        class InvalidJsonResponse:
            status_code = 200

            def json(self):
                raise ValueError("invalid json")

        assistant = ratp_assistant.IDFMAssistant()
        assistant.idfm_api_key = "idfm-key"
        assistant.get_coords = lambda city: {"lat": "48.8566", "lon": "2.3522"}

        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            side_effect=ratp_assistant.requests.RequestException("offline"),
        ):
            self.assertIn(
                "Erreur réseau IDFM",
                assistant.calculate_route("Paris", "Lyon"),
            )

        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            return_value=InvalidJsonResponse(),
        ):
            self.assertEqual(
                "Réponse IDFM invalide.",
                assistant.calculate_route("Paris", "Lyon"),
            )

    def test_media_recommendations_report_missing_api_key(self):
        if importlib.util.find_spec("requests") is None:
            self.skipTest("Dépendance requests absente.")

        environment = os.environ.copy()
        environment["API_KEY_MOVIE"] = ""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from assistant.films_and_series.films_and_series "
                "import recommend_media; "
                "assert recommend_media(genre='action', media_type='film') "
                "== \"API_KEY_MOVIE n'est pas configurée.\"",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual("", result.stderr)

    def test_media_request_uses_timeout(self):
        if (
            importlib.util.find_spec("requests") is None
            or importlib.util.find_spec("dotenv") is None
        ):
            self.skipTest("Dépendances média absentes.")

        from assistant.films_and_series import films_and_series

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"results": []}

        with mock.patch.object(films_and_series, "api_key", "movie-key"):
            with mock.patch.object(
                films_and_series.requests,
                "get",
                return_value=FakeResponse(),
            ) as get:
                response = films_and_series.make_request("search/movie", {})

        self.assertEqual({"results": []}, response)
        self.assertEqual(
            films_and_series.DEFAULT_REQUEST_TIMEOUT,
            get.call_args.kwargs["timeout"],
        )

    def test_media_request_handles_network_and_json_errors(self):
        if (
            importlib.util.find_spec("requests") is None
            or importlib.util.find_spec("dotenv") is None
        ):
            self.skipTest("Dépendances média absentes.")

        from assistant.films_and_series import films_and_series

        class InvalidJsonResponse:
            status_code = 200

            def json(self):
                raise ValueError("invalid json")

        with mock.patch.object(films_and_series, "api_key", "movie-key"):
            with mock.patch.object(
                films_and_series.requests,
                "get",
                side_effect=films_and_series.requests.RequestException(
                    "offline"
                ),
            ):
                self.assertEqual(
                    {},
                    films_and_series.make_request("search/movie", {}),
                )

            with mock.patch.object(
                films_and_series.requests,
                "get",
                return_value=InvalidJsonResponse(),
            ):
                self.assertEqual(
                    {},
                    films_and_series.make_request("search/movie", {}),
                )

    def test_media_request_does_not_mutate_params(self):
        if (
            importlib.util.find_spec("requests") is None
            or importlib.util.find_spec("dotenv") is None
        ):
            self.skipTest("Dépendances média absentes.")

        from assistant.films_and_series import films_and_series

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"results": []}

        params = {"query": "Dune"}
        with mock.patch.object(films_and_series, "api_key", "movie-key"):
            with mock.patch.object(
                films_and_series.requests,
                "get",
                return_value=FakeResponse(),
            ):
                response = films_and_series.make_request(
                    "search/movie",
                    params,
                )

        self.assertEqual({"results": []}, response)
        self.assertEqual({"query": "Dune"}, params)

    def test_spotify_assistant_reports_missing_credentials(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        with (
            mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_ID", ""),
            mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_SECRET", ""),
        ):
            assistant = spotify_assistant.SpotifyAssistant()

        self.assertIsNone(assistant.sp)
        self.assertEqual(
            "Identifiants Spotify non configurés.",
            assistant.play_track("Song"),
        )

    def test_spotify_assistant_skips_oauth_prompt_when_non_interactive(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        class FakeOAuth:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def is_token_expired(self, token_info):
                return True

            def get_authorize_url(self):
                return "https://example.test/authorize"

            def refresh_access_token(self, refresh_token):
                return {"access_token": "refreshed"}

        with (
            mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_ID", "client"),
            mock.patch.object(
                spotify_assistant,
                "SPOTIPY_CLIENT_SECRET",
                "secret",
            ),
            mock.patch.object(
                spotify_assistant,
                "TOKEN_FILE",
                "tests/missing_spotify_token.json",
            ),
            mock.patch.object(spotify_assistant, "SpotifyOAuth", FakeOAuth),
            mock.patch.object(spotify_assistant.sys.stdin, "isatty", return_value=False),
            mock.patch("builtins.input") as input_prompt,
        ):
            assistant = spotify_assistant.SpotifyAssistant()

        self.assertIsNone(assistant.sp)
        self.assertEqual(
            "Authentification Spotify interactive indisponible.",
            assistant.error_message,
        )
        input_prompt.assert_not_called()

    def test_spotify_assistant_handles_invalid_token_file(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        class FakeOAuth:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def is_token_expired(self, token_info):
                return True

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token_info.json"
            token_file.write_text("{invalid json", encoding="utf-8")
            with (
                mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_ID", "client"),
                mock.patch.object(
                    spotify_assistant,
                    "SPOTIPY_CLIENT_SECRET",
                    "secret",
                ),
                mock.patch.object(
                    spotify_assistant,
                    "TOKEN_FILE",
                    str(token_file),
                ),
                mock.patch.object(spotify_assistant, "SpotifyOAuth", FakeOAuth),
                mock.patch.object(
                    spotify_assistant.sys.stdin,
                    "isatty",
                    return_value=False,
                ),
                mock.patch("builtins.input") as input_prompt,
            ):
                assistant = spotify_assistant.SpotifyAssistant()

        self.assertIsNone(assistant.sp)
        self.assertIn("interactive indisponible", assistant.error_message)
        input_prompt.assert_not_called()

    def test_spotify_assistant_reports_refresh_failure(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        class FakeOAuth:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def is_token_expired(self, token_info):
                return True

            def refresh_access_token(self, refresh_token):
                raise RuntimeError("refresh failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token_info.json"
            token_file.write_text(
                '{"refresh_token": "refresh-placeholder"}',
                encoding="utf-8",
            )
            with (
                mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_ID", "client"),
                mock.patch.object(
                    spotify_assistant,
                    "SPOTIPY_CLIENT_SECRET",
                    "secret",
                ),
                mock.patch.object(
                    spotify_assistant,
                    "TOKEN_FILE",
                    str(token_file),
                ),
                mock.patch.object(spotify_assistant, "SpotifyOAuth", FakeOAuth),
            ):
                assistant = spotify_assistant.SpotifyAssistant()

        self.assertIsNone(assistant.sp)
        self.assertIn("rafraîchissement Spotify", assistant.error_message)

    def test_spotify_assistant_save_token_creates_parent_directory(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "nested" / "token_info.json"
            assistant = spotify_assistant.SpotifyAssistant.__new__(
                spotify_assistant.SpotifyAssistant
            )
            assistant.error_message = ""
            with mock.patch.object(
                spotify_assistant,
                "TOKEN_FILE",
                str(token_file),
            ):
                self.assertTrue(
                    assistant.save_token({"access_token": "spotify-token"})
                )
                self.assertTrue(token_file.is_file())
                self.assertEqual(
                    '{"access_token": "spotify-token"}',
                    token_file.read_text(encoding="utf-8"),
                )
        self.assertEqual("", assistant.error_message)

    def test_spotify_assistant_refresh_keeps_token_if_save_fails(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        class FakeOAuth:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def is_token_expired(self, token_info):
                return True

            def refresh_access_token(self, refresh_token):
                return {"access_token": "refreshed"}

        original_path_open = Path.open

        def selective_open(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "r")
            if "w" in mode:
                raise OSError("disk full")
            return original_path_open(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token_info.json"
            token_file.write_text(
                '{"refresh_token": "refresh-placeholder"}',
                encoding="utf-8",
            )
            with (
                mock.patch.object(spotify_assistant, "SPOTIPY_CLIENT_ID", "client"),
                mock.patch.object(
                    spotify_assistant,
                    "SPOTIPY_CLIENT_SECRET",
                    "secret",
                ),
                mock.patch.object(
                    spotify_assistant,
                    "TOKEN_FILE",
                    str(token_file),
                ),
                mock.patch.object(spotify_assistant, "SpotifyOAuth", FakeOAuth),
                mock.patch.object(
                    spotify_assistant.spotipy,
                    "Spotify",
                    side_effect=lambda auth: {"auth": auth},
                ),
                mock.patch.object(spotify_assistant.Path, "open", new=selective_open),
            ):
                assistant = spotify_assistant.SpotifyAssistant()

        self.assertEqual({"auth": "refreshed"}, assistant.sp)
        self.assertIn(
            "Impossible d'enregistrer le token Spotify",
            assistant.error_message,
        )

    def test_spotify_assistant_reports_token_without_access_token(self):
        if importlib.util.find_spec("spotipy") is None:
            self.skipTest("Dépendance spotipy absente.")

        import assistant.spotify.spotify_assistant as spotify_assistant

        assistant = spotify_assistant.SpotifyAssistant.__new__(
            spotify_assistant.SpotifyAssistant
        )
        assistant.token_info = {"refresh_token": "refresh-placeholder"}
        assistant.error_message = ""

        self.assertIsNone(assistant._build_spotify_client())
        self.assertEqual(
            "Token Spotify sans access_token.",
            assistant.error_message,
        )


if __name__ == "__main__":
    unittest.main()
