import importlib.util
from unittest import TestCase, mock


class IDFMGuardTests(TestCase):
    def require_dependencies(self):
        required = ["requests", "dotenv"]
        missing = [
            module_name
            for module_name in required
            if importlib.util.find_spec(module_name) is None
        ]
        if missing:
            self.skipTest(
                "Dépendances IDFM absentes: " + ", ".join(missing)
            )

    def test_get_coords_reports_http_error_without_printing(self):
        self.require_dependencies()

        from assistant.ratp import ratp_assistant

        class FailedResponse:
            status_code = 503
            text = "backend unavailable"

        assistant = ratp_assistant.IDFMAssistant()
        assistant.idfm_api_key = "idfm-key"

        with mock.patch.object(
            ratp_assistant.requests,
            "get",
            return_value=FailedResponse(),
        ):
            with mock.patch("builtins.print") as print_mock:
                coords = assistant.get_coords("Paris")

        self.assertIsNone(coords)
        self.assertEqual("Erreur IDFM lieux 503.", assistant.error_message)
        print_mock.assert_not_called()

    def test_calculate_route_surfaces_place_lookup_error(self):
        self.require_dependencies()

        from assistant.ratp import ratp_assistant

        assistant = ratp_assistant.IDFMAssistant()
        assistant.idfm_api_key = "idfm-key"

        def fake_get_coords(city_name):
            assistant.error_message = f"Erreur réseau IDFM : {city_name}"
            return None

        assistant.get_coords = fake_get_coords

        self.assertEqual(
            "Erreur réseau IDFM : Paris",
            assistant.calculate_route("Paris", "Lyon"),
        )
