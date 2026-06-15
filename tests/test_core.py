import argparse
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

    def test_empty_icon_path_uses_pygame_fallback_surface(self):
        import pygame
        from app.screen_assets import load_icon_or_fallback

        pygame.font.init()
        for missing_path in (None, ""):
            with mock.patch("builtins.print"):
                icon = load_icon_or_fallback(missing_path, "Réglages", size=64)

            self.assertEqual((64, 64), icon.get_size())
            self.assertGreater(icon.get_bounding_rect().width, 0)

    def test_icon_fallback_rejects_zero_or_negative_sizes(self):
        import pygame
        from app.screen_assets import make_icon_fallback

        pygame.font.init()

        self.assertEqual((1, 1), make_icon_fallback("Cortex", size=0).get_size())
        self.assertEqual((1, 1), make_icon_fallback("Cortex", size=-24).get_size())

    def test_icon_fallback_tolerates_invalid_or_text_sizes(self):
        import pygame
        from app.screen_assets import make_icon_fallback

        pygame.font.init()

        self.assertEqual((1, 1), make_icon_fallback("Cortex", size=None).get_size())
        self.assertEqual((32, 32), make_icon_fallback("Cortex", size="32").get_size())
        self.assertEqual((48, 48), make_icon_fallback("Cortex", size="48x48").get_size())

    def test_icon_fallback_works_without_display(self):
        import pygame
        from app.screen_assets import make_icon_fallback

        pygame.font.init()
        icon = make_icon_fallback("Réglages", size=48)

        self.assertEqual((48, 48), icon.get_size())
        self.assertGreater(icon.get_bounding_rect().height, 0)

    def test_missing_background_uses_pygame_fallback_surface(self):
        import pygame
        from app.screen_assets import load_background_or_fallback

        pygame.font.init()
        with mock.patch("builtins.print"):
            background = load_background_or_fallback(
                "tests/missing-background.png",
                "Horloge",
                (160, 160),
            )

        self.assertEqual((160, 160), background.get_size())
        self.assertGreater(background.get_bounding_rect().height, 0)

    def test_background_fallback_rejects_zero_or_negative_sizes(self):
        import pygame
        from app.screen_assets import make_background_fallback

        pygame.font.init()
        background = make_background_fallback("Cortex", (0, -12))

        self.assertEqual((1, 1), background.get_size())
        self.assertGreaterEqual(background.get_bounding_rect().width, 0)

    def test_background_fallback_tolerates_invalid_or_text_sizes(self):
        import pygame
        from app.screen_assets import make_background_fallback

        pygame.font.init()

        self.assertEqual(
            (1, 1),
            make_background_fallback("Cortex", None).get_size(),
        )
        self.assertEqual(
            (32, 24),
            make_background_fallback("Cortex", "32x24").get_size(),
        )
        self.assertEqual(
            (32, 32),
            make_background_fallback("Cortex", "32").get_size(),
        )
        self.assertEqual(
            (1, 1),
            make_background_fallback("Cortex", "taille-invalide").get_size(),
        )

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
            self.assertIn("draw_round_mask", content, module)
            self.assertIn("rect_hit_test", content, module)
            self.assertIn("screen.get_size()", content, module)
            self.assertNotIn("event.pos", content, module)
            self.assertNotIn("pygame.display.Info", content, module)
            self.assertNotIn("screen_width/2-200", content, module)
            self.assertNotIn("500, 400", content, module)
            if module.name == "app_reglage.py":
                self.assertIn("load_icon_or_fallback", content, module)
            else:
                self.assertIn("load_background_or_fallback", content, module)
                self.assertNotIn("pygame.image.load", content, module)

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
            self.assertIn("env_fps", content, module)
            self.assertIn("CORTEX_EXIT_AFTER_FRAME", content, module)
            self.assertIn("clock.tick(env_fps())", content, module)
            self.assertNotIn("clock.tick(60)", content, module)

    def test_legacy_settings_screen_fits_round_display_labels(self):
        content = Path("app/app_reglage.py").read_text(encoding="utf-8")

        self.assertIn("fit_text", content)
        self.assertIn('fit_text(font, "Quitter"', content)
        self.assertIn("fit_text(font, mode_text", content)
        self.assertIn('fit_text(small_font, "Touchez pour basculer"', content)

    def test_modern_pygame_modules_can_exit_after_one_frame(self):
        for module in (Path("app/app_cortex.py"), Path("app/feature_shell.py")):
            content = module.read_text(encoding="utf-8")
            self.assertIn("env_bool", content, module)
            self.assertIn("env_fps", content, module)
            self.assertIn("CORTEX_EXIT_AFTER_FRAME", content, module)
            self.assertIn("clock.tick(env_fps())", content, module)
            self.assertNotIn("clock.tick(60)", content, module)

    def test_screen_entrypoint_disables_sdl_touch_mouse_duplication(self):
        content = Path("Screen.py").read_text(encoding="utf-8")

        self.assertIn('os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "0")', content)
        self.assertIn('os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")', content)
        self.assertLess(
            content.index('os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "0")'),
            content.index("import pygame"),
        )
        self.assertLess(
            content.index('os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")'),
            content.index("import pygame"),
        )

    def test_bdd_screen_uses_responsive_touch_layout(self):
        content = Path("app/app_bdd.py").read_text(encoding="utf-8")

        self.assertIn("import math", content)
        self.assertIn("from database.database import Neo4jDatabase", content)
        self.assertIn("circular_menu_layout", content)
        self.assertIn("pointer_down_position", content)
        self.assertIn("pointer_move_position", content)
        self.assertIn("pointer_up_position", content)
        self.assertIn("draw_round_mask", content)
        self.assertIn("env_fps", content)
        self.assertIn("clock.tick(env_fps())", content)
        self.assertIn("circle_hit_test", content)
        self.assertIn("rect_hit_test", content)
        self.assertIn("screen.get_size()", content)
        self.assertIn("CORTEX_EXIT_AFTER_FRAME", content)
        self.assertIn("selection_pointer", content)
        self.assertIn("moved_fingers", content)
        self.assertIn("event.finger_id not in finger_positions", content)
        self.assertNotIn("rotated_touch_position", content)
        self.assertNotIn("event.pos", content)
        self.assertNotIn("sub_event.pos", content)
        self.assertNotIn("clock.tick(60)", content)
        self.assertNotIn("exit()", content)
        self.assertNotIn("pygame.quit()", content)
        self.assertNotIn("+ 400 + offset_x", content)
        self.assertNotIn("+ 300 + offset_y", content)
        self.assertNotIn("pygame.Rect(50, 500", content)

    def test_database_graph_view_delegates_to_bdd_screen(self):
        content = Path("database/database.py").read_text(encoding="utf-8")
        method = content.split("def visualiser_graph_interactif(self):", 1)[1].split(
            "    def close(self):",
            1,
        )[0]

        self.assertIn("from app.app_bdd import launch_bdd", method)
        self.assertIn("env_screen_size", method)
        self.assertIn("CortexProxy", method)
        self.assertNotIn("event.x * 800", method)
        self.assertNotIn("event.y * 600", method)
        self.assertNotIn("+ 400 + offset_x", method)
        self.assertNotIn("+ 300 + offset_y", method)
        self.assertNotIn("pygame.Rect(50, 500", method)
        self.assertNotIn("exit()", method)

    def test_database_form_uses_responsive_pointer_input(self):
        content = Path("database/database.py").read_text(encoding="utf-8")
        method = content.split("def afficher_formulaire(screen, titre, question):", 1)[
            1
        ].split("    def _initialiser_graphe(self):", 1)[0]

        self.assertIn("pointer_down_position", method)
        self.assertIn("screen.get_size()", method)
        self.assertIn("CORTEX_EXIT_AFTER_FRAME", method)
        self.assertNotIn("event.pos", method)
        self.assertNotIn("exit()", method)
        self.assertNotIn("pygame.quit()", method)
        self.assertNotIn("pygame.Rect(200, 300", method)

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

    def test_round_safe_point_keeps_back_button_inside_circle(self):
        import pygame
        from app.screen_config import round_safe_point

        center = pygame.Vector2(240, 240)
        radius = 240
        button_radius = 26
        margin = 6

        position = round_safe_point(
            center,
            radius,
            -0.72,
            -0.72,
            item_radius=button_radius,
            margin=margin,
        )

        self.assertLessEqual(
            position.distance_to(center) + button_radius + margin,
            radius,
        )

    def test_round_safe_rect_center_keeps_status_inside_circle(self):
        import pygame
        from app.screen_config import rect_fits_round_viewport, round_safe_rect_center

        center = pygame.Vector2(240, 240)
        radius = 240
        rect_size = (130, 34)
        position = round_safe_rect_center(
            center,
            radius,
            0,
            -0.9,
            rect_size,
            margin=6,
        )
        rect = pygame.Rect((0, 0), rect_size)
        rect.center = position

        self.assertLess(position.y, center.y)
        self.assertTrue(rect_fits_round_viewport(rect, center, radius, margin=6))

    def test_touch_hit_helpers_expand_small_targets(self):
        import pygame
        from app.screen_config import circle_hit_test, rect_hit_test

        rect = pygame.Rect(100, 100, 40, 40)

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_HIT_SLOP": "12"}):
            self.assertTrue(rect_hit_test(rect, (148, 120)))
            self.assertTrue(circle_hit_test((137, 120), (120, 120), 20))

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_HIT_SLOP": "0"}):
            self.assertFalse(rect_hit_test(rect, (148, 120)))
            self.assertFalse(circle_hit_test((141, 120), (120, 120), 20))

    def test_shared_round_mask_blacks_out_square_corners(self):
        import pygame
        from app.screen_config import draw_round_mask

        pygame.init()
        try:
            surface = pygame.Surface((240, 240))
            surface.fill((210, 30, 30))

            self.assertTrue(draw_round_mask(surface))

            self.assertEqual((0, 0, 0), surface.get_at((0, 0))[:3])
            self.assertEqual((0, 0, 0), surface.get_at((1, 103))[:3])
            self.assertEqual((210, 30, 30), surface.get_at((120, 120))[:3])
        finally:
            pygame.quit()

    def test_shared_round_mask_reuses_cached_surface(self):
        import pygame
        import app.screen_config as screen_config

        pygame.init()
        try:
            surface = pygame.Surface((240, 240))
            surface.fill((210, 30, 30))

            screen_config._ROUND_MASK_CACHE_KEY = None
            screen_config._ROUND_MASK_CACHE_SURFACE = None

            self.assertTrue(screen_config.draw_round_mask(surface))
            first_mask = screen_config._ROUND_MASK_CACHE_SURFACE

            surface.fill((40, 210, 80))
            self.assertTrue(screen_config.draw_round_mask(surface))
            second_mask = screen_config._ROUND_MASK_CACHE_SURFACE

            self.assertIs(first_mask, second_mask)
            self.assertEqual((0, 0, 0), surface.get_at((0, 0))[:3])
            self.assertEqual((40, 210, 80), surface.get_at((120, 120))[:3])
        finally:
            pygame.quit()

    def test_circle_fit_rejects_partially_clipped_controls(self):
        from app.screen_config import circle_fits_round_viewport

        self.assertTrue(
            circle_fits_round_viewport((240, 240), 480, 480, item_radius=44, margin=6)
        )
        self.assertTrue(
            circle_fits_round_viewport((240, 70), 480, 480, item_radius=44, margin=6)
        )
        self.assertFalse(
            circle_fits_round_viewport((240, 34), 480, 480, item_radius=44, margin=6)
        )

    def test_fit_text_keeps_long_labels_inside_width(self):
        import pygame
        from app.screen_config import fit_text

        pygame.font.init()
        font = pygame.font.SysFont("Segoe UI", 22, bold=True)
        fitted = fit_text(font, "Divertissement personnel familial", 180)

        self.assertLessEqual(font.size(fitted)[0], 180)
        self.assertTrue(fitted.endswith("..."))

    def test_wrap_text_keeps_unbroken_words_inside_width(self):
        import pygame
        from app.screen_config import wrap_text

        pygame.font.init()
        font = pygame.font.SysFont("Segoe UI", 23)
        lines = wrap_text(font, "supercalifragilisticexpialidocious", 120, max_lines=2)

        self.assertTrue(lines)
        self.assertTrue(all(font.size(line)[0] <= 120 for line in lines))
        self.assertTrue(lines[0].endswith("..."))

    def test_home_menu_keeps_rendered_icons_inside_round_viewport(self):
        content = Path("Screen.py").read_text(encoding="utf-8")

        self.assertIn("circle_fits_round_viewport", content)
        self.assertIn("safe_margin", content)
        self.assertIn("size / 2", content)
        self.assertIn("fit_text(self.label_font", content)
        self.assertIn("round_safe_rect_center", content)
        self.assertIn("TAP_MOVE_LIMIT", content)
        self.assertIn("app == self.selected", content)
        self.assertIn("apply_round_mask(self.screen", content)
        self.assertIn("circle_hit_test", content)

    def test_home_menu_round_mask_blacks_out_square_corners(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                center, radius = home.viewport()
                home.screen.fill((210, 30, 30))
                home.draw_round_mask(center, radius)

                self.assertEqual((0, 0, 0), home.screen.get_at((0, 0))[:3])
                self.assertEqual((210, 30, 30), home.screen.get_at((120, 120))[:3])
            finally:
                pygame.quit()

    def test_home_menu_round_mask_can_be_disabled_for_square_preview(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_ROUND_MASK": "false",
            },
        ):
            home = CortexHome()
            try:
                center, radius = home.viewport()
                home.screen.fill((210, 30, 30))
                home.draw_round_mask(center, radius)

                self.assertEqual((210, 30, 30), home.screen.get_at((0, 0))[:3])
            finally:
                pygame.quit()

    def test_home_menu_clamps_invalid_preview_size_before_creating_window(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_PREVIEW_SIZE": "0",
                "CORTEX_SCREEN_SIZE": "",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                self.assertEqual((1, 1), home.screen.get_size())
            finally:
                pygame.quit()

    def test_home_menu_windowed_mode_can_request_frameless_preview(self):
        import pygame
        from Screen import CortexHome

        screen_surface = mock.Mock()
        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "320x240",
                "CORTEX_FRAMELESS": "true",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            with (
                mock.patch("Screen.pygame.init"),
                mock.patch("Screen.pygame.display.set_caption"),
                mock.patch("Screen.pygame.mouse.set_visible"),
                mock.patch(
                    "Screen.pygame.display.set_mode",
                    return_value=screen_surface,
                ) as set_mode,
                mock.patch("Screen.load_icon_or_fallback", return_value=mock.Mock()),
                mock.patch("Screen.pygame.font.SysFont", return_value=mock.Mock()),
            ):
                home = CortexHome()

        self.assertIs(screen_surface, home.screen)
        set_mode.assert_called_once_with((320, 240), pygame.NOFRAME)

    def test_home_menu_loads_cortex_with_runtime_mode_overrides(self):
        from types import ModuleType

        from Screen import CortexHome

        screen_surface = mock.Mock()
        cortex_module = ModuleType("cortex")
        cortex_constructor = mock.Mock(return_value="local-cortex")
        cortex_module.Cortex = cortex_constructor
        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "320x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_INPUT_MODE": "text",
                "CORTEX_OUTPUT_MODE": "screen",
                "CORTEX_LOCAL_MODE": "false",
            },
        ):
            with (
                mock.patch("Screen.pygame.init"),
                mock.patch("Screen.pygame.display.set_caption"),
                mock.patch("Screen.pygame.mouse.set_visible"),
                mock.patch(
                    "Screen.pygame.display.set_mode",
                    return_value=screen_surface,
                ),
                mock.patch("Screen.load_icon_or_fallback", return_value=mock.Mock()),
                mock.patch("Screen.pygame.font.SysFont", return_value=mock.Mock()),
            ):
                home = CortexHome()

            home.loading_error = "stale import error"
            with mock.patch.dict(sys.modules, {"cortex": cortex_module}):
                home.load_cortex()

        cortex_constructor.assert_called_once_with(
            input_mode="text",
            output_mode="screen",
            local_mode=False,
        )
        self.assertEqual("local-cortex", home.cortex)
        self.assertIsNone(home.loading_error)

        cortex_constructor.reset_mock()
        cortex_constructor.return_value = "fallback-cortex"
        home.cortex = None
        home.loading_error = "stale runtime mode error"
        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_INPUT_MODE": "microphone",
                "CORTEX_OUTPUT_MODE": "display",
            },
            clear=True,
        ):
            with mock.patch.dict(sys.modules, {"cortex": cortex_module}):
                home.load_cortex()

        cortex_constructor.assert_called_once_with(
            input_mode="voice",
            output_mode="voice",
            local_mode=True,
        )
        self.assertEqual("fallback-cortex", home.cortex)
        self.assertIsNone(home.loading_error)

    def test_home_menu_reuses_static_background_cache(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                center, radius = home.viewport()

                home.draw_background(center, radius)
                first_surface = home.background_cache_surface
                first_key = home.background_cache_key

                home.draw_background(center, radius)
                self.assertIs(first_surface, home.background_cache_surface)
                self.assertEqual(first_key, home.background_cache_key)

                home.draw_background(center, radius - 1)
                self.assertIsNot(first_surface, home.background_cache_surface)
                self.assertNotEqual(first_key, home.background_cache_key)
            finally:
                pygame.quit()

    def test_home_menu_can_exit_after_one_frame(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "120x120",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_EXIT_AFTER_FRAME": "true",
            },
        ):
            home = CortexHome()
            home.run()

        self.assertFalse(pygame.get_init())

    def test_home_menu_can_save_screenshot_and_exit_after_capture(self):
        import pygame
        from Screen import CortexHome

        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot_path = Path(temp_dir) / "captures" / "screen.png"
            with mock.patch.dict(
                os.environ,
                {
                    "SDL_VIDEODRIVER": "dummy",
                    "CORTEX_FULLSCREEN": "false",
                    "CORTEX_SCREEN_SIZE": "120x120",
                    "CORTEX_SKIP_CORTEX_LOAD": "true",
                    "CORTEX_SCREENSHOT_PATH": f"  {screenshot_path}  ",
                    "CORTEX_EXIT_AFTER_SCREENSHOT": "true",
                },
            ):
                home = CortexHome()
                home.run()
                self.assertTrue(home.screenshot_saved)
                self.assertTrue(screenshot_path.is_file())
                self.assertGreater(screenshot_path.stat().st_size, 0)

        self.assertFalse(pygame.get_init())

    def test_modern_pygame_views_apply_round_mask_before_flip(self):
        cortex_content = Path("app/app_cortex.py").read_text(encoding="utf-8")
        feature_content = Path("app/feature_shell.py").read_text(encoding="utf-8")

        self.assertIn("draw_round_mask(self.screen, center, radius)", cortex_content)
        self.assertIn("draw_round_mask(screen, center, radius)", feature_content)
        self.assertIn("feature_background_cache_key", feature_content)
        self.assertIn("make_feature_background_surface", feature_content)
        self.assertIn("screen.blit(background_cache_surface", feature_content)
        self.assertIn("cached_scaled_icon", feature_content)
        self.assertIn("icon_cache", feature_content)
        self.assertIn("rect_hit_test", cortex_content)
        self.assertIn("circle_hit_test", cortex_content)
        self.assertIn("rect_hit_test", feature_content)
        self.assertIn("circle_hit_test", feature_content)
        self.assertIn("round_safe_rect_center", cortex_content)
        self.assertIn("round_safe_rect_center", feature_content)

    def test_cortex_view_reuses_static_background_cache(self):
        import pygame
        from app.app_cortex import CortexView

        with mock.patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"}):
            pygame.init()
            screen = pygame.display.set_mode((240, 240))
            view = CortexView(screen, cortex=None)
            try:
                center, radius = view.viewport()

                view.draw_background(center, radius)
                first_surface = view.background_cache_surface
                first_key = view.background_cache_key

                view.draw_background(center, radius)
                self.assertIs(first_surface, view.background_cache_surface)
                self.assertEqual(first_key, view.background_cache_key)

                view.draw_background(center, radius - 1)
                self.assertIsNot(first_surface, view.background_cache_surface)
                self.assertNotEqual(first_key, view.background_cache_key)
            finally:
                pygame.quit()

    def test_feature_shell_background_cache_helpers(self):
        import pygame
        from app.feature_shell import (
            feature_background_cache_key,
            make_feature_background_surface,
        )

        pygame.init()
        try:
            center = pygame.Vector2(120, 120)
            radius = 120
            accent = (88, 214, 255)

            surface = make_feature_background_surface((240, 240), center, radius, accent)
            self.assertEqual((240, 240), surface.get_size())
            self.assertGreater(surface.get_bounding_rect().width, 0)

            key = feature_background_cache_key(240, 240, center, radius, accent)
            self.assertEqual(key, feature_background_cache_key(240, 240, center, radius, accent))
            self.assertNotEqual(
                key,
                feature_background_cache_key(240, 240, center, radius - 1, accent),
            )
            self.assertNotEqual(
                key,
                feature_background_cache_key(240, 240, center, radius, (1, 2, 3)),
            )
        finally:
            pygame.quit()

    def test_legacy_status_panel_draws_visible_content(self):
        import pygame
        from app.legacy_widgets import draw_legacy_status_panel

        pygame.init()
        try:
            surface = pygame.Surface((240, 240))
            surface.fill((0, 0, 0))

            draw_legacy_status_panel(
                surface,
                "Calendrier",
                "Planning du jour",
                (249, 115, 22),
                ("RDV", "Taches", "Alertes"),
            )

            self.assertGreater(surface.get_bounding_rect().width, 0)
            self.assertNotEqual((0, 0, 0), surface.get_at((120, 72))[:3])
        finally:
            pygame.quit()

    def test_feature_shell_reuses_scaled_icon_cache(self):
        import pygame
        from app.feature_shell import cached_scaled_icon

        pygame.init()
        try:
            icon = pygame.Surface((32, 32), pygame.SRCALPHA)
            icon.fill((88, 214, 255, 255))
            cache = {"size": None, "surface": None}

            first = cached_scaled_icon(icon, 48, cache)
            second = cached_scaled_icon(icon, 48, cache)
            self.assertIs(first, second)
            self.assertEqual((48, 48), first.get_size())

            third = cached_scaled_icon(icon, 64, cache)
            self.assertIsNot(first, third)
            self.assertEqual((64, 64), third.get_size())

            tiny = cached_scaled_icon(icon, 0, cache)
            self.assertEqual((1, 1), tiny.get_size())
        finally:
            pygame.quit()

    def test_home_menu_shows_notice_when_app_is_not_ready(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                with mock.patch("builtins.print") as printed:
                    home.launch_app("Horloge")

                self.assertEqual("Aperçu: Cortex non chargé", home.notice_text)
                self.assertGreater(home.notice_until, pygame.time.get_ticks())
                printed.assert_called_with("Aperçu: Cortex non chargé")
            finally:
                pygame.quit()

    def test_home_menu_only_launches_app_pressed_at_pointer_down(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]
                with mock.patch.object(home, "launch_app") as launch_app:
                    home.handle_pointer_down((20, 20))
                    home.handle_pointer_up((120, 120))

                launch_app.assert_not_called()
            finally:
                pygame.quit()

    def test_home_menu_ignores_synthetic_mouse_events_after_touch(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]
                finger_down = pygame.event.Event(
                    pygame.FINGERDOWN,
                    {"x": 0.5, "y": 0.5, "finger_id": 1},
                )
                finger_up = pygame.event.Event(
                    pygame.FINGERUP,
                    {"x": 0.5, "y": 0.5, "finger_id": 1},
                )
                synthetic_mouse_down = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": (120, 120), "touch": True},
                )
                synthetic_mouse_up = pygame.event.Event(
                    pygame.MOUSEBUTTONUP,
                    {"button": 1, "pos": (120, 120), "touch": True},
                )

                with mock.patch.object(home, "launch_app") as launch_app:
                    home.handle_event(finger_down)
                    home.handle_event(finger_up)
                    home.handle_event(synthetic_mouse_down)
                    home.handle_event(synthetic_mouse_up)

                launch_app.assert_called_once_with(app.name)
            finally:
                pygame.quit()

    def test_home_menu_drag_clears_pressed_icon_selection(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]
                home.handle_pointer_down((120, 120))
                home.handle_pointer_move((160, 120))

                self.assertIsNone(home.selected)
                self.assertTrue(home.panning)
                self.assertGreater(home.offset.length(), 0)
            finally:
                pygame.quit()

    def test_home_menu_small_touch_jitter_does_not_pan(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]
                home.handle_pointer_down((120, 120))
                home.handle_pointer_move((126, 120))

                self.assertEqual((0, 0), tuple(home.offset))
                self.assertFalse(home.panning)
                self.assertEqual(app, home.selected)
            finally:
                pygame.quit()

    def test_home_menu_honors_custom_tap_move_limit(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_TAP_MOVE_LIMIT": "60",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 90)]
                with mock.patch.object(home, "launch_app") as launch_app:
                    home.handle_pointer_down((120, 120))
                    home.handle_pointer_move((158, 120))
                    home.handle_pointer_up((158, 120))

                self.assertEqual((0, 0), tuple(home.offset))
                self.assertFalse(home.panning)
                launch_app.assert_called_once_with(app.name)
            finally:
                pygame.quit()

    def test_home_menu_honors_custom_fps(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_FPS": "30",
            },
        ):
            home = CortexHome()
            try:
                self.assertEqual(30, home.fps)
            finally:
                pygame.quit()

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_FPS": "0",
            },
        ):
            home = CortexHome()
            try:
                self.assertEqual(1, home.fps)
            finally:
                pygame.quit()

    def test_home_menu_empty_double_tap_resets_view(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_EMPTY_DOUBLE_TAP_MS": "900",
                "CORTEX_EMPTY_DOUBLE_TAP_DISTANCE": "60",
            },
        ):
            home = CortexHome()
            try:
                home.rendered_apps = []
                home.offset.update(42, -24)
                home.velocity.update(8, 3)
                home.zoom = 1.2

                with mock.patch(
                    "pygame.time.get_ticks",
                    side_effect=[1000, 1700, 1700],
                ):
                    home.handle_pointer_down((40, 120))
                    home.handle_pointer_up((40, 120))
                    self.assertEqual((42, -24), tuple(home.offset))
                    self.assertEqual(1.2, home.zoom)

                    home.handle_pointer_down((90, 120))
                    home.handle_pointer_up((90, 120))

                self.assertEqual((0, 0), tuple(home.offset))
                self.assertEqual((0, 0), tuple(home.velocity))
                self.assertEqual(1.0, home.zoom)
                self.assertEqual("Vue recentrée", home.notice_text)
            finally:
                pygame.quit()

    def test_home_menu_clamps_invalid_empty_double_tap_config(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_EMPTY_DOUBLE_TAP_MS": "0",
                "CORTEX_EMPTY_DOUBLE_TAP_DISTANCE": "0",
            },
        ):
            home = CortexHome()
            try:
                home.rendered_apps = []
                home.offset.update(18, -12)
                home.velocity.update(3, 1)
                home.zoom = 1.15

                with mock.patch(
                    "pygame.time.get_ticks",
                    side_effect=[1000, 1001, 1001],
                ):
                    home.handle_pointer_down((90, 120))
                    home.handle_pointer_up((90, 120))
                    home.handle_pointer_down((90, 120))
                    home.handle_pointer_up((90, 120))

                self.assertEqual((0, 0), tuple(home.offset))
                self.assertEqual((0, 0), tuple(home.velocity))
                self.assertEqual(1.0, home.zoom)
            finally:
                pygame.quit()

    def test_home_menu_zoom_keeps_focus_point_stable(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                center, _ = home.viewport()
                focus = pygame.Vector2(170, 120)
                home.offset.update(24, -8)
                before = (focus - center - home.offset) / home.zoom

                home.set_zoom(1.2, focus=focus)

                after = (focus - center - home.offset) / home.zoom
                self.assertAlmostEqual(before.x, after.x, places=5)
                self.assertAlmostEqual(before.y, after.y, places=5)
            finally:
                pygame.quit()

    def test_home_menu_supports_two_finger_pinch_zoom(self):
        import pygame
        from Screen import CortexHome

        def finger_event(event_type, finger_id, x, y):
            return pygame.event.Event(
                event_type,
                {"finger_id": finger_id, "x": x, "y": y},
            )

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                home.handle_event(finger_event(pygame.FINGERDOWN, 1, 0.35, 0.50))
                self.assertTrue(home.dragging)

                home.handle_event(finger_event(pygame.FINGERDOWN, 2, 0.65, 0.50))
                self.assertFalse(home.dragging)
                self.assertIsNone(home.selected)
                self.assertIsNotNone(home.pinch_last_distance)

                home.handle_event(finger_event(pygame.FINGERMOTION, 2, 0.85, 0.50))
                self.assertGreater(home.zoom, 1.0)
                self.assertFalse(home.dragging)

                home.zoom = 1.27
                home.handle_event(finger_event(pygame.FINGERMOTION, 2, 0.99, 0.50))
                self.assertLessEqual(home.zoom, 1.28)

                with mock.patch.object(home, "launch_app") as launch_app:
                    home.handle_event(finger_event(pygame.FINGERUP, 2, 0.99, 0.50))
                    home.handle_event(finger_event(pygame.FINGERUP, 1, 0.35, 0.50))

                launch_app.assert_not_called()
                self.assertFalse(home.active_fingers)
                self.assertFalse(home.dragging)
            finally:
                pygame.quit()

    def test_home_menu_can_pan_after_pinch_lifts_one_finger(self):
        import pygame
        from Screen import CortexHome

        def finger_event(event_type, finger_id, x, y):
            return pygame.event.Event(
                event_type,
                {"finger_id": finger_id, "x": x, "y": y},
            )

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                home.handle_event(finger_event(pygame.FINGERDOWN, 1, 0.35, 0.50))
                home.handle_event(finger_event(pygame.FINGERDOWN, 2, 0.65, 0.50))
                home.handle_event(finger_event(pygame.FINGERMOTION, 2, 0.80, 0.50))

                home.handle_event(finger_event(pygame.FINGERUP, 2, 0.80, 0.50))
                self.assertTrue(home.dragging)
                self.assertTrue(home.suppress_next_empty_tap)

                home.handle_event(finger_event(pygame.FINGERMOTION, 1, 0.28, 0.50))
                self.assertTrue(home.panning)
                self.assertGreater(home.offset.length(), 0)

                with mock.patch.object(home, "reset_view") as reset_view:
                    home.handle_event(finger_event(pygame.FINGERUP, 1, 0.28, 0.50))

                reset_view.assert_not_called()
                self.assertFalse(home.active_fingers)
                self.assertFalse(home.dragging)
                self.assertFalse(home.suppress_next_empty_tap)
            finally:
                pygame.quit()

    def test_home_menu_mouse_wheel_uses_zoom_bounds(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                for _ in range(20):
                    home.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1}))
                self.assertEqual(1.28, home.zoom)

                for _ in range(40):
                    home.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}))
                self.assertEqual(0.72, home.zoom)
            finally:
                pygame.quit()

    def test_home_menu_launches_matching_tap(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]
                with mock.patch.object(home, "launch_app") as launch_app:
                    home.handle_pointer_down((120, 120))
                    home.handle_pointer_up((120, 120))

                launch_app.assert_called_once_with(app.name)
            finally:
                pygame.quit()

    def test_home_menu_uses_touch_hit_slop_for_icon_taps(self):
        import pygame
        from Screen import APP_DEFINITIONS, CortexHome, build_honeycomb

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_TOUCH_HIT_SLOP": "12",
            },
        ):
            home = CortexHome()
            try:
                app = build_honeycomb(APP_DEFINITIONS)[0]
                home.rendered_apps = [(app, pygame.Vector2(120, 120), 60)]

                self.assertEqual(app, home.app_at((161, 120)))
            finally:
                pygame.quit()

    def test_home_menu_accepts_zero_coordinate_events_when_unclipped(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_TOUCH_ROUND_CLIP": "false",
            },
        ):
            home = CortexHome()
            try:
                down = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": (0, 0)},
                )
                up = pygame.event.Event(
                    pygame.MOUSEBUTTONUP,
                    {"button": 1, "pos": (0, 0)},
                )

                home.handle_event(down)
                self.assertTrue(home.dragging)
                self.assertEqual((0, 0), tuple(home.press_position))

                home.handle_event(up)
                self.assertFalse(home.dragging)
            finally:
                pygame.quit()

    def test_home_menu_release_at_round_edge_ends_drag(self):
        import pygame
        from Screen import CortexHome

        with mock.patch.dict(
            os.environ,
            {
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": "240x240",
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_TOUCH_ROUND_CLIP": "true",
                "CORTEX_TOUCH_EDGE_CLAMP": "false",
            },
        ):
            home = CortexHome()
            try:
                home.handle_event(
                    pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        {"button": 1, "pos": (120, 120)},
                    )
                )
                self.assertTrue(home.dragging)

                home.handle_event(
                    pygame.event.Event(
                        pygame.MOUSEBUTTONUP,
                        {"button": 1, "pos": (0, 0)},
                    )
                )
                self.assertFalse(home.dragging)
            finally:
                pygame.quit()

    def test_screen_text_helpers_are_shared(self):
        helper_content = Path("app/screen_config.py").read_text(encoding="utf-8")

        self.assertIn("def fit_text(", helper_content)
        self.assertIn("def wrap_text(", helper_content)
        for module in (Path("app/app_cortex.py"), Path("app/feature_shell.py")):
            content = module.read_text(encoding="utf-8")

            self.assertIn("fit_text", content, module)
            self.assertNotIn("def fit_text(", content, module)
        cortex_content = Path("app/app_cortex.py").read_text(encoding="utf-8")
        self.assertIn("wrap_text", cortex_content)
        self.assertNotIn("def wrap_text(", cortex_content)

    def test_modern_back_buttons_use_round_safe_position(self):
        for module in (Path("app/app_cortex.py"), Path("app/feature_shell.py")):
            content = module.read_text(encoding="utf-8")

            self.assertIn("round_safe_point", content, module)
            self.assertNotIn("center.x - radius * 0.72", content, module)
            self.assertNotIn("center.x - radius * 0.68", content, module)

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
        with self.assertRaises(argparse.ArgumentTypeError):
            rotated_touch_position(0.25, 0.75, width, height, 45)
        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_FLIP_X": "true"}):
            self.assertEqual(
                (300.0, 300.0),
                rotated_touch_position(0.25, 0.75, width, height, 0),
            )
        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_FLIP_Y": "true"}):
            self.assertEqual(
                (100.0, 100.0),
                rotated_touch_position(0.25, 0.75, width, height, 0),
            )
        self.assertEqual(
            (400.0, 0.0),
            rotated_touch_position(1.02, -0.01, width, height, 0),
        )
        with mock.patch.dict(
            os.environ,
            {"CORTEX_TOUCH_FLIP_X": "true", "CORTEX_TOUCH_FLIP_Y": "true"},
        ):
            self.assertEqual(
                (0.0, 400.0),
                rotated_touch_position(1.02, -0.01, width, height, 0),
            )

    def test_touch_drag_motion_can_clamp_to_round_edge(self):
        import pygame
        from app.screen_config import (
            clamp_to_round_viewport,
            pointer_down_position,
            pointer_move_position,
            pointer_up_position,
        )

        clipped_down = pygame.event.Event(
            pygame.FINGERDOWN,
            {"x": 0.0, "y": 0.0},
        )
        clipped_motion = pygame.event.Event(
            pygame.FINGERMOTION,
            {"x": 0.0, "y": 0.0},
        )
        clipped_up = pygame.event.Event(
            pygame.FINGERUP,
            {"x": 0.0, "y": 0.0},
        )

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_ROUND_CLIP": "true"}):
            self.assertIsNone(pointer_down_position(clipped_down, 400, 400))
            clamped = pointer_move_position(clipped_motion, 400, 400)
            clamped_up = pointer_up_position(clipped_up, 400, 400)

        expected = clamp_to_round_viewport((0, 0), 400, 400)
        self.assertAlmostEqual(expected[0], clamped[0], places=5)
        self.assertAlmostEqual(expected[1], clamped[1], places=5)
        self.assertAlmostEqual(expected[0], clamped_up[0], places=5)
        self.assertAlmostEqual(expected[1], clamped_up[1], places=5)

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_TOUCH_ROUND_CLIP": "true",
                "CORTEX_TOUCH_EDGE_CLAMP": "false",
            },
        ):
            self.assertIsNone(pointer_move_position(clipped_motion, 400, 400))
            clamped_up = pointer_up_position(clipped_up, 400, 400)
            self.assertAlmostEqual(expected[0], clamped_up[0], places=5)
            self.assertAlmostEqual(expected[1], clamped_up[1], places=5)

    def test_screen_config_parses_environment_defaults(self):
        from app import screen_config

        content = Path("app/screen_config.py").read_text(encoding="utf-8")
        self.assertIn("from tools.touch_config import", content)
        self.assertIn("parse_required_int", content)
        self.assertIn("parse_touch_bool", content)
        self.assertIn("parse_touch_rotation", content)
        self.assertNotIn("return int(os.getenv", content)
        self.assertNotIn("TRUTHY =", content)
        self.assertNotIn("FALSY =", content)

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_TEST_TRUE": "oui",
                "CORTEX_TEST_FALSE": "off",
                "CORTEX_TEST_INT": "abc",
                "CORTEX_TOUCH_ROTATION": "180",
                "CORTEX_TOUCH_ROUND_CLIP": "true",
                "CORTEX_TOUCH_EDGE_MARGIN": "12",
                "CORTEX_TOUCH_EDGE_CLAMP": "false",
                "CORTEX_FPS": "24",
                "CORTEX_SCREEN_SIZE": "480x480",
            },
        ):
            self.assertTrue(screen_config.env_bool("CORTEX_TEST_TRUE"))
            self.assertFalse(screen_config.env_bool("CORTEX_TEST_FALSE", True))
            self.assertEqual(7, screen_config.env_int("CORTEX_TEST_INT", 7))
            self.assertEqual(9, screen_config.env_positive_int("CORTEX_TEST_INT", 9))
            self.assertEqual(9, screen_config.env_non_negative_int("CORTEX_TEST_INT", 9))
            self.assertEqual("voice", screen_config.env_input_mode())
            self.assertEqual("voice", screen_config.env_output_mode())
            self.assertEqual(24, screen_config.env_fps())
            self.assertEqual(180, screen_config.env_touch_rotation())
            self.assertEqual(12, screen_config.env_touch_edge_margin())
            self.assertEqual(
                (480, 480),
                screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
            )
            self.assertEqual(
                (300.0, 100.0),
                screen_config.rotated_touch_position(0.25, 0.75, 400, 400),
            )
            self.assertFalse(screen_config.is_inside_round_viewport((10, 10), 400, 400))
            self.assertFalse(
                screen_config.is_inside_round_viewport((200, 20), 400, 400, 24)
            )

        for value in ("0", "-5", "abc"):
            with mock.patch.dict(os.environ, {"CORTEX_FPS": value}):
                self.assertEqual(1 if value != "abc" else 60, screen_config.env_fps())

        for value in ("0", "-5", "abc"):
            with mock.patch.dict(os.environ, {"CORTEX_TEST_POSITIVE_INT": value}):
                self.assertEqual(
                    1 if value != "abc" else 11,
                    screen_config.env_positive_int("CORTEX_TEST_POSITIVE_INT", 11),
                )

        for value in ("0", "-5", "abc"):
            with mock.patch.dict(os.environ, {"CORTEX_TEST_NON_NEGATIVE_INT": value}):
                self.assertEqual(
                    0 if value != "abc" else 11,
                    screen_config.env_non_negative_int(
                        "CORTEX_TEST_NON_NEGATIVE_INT",
                        11,
                    ),
                )

        for value in ("45", "-90", "abc"):
            with mock.patch.dict(os.environ, {"CORTEX_TOUCH_ROTATION": value}):
                self.assertEqual(0, screen_config.env_touch_rotation())
                self.assertEqual(90, screen_config.env_touch_rotation(default="90"))
                self.assertEqual(0, screen_config.env_touch_rotation(default="45"))

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_INPUT_MODE": " Text ",
                "CORTEX_OUTPUT_MODE": " SCREEN ",
            },
        ):
            self.assertEqual("text", screen_config.env_input_mode())
            self.assertEqual("screen", screen_config.env_output_mode())

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_INPUT_MODE": "microphone",
                "CORTEX_OUTPUT_MODE": "display",
            },
        ):
            self.assertEqual("voice", screen_config.env_input_mode())
            self.assertEqual("voice", screen_config.env_output_mode())
            self.assertEqual("text", screen_config.env_input_mode(default="text"))
            self.assertEqual("screen", screen_config.env_output_mode(default="screen"))
            self.assertEqual("voice", screen_config.env_input_mode(default="microphone"))
            self.assertEqual("voice", screen_config.env_output_mode(default="display"))

        for value in ("-5", "abc"):
            with mock.patch.dict(os.environ, {"CORTEX_TOUCH_EDGE_MARGIN": value}):
                self.assertEqual(0, screen_config.env_touch_edge_margin())

    def test_screen_config_rejects_invalid_screen_size(self):
        from app import screen_config

        with mock.patch.dict(os.environ, {"CORTEX_SCREEN_SIZE": "480×480"}):
            self.assertEqual(
                (480, 480),
                screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
            )
        with mock.patch.dict(os.environ, {"CORTEX_SCREEN_SIZE": "480*320"}):
            self.assertEqual(
                (480, 320),
                screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
            )

        for value in ("large", "480", "0x480", "480x0", "480xabc"):
            with mock.patch.dict(os.environ, {"CORTEX_SCREEN_SIZE": value}):
                self.assertEqual(
                    (900, 900),
                    screen_config.env_screen_size("CORTEX_SCREEN_SIZE", (900, 900)),
                )

    def test_pointer_helpers_support_mouse_and_rotated_touch(self):
        import pygame
        from app import screen_config
        from app.screen_config import (
            pointer_down_position,
            pointer_move_position,
            pointer_up_position,
        )

        mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (200, 200)},
        )
        mouse_motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (56, 78)},
        )
        clipped_mouse_motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (12, 34)},
        )
        mouse_up_event = pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (90, 123)},
        )
        clipped_mouse_up_event = pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (12, 34)},
        )
        touch_event = pygame.event.Event(
            pygame.FINGERDOWN,
            {"x": 0.25, "y": 0.75},
        )
        touch_motion_event = pygame.event.Event(
            pygame.FINGERMOTION,
            {"x": 0.5, "y": 0.25},
        )
        clipped_touch_motion_event = pygame.event.Event(
            pygame.FINGERMOTION,
            {"x": 0.0, "y": 0.0},
        )
        touch_up_event = pygame.event.Event(
            pygame.FINGERUP,
            {"x": 0.75, "y": 0.5},
        )
        clipped_touch_up_event = pygame.event.Event(
            pygame.FINGERUP,
            {"x": 0.0, "y": 0.0},
        )
        ignored_mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 2, "pos": (12, 34)},
        )
        synthetic_touch_mouse_down = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (200, 200), "touch": True},
        )
        synthetic_touch_mouse_motion = pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (200, 200), "touch": True},
        )
        synthetic_touch_mouse_up = pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (200, 200), "touch": True},
        )
        clipped_corner_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (12, 34)},
        )
        clipped_touch_event = pygame.event.Event(
            pygame.FINGERDOWN,
            {"x": 0.0, "y": 0.0},
        )

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_ROTATION": "180"}):
            self.assertEqual((200, 200), pointer_down_position(mouse_event, 400, 400))
            self.assertIsNone(pointer_down_position(clipped_corner_event, 400, 400))
            self.assertIsNone(pointer_down_position(clipped_touch_event, 400, 400))
            self.assertEqual((56, 78), pointer_move_position(mouse_motion_event, 400, 400))
            clipped_mouse = pointer_move_position(clipped_mouse_motion_event, 400, 400)
            self.assertIsNotNone(clipped_mouse)
            self.assertTrue(screen_config.is_inside_round_viewport(clipped_mouse, 400, 400))
            self.assertEqual((90, 123), pointer_up_position(mouse_up_event, 400, 400))
            clipped_mouse_up = pointer_up_position(clipped_mouse_up_event, 400, 400)
            self.assertIsNotNone(clipped_mouse_up)
            self.assertTrue(
                screen_config.is_inside_round_viewport(clipped_mouse_up, 400, 400)
            )
            self.assertIsNone(pointer_down_position(ignored_mouse_event, 400, 400))
            self.assertIsNone(pointer_down_position(synthetic_touch_mouse_down, 400, 400))
            self.assertIsNone(pointer_move_position(synthetic_touch_mouse_motion, 400, 400))
            self.assertIsNone(pointer_up_position(synthetic_touch_mouse_up, 400, 400))
            self.assertEqual(
                (300.0, 100.0),
                pointer_down_position(touch_event, 400, 400),
            )
            self.assertEqual(
                (200.0, 300.0),
                pointer_move_position(touch_motion_event, 400, 400),
            )
            clipped_touch = pointer_move_position(clipped_touch_motion_event, 400, 400)
            self.assertIsNotNone(clipped_touch)
            self.assertTrue(screen_config.is_inside_round_viewport(clipped_touch, 400, 400))
            clipped_touch_up = pointer_up_position(clipped_touch_up_event, 400, 400)
            self.assertIsNotNone(clipped_touch_up)
            self.assertTrue(
                screen_config.is_inside_round_viewport(clipped_touch_up, 400, 400)
            )
            self.assertEqual(
                (100.0, 200.0),
                pointer_up_position(touch_up_event, 400, 400),
            )

        with mock.patch.dict(
            os.environ,
            {
                "CORTEX_TOUCH_ROTATION": "180",
                "CORTEX_TOUCH_EDGE_CLAMP": "false",
            },
        ):
            self.assertIsNone(
                pointer_move_position(clipped_mouse_motion_event, 400, 400)
            )
            clipped_mouse_up = pointer_up_position(clipped_mouse_up_event, 400, 400)
            self.assertIsNotNone(clipped_mouse_up)
            self.assertTrue(
                screen_config.is_inside_round_viewport(clipped_mouse_up, 400, 400)
            )
            self.assertIsNone(
                pointer_move_position(clipped_touch_motion_event, 400, 400)
            )
            clipped_touch_up = pointer_up_position(clipped_touch_up_event, 400, 400)
            self.assertIsNotNone(clipped_touch_up)
            self.assertTrue(
                screen_config.is_inside_round_viewport(clipped_touch_up, 400, 400)
            )

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_ROUND_CLIP": "false"}):
            self.assertEqual((12, 34), pointer_down_position(clipped_corner_event, 400, 400))
            self.assertEqual(
                (12, 34),
                pointer_move_position(clipped_mouse_motion_event, 400, 400),
            )

    def test_prepare_screenshot_path_creates_parent_directory(self):
        from app.screen_config import prepare_screenshot_path

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "screen.png"

            self.assertEqual(str(target), prepare_screenshot_path(target))
            self.assertTrue(target.parent.is_dir())
            self.assertEqual(str(target), prepare_screenshot_path(f"  {target}  "))
            self.assertIsNone(prepare_screenshot_path(""))
            self.assertIsNone(prepare_screenshot_path("   "))

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(
                os.environ,
                {"HOME": temp_dir, "USERPROFILE": temp_dir},
            ):
                target = Path(temp_dir) / "screens" / "screen.png"

                self.assertEqual(
                    str(target),
                    prepare_screenshot_path("~/screens/screen.png"),
                )
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

    def test_cortex_view_activation_uses_touch_hit_slop(self):
        from app.app_cortex import CortexView

        view = CortexView.__new__(CortexView)
        view.running = True
        view.run_query = lambda prompt=None: self.fail("query should not run")

        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_HIT_SLOP": "12"}):
            view.activate_at(
                (131, 100),
                back_center=(100, 100),
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

    def test_feature_activation_uses_touch_hit_slop(self):
        import pygame
        from app.feature_shell import activate_feature_at

        class CortexState:
            local_mode = True

        cards = ["Mode de calcul"]
        with mock.patch.dict(os.environ, {"CORTEX_TOUCH_HIT_SLOP": "12"}):
            running = activate_feature_at(
                CortexState,
                "Réglages",
                position=(91, 25),
                back_center=(200, 200),
                back_radius=20,
                card_rects=[pygame.Rect(0, 0, 80, 50)],
                cards=cards,
            )

        self.assertTrue(running)
        self.assertFalse(CortexState.local_mode)


class ToolingDefaultsTests(unittest.TestCase):
    def test_raspberry_pi_launcher_defaults_to_screen_kiosk(self):
        launcher = Path("scripts/launch_raspberry_pi.sh")
        content = launcher.read_text(encoding="utf-8")

        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", content)
        self.assertIn("exec \"$PYTHON_BIN\" Screen.py", content)
        self.assertIn("CORTEX_FULLSCREEN=\"${CORTEX_FULLSCREEN:-true}\"", content)
        self.assertIn("CORTEX_HIDE_CURSOR=\"${CORTEX_HIDE_CURSOR:-true}\"", content)
        self.assertIn("CORTEX_PREVIEW_SIZE=\"${CORTEX_PREVIEW_SIZE:-900}\"", content)
        self.assertIn("CORTEX_FPS=\"${CORTEX_FPS:-60}\"", content)
        self.assertIn("CORTEX_SCREEN_SIZE=\"${CORTEX_SCREEN_SIZE:-480x480}\"", content)
        self.assertIn("CORTEX_TOUCH_ROTATION=\"${CORTEX_TOUCH_ROTATION:-0}\"", content)
        self.assertIn("CORTEX_TOUCH_FLIP_X=\"${CORTEX_TOUCH_FLIP_X:-false}\"", content)
        self.assertIn("CORTEX_TOUCH_FLIP_Y=\"${CORTEX_TOUCH_FLIP_Y:-false}\"", content)
        self.assertIn(
            "CORTEX_TOUCH_ROUND_CLIP=\"${CORTEX_TOUCH_ROUND_CLIP:-true}\"",
            content,
        )
        self.assertIn(
            "CORTEX_TOUCH_EDGE_MARGIN=\"${CORTEX_TOUCH_EDGE_MARGIN:-0}\"",
            content,
        )
        self.assertIn(
            "CORTEX_TOUCH_EDGE_CLAMP=\"${CORTEX_TOUCH_EDGE_CLAMP:-true}\"",
            content,
        )
        self.assertIn("CORTEX_ROUND_MASK=\"${CORTEX_ROUND_MASK:-true}\"", content)
        self.assertIn("CORTEX_TOUCH_HIT_SLOP=\"${CORTEX_TOUCH_HIT_SLOP:-10}\"", content)
        self.assertIn("CORTEX_TAP_MOVE_LIMIT=\"${CORTEX_TAP_MOVE_LIMIT:-14}\"", content)
        self.assertIn(
            "CORTEX_EMPTY_DOUBLE_TAP_MS=\"${CORTEX_EMPTY_DOUBLE_TAP_MS:-500}\"",
            content,
        )
        self.assertIn(
            "CORTEX_EMPTY_DOUBLE_TAP_DISTANCE="
            "\"${CORTEX_EMPTY_DOUBLE_TAP_DISTANCE:-36}\"",
            content,
        )
        self.assertIn(
            "CORTEX_EXIT_AFTER_SCREENSHOT=\"${CORTEX_EXIT_AFTER_SCREENSHOT:-false}\"",
            content,
        )
        self.assertIn(
            "CORTEX_EXIT_AFTER_FRAME=\"${CORTEX_EXIT_AFTER_FRAME:-false}\"",
            content,
        )
        self.assertIn("CORTEX_INPUT_MODE=\"${CORTEX_INPUT_MODE:-voice}\"", content)
        self.assertIn("CORTEX_OUTPUT_MODE=\"${CORTEX_OUTPUT_MODE:-voice}\"", content)
        self.assertIn("CORTEX_LOCAL_MODE=\"${CORTEX_LOCAL_MODE:-true}\"", content)
        self.assertIn("SDL_VIDEODRIVER=\"${SDL_VIDEODRIVER:-kmsdrm}\"", content)
        self.assertIn("SDL_TOUCH_MOUSE_EVENTS=\"${SDL_TOUCH_MOUSE_EVENTS:-0}\"", content)
        self.assertIn("SDL_MOUSE_TOUCH_EVENTS=\"${SDL_MOUSE_TOUCH_EVENTS:-0}\"", content)
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
        self.assertIn("bash -n scripts/launch_raspberry_pi.sh", content)
        self.assertIn("bash -n deploy/raspberry-pi/install_service.sh", content)
        self.assertIn(
            "tools/raspberry_pi_preflight.py \\\n  --project-root .",
            content,
        )
        self.assertIn("--skip-pygame-import", content)
        self.assertIn("--skip-executable-check", content)
        self.assertIn("\"$PYTHON_BIN\" -m compileall -q Screen.py app tools", content)
        self.assertIn("requirements-raspberry-pi.txt", content)
        self.assertIn("\"$VENV_DIR/bin/python\" -m pip check", content)
        self.assertIn(
            "chmod +x scripts/launch_raspberry_pi.sh deploy/raspberry-pi/install_service.sh",
            content,
        )
        self.assertIn("tools/validate_raspberry_pi_ui.py", content)
        self.assertIn("--step-timeout \"${CORTEX_VALIDATE_STEP_TIMEOUT:-120}\"", content)
        self.assertIn("--touch-rotation \"${CORTEX_TOUCH_ROTATION:-0}\"", content)
        self.assertIn("TOUCH_FLIP_ARGS", content)
        self.assertIn("--touch-flip-x", content)
        self.assertIn("--touch-flip-y", content)
        self.assertIn("--screenshot artifacts/screen-smoke.png", content)
        self.assertIn("--legacy-output-dir artifacts/legacy-screen-smoke", content)
        self.assertIn("--modern-output-dir artifacts/modern-screen-smoke", content)

    def test_github_actions_runs_pygame_smokes(self):
        workflow = Path(".github/workflows/core-checks.yml")
        content = workflow.read_text(encoding="utf-8")

        self.assertIn("bash -n scripts/launch_raspberry_pi.sh", content)
        self.assertIn("python tools/run_local_checks.py", content)
        self.assertIn("--screen-size 480x480", content)

    def test_pygame_smokes_disable_sdl_touch_mouse_duplication(self):
        smoke_tools = [
            Path("tools/smoke_home_touch_interactions.py"),
            Path("tools/smoke_modern_touch_interactions.py"),
            Path("tools/smoke_legacy_touch_interactions.py"),
            Path("tools/smoke_touch_rotations.py"),
            Path("tools/smoke_legacy_pygame_screens.py"),
            Path("tools/smoke_modern_pygame_screens.py"),
        ]

        for tool in smoke_tools:
            content = tool.read_text(encoding="utf-8")
            self.assertIn('os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "0")', content)
            self.assertIn('os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")', content)

    def test_pygame_smokes_use_lightweight_screen_size_parser(self):
        smoke_tools = [
            Path("tools/smoke_home_touch_interactions.py"),
            Path("tools/smoke_modern_pygame_screens.py"),
            Path("tools/smoke_modern_touch_interactions.py"),
            Path("tools/smoke_legacy_touch_interactions.py"),
            Path("tools/smoke_touch_rotations.py"),
        ]

        for tool in smoke_tools:
            content = tool.read_text(encoding="utf-8")
            self.assertIn("parse_square_screen_size", content)
            self.assertNotIn("from tools.smoke_legacy_pygame_screens import parse_size", content)

    def test_pygame_smokes_reject_rectangular_pi_sizes(self):
        smoke_modules = [
            "tools.smoke_home_touch_interactions",
            "tools.smoke_modern_pygame_screens",
            "tools.smoke_modern_touch_interactions",
            "tools.smoke_legacy_touch_interactions",
            "tools.smoke_touch_rotations",
            "tools.smoke_legacy_pygame_screens",
        ]

        for module_name in smoke_modules:
            module = __import__(module_name, fromlist=["parse_size"])
            self.assertEqual((480, 480), module.parse_size("480x480"))
            with self.assertRaises(argparse.ArgumentTypeError, msg=module_name):
                module.parse_size("800x480")

        from tools.smoke_touch_rotations import smoke_touch_rotations

        with self.assertRaises(ValueError):
            smoke_touch_rotations((800, 480), rotations=(), flip_cases=())

    def test_touch_smokes_use_shared_touch_rotation_parser(self):
        smoke_tools = [
            Path("tools/smoke_home_touch_interactions.py"),
            Path("tools/smoke_modern_touch_interactions.py"),
            Path("tools/smoke_legacy_touch_interactions.py"),
        ]

        for tool in smoke_tools:
            content = tool.read_text(encoding="utf-8")
            self.assertIn("from tools.touch_config import", content)
            self.assertIn("parse_touch_rotation", content)
            self.assertIn("type=parse_touch_rotation", content)
            self.assertNotIn("choices=(0, 90, 180, 270)", content)

    def test_touch_smokes_reject_invalid_programmatic_rotation(self):
        from tools.smoke_home_touch_interactions import configure_touch_environment
        from tools.smoke_touch_rotations import smoke_touch_rotations

        with self.assertRaises(argparse.ArgumentTypeError):
            configure_touch_environment(touch_rotation=45)
        with self.assertRaises(argparse.ArgumentTypeError):
            smoke_touch_rotations((480, 480), rotations=(45,), flip_cases=())

    def test_touch_smokes_reject_invalid_programmatic_flip_flags(self):
        from tools.smoke_home_touch_interactions import (
            configure_touch_environment,
            touch_fraction_for_screen_position,
        )
        from tools.touch_config import (
            normalize_touch_calibration,
            parse_required_touch_bool,
        )

        self.assertTrue(parse_required_touch_bool("oui"))
        self.assertFalse(parse_required_touch_bool("0"))
        self.assertEqual(
            (90, True, False),
            normalize_touch_calibration("90", "oui", "0"),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_required_touch_bool("maybe")
        with self.assertRaises(argparse.ArgumentTypeError):
            normalize_touch_calibration("45", "oui", "0")
        with self.assertRaises(argparse.ArgumentTypeError):
            configure_touch_environment(touch_flip_x="maybe")
        with self.assertRaises(argparse.ArgumentTypeError):
            touch_fraction_for_screen_position(
                (120, 120),
                (480, 480),
                0,
                touch_flip_y="maybe",
            )

    def test_touch_smokes_use_shared_touch_flip_parser(self):
        content = Path("tools/smoke_home_touch_interactions.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from tools.touch_config import", content)
        self.assertIn("env_touch_bool", content)
        self.assertIn("parse_required_touch_bool", content)
        self.assertIn('env_touch_bool("CORTEX_TOUCH_FLIP_X")', content)
        self.assertIn('env_touch_bool("CORTEX_TOUCH_FLIP_Y")', content)

    def test_raspberry_pi_ui_validator_runs_full_headless_chain(self):
        from tools.validate_raspberry_pi_ui import build_validation_steps, parse_size

        steps = build_validation_steps(
            "python",
            ".",
            parse_size("480*480"),
            "artifacts/screen-smoke.png",
            "artifacts/legacy-screen-smoke",
            "artifacts/modern-screen-smoke",
            touch_rotation=90,
            touch_flip_x=True,
            touch_flip_y=True,
        )
        step_commands = [" ".join(step.command) for step in steps]

        self.assertEqual(
            [
                "Préflight Raspberry Pi",
                "Screen.py un frame headless",
                "Capture Screen.py headless",
                "Validation capture Screen.py",
                "Préflight avec capture",
                "Interactions tactiles menu principal",
                "Interactions tactiles écrans modernes",
                "Interactions tactiles anciens écrans",
                "Interactions tactiles toutes rotations",
                "Smokes anciens écrans Pygame",
                "Smokes écrans Pygame modernes",
            ],
            [step.name for step in steps],
        )
        self.assertIn("python Screen.py", step_commands)
        self.assertEqual("true", steps[1].env["CORTEX_EXIT_AFTER_FRAME"])
        self.assertNotIn("CORTEX_SCREENSHOT_PATH", steps[1].env)
        self.assertIn(
            "python tools/verify_screen_smoke.py artifacts/screen-smoke.png --min-width 400 --min-height 400 --require-round-mask",
            step_commands,
        )
        self.assertIn(
            "python tools/raspberry_pi_preflight.py --project-root . --screenshot artifacts/screen-smoke.png",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_home_touch_interactions.py --size 480x480 --touch-rotation 90 --touch-flip-x --touch-flip-y",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_modern_touch_interactions.py --size 480x480 --touch-rotation 90 --touch-flip-x --touch-flip-y",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_legacy_touch_interactions.py --size 480x480 --touch-rotation 90 --touch-flip-x --touch-flip-y",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_touch_rotations.py --size 480x480",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_legacy_pygame_screens.py --size 480x480 --output-dir artifacts/legacy-screen-smoke --require-round-mask",
            step_commands,
        )
        self.assertIn(
            "python tools/smoke_modern_pygame_screens.py --size 480x480 --output-dir artifacts/modern-screen-smoke --require-round-mask",
            step_commands,
        )
        self.assertEqual("dummy", steps[2].env["SDL_VIDEODRIVER"])
        self.assertEqual("0", steps[2].env["SDL_TOUCH_MOUSE_EVENTS"])
        self.assertEqual("0", steps[2].env["SDL_MOUSE_TOUCH_EVENTS"])
        self.assertEqual("false", steps[2].env["CORTEX_FULLSCREEN"])
        self.assertEqual("480x480", steps[2].env["CORTEX_SCREEN_SIZE"])
        self.assertEqual("90", steps[2].env["CORTEX_TOUCH_ROTATION"])
        self.assertEqual("true", steps[2].env["CORTEX_TOUCH_FLIP_X"])
        self.assertEqual("true", steps[2].env["CORTEX_TOUCH_FLIP_Y"])
        for index in (5, 6, 7, 8, 9, 10):
            self.assertEqual("dummy", steps[index].env["SDL_VIDEODRIVER"])
            self.assertEqual("0", steps[index].env["SDL_TOUCH_MOUSE_EVENTS"])
            self.assertEqual("0", steps[index].env["SDL_MOUSE_TOUCH_EVENTS"])
            self.assertEqual("480x480", steps[index].env["CORTEX_SCREEN_SIZE"])
        for index in (5, 6, 7, 9, 10):
            self.assertEqual("90", steps[index].env["CORTEX_TOUCH_ROTATION"])
            self.assertEqual("true", steps[index].env["CORTEX_TOUCH_FLIP_X"])
            self.assertEqual("true", steps[index].env["CORTEX_TOUCH_FLIP_Y"])

        text_steps = build_validation_steps(
            "python",
            ".",
            parse_size("480x480"),
            "artifacts/screen-smoke.png",
            "artifacts/legacy-screen-smoke",
            "artifacts/modern-screen-smoke",
            touch_rotation="270",
            touch_flip_x="oui",
            touch_flip_y="0",
        )
        text_command = " ".join(text_steps[5].command)
        self.assertIn("--touch-rotation 270", text_command)
        self.assertIn("--touch-flip-x", text_command)
        self.assertNotIn("--touch-flip-y", text_command)
        self.assertEqual("270", text_steps[2].env["CORTEX_TOUCH_ROTATION"])
        self.assertEqual("true", text_steps[2].env["CORTEX_TOUCH_FLIP_X"])
        self.assertEqual("false", text_steps[2].env["CORTEX_TOUCH_FLIP_Y"])
        with self.assertRaises(argparse.ArgumentTypeError):
            build_validation_steps(
                "python",
                ".",
                parse_size("480x480"),
                "artifacts/screen-smoke.png",
                "artifacts/legacy-screen-smoke",
                "artifacts/modern-screen-smoke",
                touch_rotation="45",
            )
        with self.assertRaises(argparse.ArgumentTypeError):
            build_validation_steps(
                "python",
                ".",
                parse_size("480x480"),
                "artifacts/screen-smoke.png",
                "artifacts/legacy-screen-smoke",
                "artifacts/modern-screen-smoke",
                touch_flip_x="maybe",
            )

    def test_legacy_touch_smoke_toggles_settings_both_ways(self):
        from tools.smoke_legacy_touch_interactions import (
            smoke_legacy_touch_interactions,
        )

        smoke_legacy_touch_interactions((240, 240), touch_rotation=90)

    def test_touch_smokes_restore_calibration_environment(self):
        from tools.smoke_home_touch_interactions import (
            restore_touch_environment,
            snapshot_touch_environment,
        )
        from tools.smoke_legacy_touch_interactions import (
            smoke_legacy_touch_interactions,
        )
        from tools import smoke_home_touch_interactions, smoke_modern_touch_interactions

        calibration = {
            "CORTEX_SCREEN_SIZE": "320x320",
            "CORTEX_TOUCH_ROTATION": "270",
            "CORTEX_TOUCH_FLIP_X": "true",
            "CORTEX_TOUCH_FLIP_Y": "false",
        }
        with mock.patch.dict(os.environ, calibration, clear=False):
            smoke_legacy_touch_interactions(
                (240, 240),
                touch_rotation=90,
                touch_flip_x=False,
                touch_flip_y=True,
            )

            for key, value in calibration.items():
                self.assertEqual(value, os.environ.get(key))

            with (
                mock.patch.object(
                    smoke_home_touch_interactions,
                    "CortexHome",
                    side_effect=RuntimeError("stop"),
                ),
                self.assertRaisesRegex(RuntimeError, "stop"),
            ):
                smoke_home_touch_interactions.smoke_home_touch_interactions(
                    (240, 240),
                    touch_rotation=90,
                    touch_flip_x=False,
                    touch_flip_y=True,
                )
            for key, value in calibration.items():
                self.assertEqual(value, os.environ.get(key))

            with (
                mock.patch.object(
                    smoke_modern_touch_interactions.pygame.display,
                    "set_mode",
                    side_effect=RuntimeError("stop"),
                ),
                self.assertRaisesRegex(RuntimeError, "stop"),
            ):
                smoke_modern_touch_interactions.smoke_modern_touch_interactions(
                    (240, 240),
                    touch_rotation=90,
                    touch_flip_x=False,
                    touch_flip_y=True,
                )
            for key, value in calibration.items():
                self.assertEqual(value, os.environ.get(key))

            snapshot = snapshot_touch_environment()
            for key in calibration:
                os.environ[key] = "temporary"
            restore_touch_environment(snapshot)
            for key, value in calibration.items():
                self.assertEqual(value, os.environ.get(key))

    def test_raspberry_pi_ui_validator_times_out_stuck_steps(self):
        from tools.validate_raspberry_pi_ui import ValidationStep, run_step

        step = ValidationStep(
            "Commande lente",
            [sys.executable, "-c", "pass"],
        )

        with (
            mock.patch(
                "tools.validate_raspberry_pi_ui.subprocess.run",
                side_effect=subprocess.TimeoutExpired(step.command, 1),
            ),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(124, run_step(step, ".", 1))

    def test_raspberry_pi_ui_validator_requires_square_size(self):
        from tools.validate_raspberry_pi_ui import build_validation_steps, parse_size

        self.assertEqual((480, 480), parse_size("480x480"))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_size("800x480")
        with self.assertRaises(ValueError):
            build_validation_steps(
                "python",
                ".",
                (800, 480),
                "artifacts/screen-smoke.png",
                "artifacts/legacy-screen-smoke",
                "artifacts/modern-screen-smoke",
            )

    def test_raspberry_pi_ui_validator_rejects_invalid_step_timeout(self):
        from tools.validate_raspberry_pi_ui import positive_int, touch_rotation

        validator_content = Path("tools/validate_raspberry_pi_ui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("positive_int = parse_positive_int", validator_content)
        self.assertNotIn("def positive_int", validator_content)
        self.assertEqual(5, positive_int("5"))
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
        self.assertEqual(270, touch_rotation("270"))
        with self.assertRaises(argparse.ArgumentTypeError):
            touch_rotation("45")

    def test_local_check_runner_covers_autonomous_validation_chain(self):
        from tools.run_local_checks import build_check_steps, secret_findings

        steps = build_check_steps(
            "python",
            "training/finetune_cortex_v3",
            "480x480",
        )
        step_commands = [" ".join(step.command) for step in steps]

        self.assertEqual(
            [
                "Contrôle whitespace Git",
                "Scan secrets fichiers modifiés",
                "Compilation Python",
                "Tests unitaires",
                "Vérification dépendances",
                "Validation dataset fine-tuning",
                "Validation Raspberry Pi/Pygame",
            ],
            [step.name for step in steps],
        )
        self.assertIn("git diff --check", step_commands)
        self.assertIn(
            "python tools/run_local_checks.py --project-root . --secrets-only",
            step_commands,
        )
        self.assertIn(
            "python -m compileall -q Screen.py app function_calling.py model_loader.py tools tests",
            step_commands,
        )
        self.assertIn("python -m unittest discover -s tests -v", step_commands)
        self.assertIn("python -m pip check", step_commands)
        self.assertIn(
            "python tools/validate_finetune_dataset.py --dataset-dir training/finetune_cortex_v3",
            step_commands,
        )
        self.assertIn(
            "python tools/validate_raspberry_pi_ui.py --project-root . --size 480x480",
            step_commands[-1],
        )
        self.assertIn("--step-timeout 300", step_commands[-1])
        self.assertIn("--touch-rotation 0", step_commands[-1])
        flipped_steps = build_check_steps(
            "python",
            "training/finetune_cortex_v3",
            "480x480",
            touch_rotation=270,
            touch_flip_x=True,
            touch_flip_y=True,
        )
        flipped_command = " ".join(flipped_steps[-1].command)
        self.assertIn("--touch-rotation 270", flipped_command)
        self.assertIn("--touch-flip-x", flipped_command)
        self.assertIn("--touch-flip-y", flipped_command)
        text_flipped_steps = build_check_steps(
            "python",
            "training/finetune_cortex_v3",
            "480x480",
            touch_rotation="90",
            touch_flip_x="non",
            touch_flip_y="1",
        )
        text_flipped_command = " ".join(text_flipped_steps[-1].command)
        self.assertIn("--touch-rotation 90", text_flipped_command)
        self.assertNotIn("--touch-flip-x", text_flipped_command)
        self.assertIn("--touch-flip-y", text_flipped_command)
        with self.assertRaises(argparse.ArgumentTypeError):
            build_check_steps(
                "python",
                "training/finetune_cortex_v3",
                "480x480",
                touch_rotation="45",
            )
        with self.assertRaises(argparse.ArgumentTypeError):
            build_check_steps(
                "python",
                "training/finetune_cortex_v3",
                "480x480",
                touch_flip_y="maybe",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            secret_file = root / "secrets.env"
            secret_file.write_text(
                "OPENAI_API_KEY=" + "sk-" + ("a" * 32) + "\n",
                encoding="utf-8",
            )
            placeholder_file = root / "example.env"
            placeholder_file.write_text(
                "OPENAI_API_KEY=your-key-here\n",
                encoding="utf-8",
            )

            findings = secret_findings(
                root,
                ["secrets.env", "example.env"],
            )

        self.assertEqual([("secrets.env", 1, "OpenAI-style API key")], findings)

    def test_local_check_runner_times_out_stuck_steps(self):
        from tools.run_local_checks import CheckStep, run_step

        step = CheckStep(
            "Commande lente",
            [sys.executable, "-c", "pass"],
        )

        with (
            mock.patch(
                "tools.run_local_checks.subprocess.run",
                side_effect=subprocess.TimeoutExpired(step.command, 1),
            ),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(124, run_step(step, ".", 1))

    def test_local_check_runner_rejects_invalid_step_timeout(self):
        from tools.run_local_checks import positive_int, touch_rotation
        from tools.screen_size import (
            format_screen_size,
            format_square_screen_size,
            parse_screen_size,
            parse_square_screen_size,
            require_square_screen_size,
        )
        from tools.touch_config import (
            parse_non_negative_int,
            parse_positive_int,
            parse_touch_bool,
            parse_touch_rotation,
        )

        runner_content = Path("tools/run_local_checks.py").read_text(encoding="utf-8")
        self.assertIn("positive_int = parse_positive_int", runner_content)
        self.assertNotIn("def positive_int", runner_content)
        self.assertEqual(5, positive_int("5"))
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
        self.assertEqual(90, touch_rotation("90"))
        self.assertEqual(270, parse_touch_rotation(" 270 "))
        self.assertEqual(5, parse_positive_int("5"))
        self.assertEqual(0, parse_non_negative_int("0"))
        self.assertTrue(parse_touch_bool(" oui "))
        self.assertFalse(parse_touch_bool(" non "))
        self.assertTrue(parse_touch_bool("maybe", default=True))
        with self.assertRaises(argparse.ArgumentTypeError):
            touch_rotation("45")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_positive_int("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_non_negative_int("-1")
        self.assertEqual((480, 480), parse_screen_size(" 480 * 480 "))
        self.assertEqual((480, 480), parse_screen_size("480×480"))
        self.assertEqual((480, 480), require_square_screen_size((480, 480)))
        self.assertEqual((480, 480), parse_square_screen_size("480*480"))
        with self.assertRaises(ValueError):
            require_square_screen_size((800, 480))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_square_screen_size("800x480")
        self.assertEqual("480x480", format_screen_size("480*480"))
        self.assertEqual("480x480", format_screen_size("480×480"))
        self.assertEqual("480x480", format_square_screen_size("480×480"))
        with self.assertRaises(argparse.ArgumentTypeError):
            format_square_screen_size("800x480")
        with self.assertRaises(argparse.ArgumentTypeError):
            format_screen_size("480")
        with self.assertRaises(argparse.ArgumentTypeError):
            format_screen_size("480x0")

    def test_raspberry_pi_requirements_exclude_heavy_local_model_stack(self):
        requirements = Path("requirements-raspberry-pi.txt").read_text(encoding="utf-8")

        self.assertIn("pygame==2.6.1", requirements)
        self.assertIn("python-dotenv==1.0.1", requirements)
        self.assertNotIn("torch==", requirements)
        self.assertNotIn("transformers==", requirements)
        self.assertNotIn("peft==", requirements)

    def test_raspberry_pi_preflight_reports_missing_runtime_requirement(self):
        from tools.raspberry_pi_preflight import missing_raspberry_pi_requirements

        requirements = "\n".join(
            [
                "pygame==2.6.1",
                "python-dotenv==1.0.1",
                "requests==2.32.3",
                "PyAudio==0.2.14",
                "sounddevice==0.5.1",
                "soundfile==0.12.1",
                "pvporcupine==3.0.3",
            ]
        )

        self.assertEqual(["vosk"], missing_raspberry_pi_requirements(requirements))

    def test_raspberry_pi_preflight_imports_screenshot_validator_lazily(self):
        content = Path("tools/raspberry_pi_preflight.py").read_text(encoding="utf-8")

        self.assertNotIn(
            "from tools.verify_screen_smoke import validate_screen_image\n\n\nREQUIRED_FILES",
            content,
        )
        self.assertIn("from tools.verify_screen_smoke import validate_screen_image", content)

    def test_raspberry_pi_preflight_reports_missing_apt_package(self):
        from tools.raspberry_pi_preflight import missing_raspberry_pi_apt_packages

        setup_script = "\n".join(
            [
                "sudo apt-get install -y \\",
                "  python3-venv \\",
                "  python3-dev \\",
                "  portaudio19-dev \\",
                "  libasound2-dev \\",
                "  libsdl2-2.0-0 \\",
                "  libffi-dev",
            ]
        )

        self.assertEqual(["libsdl2-dev"], missing_raspberry_pi_apt_packages(setup_script))

    def test_raspberry_pi_systemd_service_uses_launcher(self):
        service = Path("deploy/raspberry-pi/cortex.service.example")
        content = service.read_text(encoding="utf-8")

        self.assertIn("WorkingDirectory=/home/pi/Cortex", content)
        self.assertIn(
            "ExecStart=/home/pi/Cortex/scripts/launch_raspberry_pi.sh",
            content,
        )
        self.assertIn("Environment=SDL_TOUCH_MOUSE_EVENTS=0", content)
        self.assertIn("Environment=SDL_MOUSE_TOUCH_EVENTS=0", content)
        self.assertIn("Environment=CORTEX_FULLSCREEN=true", content)
        self.assertIn("Environment=CORTEX_HIDE_CURSOR=true", content)
        self.assertIn("Environment=CORTEX_PREVIEW_SIZE=900", content)
        self.assertIn("Environment=CORTEX_FPS=60", content)
        self.assertIn("Environment=CORTEX_SCREEN_SIZE=480x480", content)
        self.assertIn("Environment=CORTEX_TOUCH_ROTATION=0", content)
        self.assertIn("Environment=CORTEX_TOUCH_FLIP_X=false", content)
        self.assertIn("Environment=CORTEX_TOUCH_FLIP_Y=false", content)
        self.assertIn("Environment=CORTEX_TOUCH_ROUND_CLIP=true", content)
        self.assertIn("Environment=CORTEX_TOUCH_EDGE_MARGIN=0", content)
        self.assertIn("Environment=CORTEX_TOUCH_EDGE_CLAMP=true", content)
        self.assertIn("Environment=CORTEX_ROUND_MASK=true", content)
        self.assertIn("Environment=CORTEX_TOUCH_HIT_SLOP=10", content)
        self.assertIn("Environment=CORTEX_TAP_MOVE_LIMIT=14", content)
        self.assertIn("Environment=CORTEX_EMPTY_DOUBLE_TAP_MS=500", content)
        self.assertIn("Environment=CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36", content)
        self.assertIn("Environment=CORTEX_INPUT_MODE=voice", content)
        self.assertIn("Environment=CORTEX_OUTPUT_MODE=voice", content)
        self.assertIn("Environment=CORTEX_LOCAL_MODE=true", content)
        self.assertIn("Restart=on-failure", content)

    def test_raspberry_pi_service_installer_generates_systemd_unit(self):
        installer = Path("deploy/raspberry-pi/install_service.sh")
        content = installer.read_text(encoding="utf-8")

        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", content)
        self.assertIn("CORTEX_PROJECT_DIR", content)
        self.assertIn("CORTEX_SERVICE_USER", content)
        self.assertIn("scripts/launch_raspberry_pi.sh", content)
        self.assertIn("Environment=SDL_TOUCH_MOUSE_EVENTS=0", content)
        self.assertIn("Environment=SDL_MOUSE_TOUCH_EVENTS=0", content)
        self.assertIn("Environment=CORTEX_FULLSCREEN=true", content)
        self.assertIn("Environment=CORTEX_HIDE_CURSOR=true", content)
        self.assertIn("Environment=CORTEX_PREVIEW_SIZE=900", content)
        self.assertIn("Environment=CORTEX_FPS=60", content)
        self.assertIn("Environment=CORTEX_SCREEN_SIZE=480x480", content)
        self.assertIn("Environment=CORTEX_TOUCH_ROTATION=0", content)
        self.assertIn("Environment=CORTEX_TOUCH_FLIP_X=false", content)
        self.assertIn("Environment=CORTEX_TOUCH_FLIP_Y=false", content)
        self.assertIn("Environment=CORTEX_TOUCH_ROUND_CLIP=true", content)
        self.assertIn("Environment=CORTEX_TOUCH_EDGE_MARGIN=0", content)
        self.assertIn("Environment=CORTEX_TOUCH_EDGE_CLAMP=true", content)
        self.assertIn("Environment=CORTEX_ROUND_MASK=true", content)
        self.assertIn("Environment=CORTEX_TOUCH_HIT_SLOP=10", content)
        self.assertIn("Environment=CORTEX_TAP_MOVE_LIMIT=14", content)
        self.assertIn("Environment=CORTEX_EMPTY_DOUBLE_TAP_MS=500", content)
        self.assertIn("Environment=CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36", content)
        self.assertIn("Environment=CORTEX_INPUT_MODE=voice", content)
        self.assertIn("Environment=CORTEX_OUTPUT_MODE=voice", content)
        self.assertIn("Environment=CORTEX_LOCAL_MODE=true", content)
        self.assertIn("systemd-analyze verify \"${SERVICE_FILE}\"", content)
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
        self.assertEqual(0, stats["masked_corners"])
        self.assertGreater(stats["outside_round_pixels"], 0)

    def test_screen_smoke_validator_accepts_round_masked_capture(self):
        import pygame
        from tools.verify_screen_smoke import validate_screen_image

        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "round.png"
                surface = pygame.Surface((320, 320))
                surface.fill((0, 0, 0))
                for index in range(10):
                    pygame.draw.circle(
                        surface,
                        (40 + index * 20, 90 + index * 9, 180),
                        (50 + index * 24, 160),
                        18,
                    )
                pygame.image.save(surface, target)

                stats = validate_screen_image(
                    target,
                    min_width=300,
                    min_height=300,
                    require_round_mask=True,
                )
        finally:
            pygame.quit()

        self.assertEqual(4, stats["masked_corners"])
        self.assertGreater(stats["outside_round_samples"], 0)
        self.assertEqual(0, stats["outside_round_pixels"])

    def test_screen_smoke_formatter_reports_round_mask_stats(self):
        from tools.verify_screen_smoke import format_screen_stats

        summary = format_screen_stats(
            {
                "width": 480,
                "height": 480,
                "unique_colors": 42,
                "bright_pixels": 24,
                "masked_corners": 4,
                "outside_round_pixels": 0,
                "outside_round_samples": 158,
            }
        )

        self.assertIn("480x480", summary)
        self.assertIn("42 couleurs", summary)
        self.assertIn("0/158 pixels hors cercle visibles", summary)

    def test_screen_smoke_validator_rejects_missing_round_mask(self):
        import pygame
        from tools.verify_screen_smoke import validate_screen_image

        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "square.png"
                surface = pygame.Surface((320, 320))
                surface.fill((210, 30, 30))
                for index in range(10):
                    pygame.draw.circle(
                        surface,
                        (40 + index * 20, 90 + index * 9, 180),
                        (32 + index * 28, 160),
                        18,
                    )
                pygame.image.save(surface, target)

                with self.assertRaisesRegex(ValueError, "Masque rond"):
                    validate_screen_image(
                        target,
                        min_width=300,
                        min_height=300,
                        require_round_mask=True,
                    )
        finally:
            pygame.quit()

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

    def test_modern_screen_smoke_tool_covers_catalog(self):
        from Screen import APP_DEFINITIONS
        from tools.smoke_modern_pygame_screens import FEATURE_SPECS, screen_slug

        expected_names = [name for name, _ in APP_DEFINITIONS if name != "Cortex"]

        self.assertEqual(expected_names, [spec.app_name for spec in FEATURE_SPECS])
        self.assertEqual("sante", screen_slug("Santé"))
        self.assertEqual("mots_de_passe", screen_slug("Mots de passe"))
        self.assertEqual("meteo", screen_slug("Météo"))
        self.assertTrue(
            all(spec.name.isascii() for spec in FEATURE_SPECS),
            [spec.name for spec in FEATURE_SPECS if not spec.name.isascii()],
        )

    def test_touch_rotation_smoke_tool_covers_all_quadrants(self):
        from tools import smoke_touch_rotations
        from tools.smoke_touch_rotations import TOUCH_FLIP_CASES, TOUCH_ROTATIONS

        self.assertEqual((0, 90, 180, 270), TOUCH_ROTATIONS)
        self.assertEqual(
            ((False, False), (True, False), (False, True), (True, True)),
            TOUCH_FLIP_CASES,
        )
        with (
            mock.patch.object(
                smoke_touch_rotations,
                "smoke_home_touch_interactions",
            ) as home_smoke,
            mock.patch.object(
                smoke_touch_rotations,
                "smoke_modern_touch_interactions",
            ) as modern_smoke,
            mock.patch.object(
                smoke_touch_rotations,
                "smoke_legacy_touch_interactions",
            ) as legacy_smoke,
        ):
            checked = smoke_touch_rotations.smoke_touch_rotations(
                (240, 240),
                rotations=(90,),
                flip_cases=(("true", "0"),),
            )

        self.assertEqual([(90, True, False)], checked)
        home_smoke.assert_called_once_with(
            (240, 240),
            touch_rotation=90,
            touch_flip_x=True,
            touch_flip_y=False,
        )
        modern_smoke.assert_called_once_with(
            (240, 240),
            touch_rotation=90,
            touch_flip_x=True,
            touch_flip_y=False,
        )
        legacy_smoke.assert_called_once_with(
            (240, 240),
            touch_rotation=90,
            touch_flip_x=True,
            touch_flip_y=False,
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            smoke_touch_rotations.smoke_touch_rotations(
                (240, 240),
                rotations=(),
                flip_cases=(("maybe", False),),
            )

    def test_legacy_screen_smoke_tool_covers_bdd_view(self):
        from tools.smoke_legacy_pygame_screens import SCREEN_SPECS

        self.assertIn("bdd", [spec.name for spec in SCREEN_SPECS])

    def test_raspberry_pi_preflight_accepts_repo_layout(self):
        from tools.raspberry_pi_preflight import collect_preflight_errors

        errors = collect_preflight_errors(
            ".",
            check_pygame=False,
            require_executable=False,
        )

        self.assertEqual([], errors)

    def test_raspberry_pi_preflight_validates_touch_config_values(self):
        from tools.raspberry_pi_preflight import invalid_touch_config_values

        valid_content = "\n".join(
            [
                "CORTEX_TOUCH_ROTATION=90",
                'export CORTEX_TOUCH_FLIP_X="${CORTEX_TOUCH_FLIP_X:-oui}"',
                "Environment=CORTEX_TOUCH_FLIP_Y=false",
            ]
        )
        invalid_content = "\n".join(
            [
                "CORTEX_TOUCH_ROTATION=45",
                'export CORTEX_TOUCH_FLIP_X="${CORTEX_TOUCH_FLIP_X:-maybe}"',
            ]
        )

        self.assertEqual([], invalid_touch_config_values(".env.example", valid_content))
        errors = invalid_touch_config_values("scripts/launch_raspberry_pi.sh", invalid_content)
        self.assertTrue(any("CORTEX_TOUCH_ROTATION=45" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_FLIP_X=maybe" in error for error in errors))

    def test_raspberry_pi_preflight_validates_screen_size_values(self):
        from tools.raspberry_pi_preflight import invalid_screen_size_values

        valid_content = "\n".join(
            [
                "CORTEX_SCREEN_SIZE=",
                'export CORTEX_SCREEN_SIZE="${CORTEX_SCREEN_SIZE:-480*480}"',
                "Environment=CORTEX_SCREEN_SIZE=480x480",
            ]
        )
        invalid_content = 'export CORTEX_SCREEN_SIZE="${CORTEX_SCREEN_SIZE:-480}"'
        rectangular_content = "Environment=CORTEX_SCREEN_SIZE=800x480"

        self.assertEqual([], invalid_screen_size_values(".env.example", valid_content))
        errors = invalid_screen_size_values("scripts/launch_raspberry_pi.sh", invalid_content)
        rectangular_errors = invalid_screen_size_values(
            "deploy/raspberry-pi/cortex.service.example",
            rectangular_content,
        )
        self.assertTrue(any("CORTEX_SCREEN_SIZE=480" in error for error in errors))
        self.assertTrue(
            any("CORTEX_SCREEN_SIZE=800x480" in error for error in rectangular_errors)
        )

    def test_raspberry_pi_preflight_validates_numeric_kiosk_values(self):
        from tools.raspberry_pi_preflight import invalid_numeric_config_values

        valid_content = "\n".join(
            [
                "CORTEX_PREVIEW_SIZE=900",
                'export CORTEX_FPS="${CORTEX_FPS:-60}"',
                "Environment=CORTEX_TOUCH_EDGE_MARGIN=0",
                "Environment=CORTEX_TOUCH_HIT_SLOP=10",
                "Environment=CORTEX_TAP_MOVE_LIMIT=14",
                "Environment=CORTEX_EMPTY_DOUBLE_TAP_MS=500",
                "Environment=CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36",
                'export CORTEX_VALIDATE_STEP_TIMEOUT="${CORTEX_VALIDATE_STEP_TIMEOUT:-120}"',
            ]
        )
        invalid_content = "\n".join(
            [
                "CORTEX_PREVIEW_SIZE=0",
                "Environment=CORTEX_FPS=0",
                "Environment=CORTEX_TOUCH_HIT_SLOP=-1",
                'export CORTEX_TAP_MOVE_LIMIT="${CORTEX_TAP_MOVE_LIMIT:-wide}"',
                "CORTEX_VALIDATE_STEP_TIMEOUT=0",
            ]
        )

        self.assertEqual([], invalid_numeric_config_values("service", valid_content))
        errors = invalid_numeric_config_values("service", invalid_content)
        self.assertTrue(any("CORTEX_PREVIEW_SIZE=0" in error for error in errors))
        self.assertTrue(any("CORTEX_FPS=0" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_HIT_SLOP=-1" in error for error in errors))
        self.assertTrue(any("CORTEX_TAP_MOVE_LIMIT=wide" in error for error in errors))
        self.assertTrue(
            any("CORTEX_VALIDATE_STEP_TIMEOUT=0" in error for error in errors)
        )

    def test_raspberry_pi_preflight_validates_boolean_kiosk_values(self):
        from tools.raspberry_pi_preflight import invalid_boolean_config_values

        valid_content = "\n".join(
            [
                'export CORTEX_FULLSCREEN="${CORTEX_FULLSCREEN:-true}"',
                "Environment=CORTEX_HIDE_CURSOR=true",
                "Environment=CORTEX_FRAMELESS=false",
                "Environment=CORTEX_EXIT_AFTER_SCREENSHOT=off",
                "Environment=CORTEX_EXIT_AFTER_FRAME=false",
                "Environment=CORTEX_SKIP_CORTEX_LOAD=oui",
                "Environment=CORTEX_LOCAL_MODE=true",
                "Environment=CORTEX_TOUCH_ROUND_CLIP=oui",
                "Environment=CORTEX_TOUCH_EDGE_CLAMP=non",
                "Environment=CORTEX_ROUND_MASK=1",
            ]
        )
        invalid_content = "\n".join(
            [
                "Environment=CORTEX_FULLSCREEN=fullscreen",
                "Environment=CORTEX_EXIT_AFTER_SCREENSHOT=close",
                "Environment=CORTEX_EXIT_AFTER_FRAME=stop",
                "Environment=CORTEX_LOCAL_MODE=offline",
                'export CORTEX_ROUND_MASK="${CORTEX_ROUND_MASK:-maybe}"',
            ]
        )

        self.assertEqual([], invalid_boolean_config_values("service", valid_content))
        errors = invalid_boolean_config_values("service", invalid_content)
        self.assertTrue(any("CORTEX_FULLSCREEN=fullscreen" in error for error in errors))
        self.assertTrue(
            any("CORTEX_EXIT_AFTER_SCREENSHOT=close" in error for error in errors)
        )
        self.assertTrue(any("CORTEX_EXIT_AFTER_FRAME=stop" in error for error in errors))
        self.assertTrue(any("CORTEX_LOCAL_MODE=offline" in error for error in errors))
        self.assertTrue(any("CORTEX_ROUND_MASK=maybe" in error for error in errors))

    def test_raspberry_pi_preflight_validates_runtime_mode_values(self):
        from tools.raspberry_pi_preflight import invalid_runtime_mode_values

        valid_content = "\n".join(
            [
                "CORTEX_INPUT_MODE=voice",
                'export CORTEX_INPUT_MODE="${CORTEX_INPUT_MODE:-text}"',
                "Environment=CORTEX_OUTPUT_MODE=voice",
                "Environment=CORTEX_OUTPUT_MODE=text",
                "Environment=CORTEX_OUTPUT_MODE=screen",
            ]
        )
        invalid_content = "\n".join(
            [
                "Environment=CORTEX_INPUT_MODE=microphone",
                'export CORTEX_OUTPUT_MODE="${CORTEX_OUTPUT_MODE:-display}"',
            ]
        )

        self.assertEqual([], invalid_runtime_mode_values("service", valid_content))
        errors = invalid_runtime_mode_values("service", invalid_content)
        self.assertTrue(any("CORTEX_INPUT_MODE=microphone" in error for error in errors))
        self.assertTrue(any("CORTEX_OUTPUT_MODE=display" in error for error in errors))

    def test_env_example_documents_raspberry_pi_screen_settings(self):
        content = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("CORTEX_FULLSCREEN=true", content)
        self.assertIn("CORTEX_PREVIEW_SIZE=900", content)
        self.assertIn("CORTEX_FRAMELESS=false", content)
        self.assertIn("CORTEX_HIDE_CURSOR=true", content)
        self.assertIn("CORTEX_FPS=60", content)
        self.assertIn("CORTEX_SCREEN_SIZE=", content)
        self.assertIn("CORTEX_TOUCH_ROTATION=0", content)
        self.assertIn("CORTEX_TOUCH_FLIP_X=false", content)
        self.assertIn("CORTEX_TOUCH_FLIP_Y=false", content)
        self.assertIn("CORTEX_TOUCH_ROUND_CLIP=true", content)
        self.assertIn("CORTEX_TOUCH_EDGE_MARGIN=0", content)
        self.assertIn("CORTEX_TOUCH_EDGE_CLAMP=true", content)
        self.assertIn("CORTEX_ROUND_MASK=true", content)
        self.assertIn("CORTEX_TOUCH_HIT_SLOP=10", content)
        self.assertIn("CORTEX_TAP_MOVE_LIMIT=14", content)
        self.assertIn("CORTEX_EMPTY_DOUBLE_TAP_MS=500", content)
        self.assertIn("CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36", content)
        self.assertIn("CORTEX_VALIDATE_STEP_TIMEOUT=120", content)
        self.assertIn("CORTEX_SCREENSHOT_PATH=", content)
        self.assertIn("CORTEX_EXIT_AFTER_SCREENSHOT=false", content)
        self.assertIn("CORTEX_EXIT_AFTER_FRAME=false", content)
        self.assertIn("CORTEX_SKIP_CORTEX_LOAD=false", content)
        self.assertIn("CORTEX_INPUT_MODE=voice", content)
        self.assertIn("CORTEX_OUTPUT_MODE=voice", content)
        self.assertIn("CORTEX_LOCAL_MODE=true", content)

    def test_env_example_documents_oauth_token_overrides(self):
        content = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("SPOTIFY_TOKEN_FILE=", content)
        self.assertIn("FLASK_SECRET_KEY=", content)
        self.assertIn("FLASK_DEBUG=false", content)
        self.assertIn("OAUTHLIB_INSECURE_TRANSPORT=1", content)
        self.assertIn("OAUTH2_SESSION_COOKIE_SECURE=false", content)
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
                "tools/validate_raspberry_pi_ui.py",
                "tools/smoke_home_touch_interactions.py",
                "tools/smoke_modern_touch_interactions.py",
                "tools/smoke_legacy_touch_interactions.py",
                "tools/smoke_touch_rotations.py",
                "tools/smoke_legacy_pygame_screens.py",
                "tools/smoke_modern_pygame_screens.py",
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

    def test_raspberry_pi_preflight_reports_missing_touch_settings(self):
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
                "tools/validate_raspberry_pi_ui.py",
                "tools/smoke_home_touch_interactions.py",
                "tools/smoke_modern_touch_interactions.py",
                "tools/smoke_legacy_touch_interactions.py",
                "tools/smoke_touch_rotations.py",
                "tools/smoke_legacy_pygame_screens.py",
                "tools/smoke_modern_pygame_screens.py",
            ):
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# placeholder\n", encoding="utf-8")

            (root / ".env.example").write_text(
                "\n".join(
                    [
                        "CORTEX_FULLSCREEN=true",
                        "CORTEX_HIDE_CURSOR=true",
                        "CORTEX_SCREEN_SIZE=",
                        "CORTEX_TOUCH_ROTATION=0",
                        "CORTEX_TOUCH_ROUND_CLIP=true",
                        "CORTEX_TOUCH_EDGE_MARGIN=0",
                        "CORTEX_TOUCH_EDGE_CLAMP=true",
                    ]
                ),
                encoding="utf-8",
            )

            errors = collect_preflight_errors(
                root,
                check_pygame=False,
                require_executable=False,
            )

        self.assertTrue(any("SDL_TOUCH_MOUSE_EVENTS" in error for error in errors))
        self.assertTrue(any("CORTEX_FPS" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_FLIP_X" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_FLIP_Y" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_ROUND_CLIP" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_EDGE_CLAMP" in error for error in errors))
        self.assertTrue(any("CORTEX_TOUCH_HIT_SLOP" in error for error in errors))
        self.assertTrue(any("CORTEX_TAP_MOVE_LIMIT" in error for error in errors))
        self.assertTrue(any("CORTEX_EMPTY_DOUBLE_TAP_MS" in error for error in errors))
        self.assertTrue(
            any("CORTEX_EMPTY_DOUBLE_TAP_DISTANCE" in error for error in errors)
        )
        self.assertTrue(any("CORTEX_EXIT_AFTER_FRAME" in error for error in errors))
        self.assertTrue(any("CORTEX_INPUT_MODE" in error for error in errors))
        self.assertTrue(any("CORTEX_OUTPUT_MODE" in error for error in errors))
        self.assertTrue(any("CORTEX_LOCAL_MODE" in error for error in errors))
        self.assertTrue(
            any(
                "deploy/raspberry-pi/install_service.sh" in error
                and "Environment=CORTEX_SCREEN_SIZE=480x480" in error
                for error in errors
            )
        )
        self.assertTrue(
            any("chmod +x scripts/launch_raspberry_pi.sh" in error for error in errors)
        )


class RepositoryHygieneTests(unittest.TestCase):
    def test_oauth_helper_uses_safe_runtime_defaults(self):
        content = Path("oauth2/app.py").read_text(encoding="utf-8")

        self.assertIn('os.getenv("FLASK_SECRET_KEY")', content)
        self.assertIn('app.config["SESSION_COOKIE_HTTPONLY"] = True', content)
        self.assertIn('app.config["SESSION_COOKIE_SAMESITE"] = "Lax"', content)
        self.assertIn('app.config["SESSION_COOKIE_SECURE"] = env_flag(', content)
        self.assertIn(
            'os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")',
            content,
        )
        self.assertIn('debug=env_flag("FLASK_DEBUG", default=False)', content)
        self.assertNotIn("os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'", content)
        self.assertNotIn("app.run(debug=True", content)

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
