import importlib.util
from unittest import TestCase, mock


class FilmAndSeriesGuardTests(TestCase):
    def test_propose_recommendations_skips_prompt_when_non_interactive(self):
        if (
            importlib.util.find_spec("requests") is None
            or importlib.util.find_spec("dotenv") is None
        ):
            self.skipTest("Dépendances média absentes.")

        from assistant.films_and_series import films_and_series

        with mock.patch.object(
            films_and_series.sys.stdin,
            "isatty",
            return_value=False,
        ):
            with mock.patch.object(
                films_and_series,
                "get_genre_list",
            ) as get_genre_list:
                with mock.patch("builtins.input") as prompt:
                    with mock.patch("builtins.print") as print_mock:
                        result = films_and_series.propose_recommendations(
                            media_type="movie"
                        )

        self.assertEqual([], result)
        get_genre_list.assert_not_called()
        prompt.assert_not_called()
        print_mock.assert_called_once_with(
            "Recherche films/séries interactive indisponible."
        )
