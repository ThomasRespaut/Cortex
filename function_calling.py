import importlib
import inspect
import json
import shlex
from functools import lru_cache

from assistant import functions


def _coerce_value(value):
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"none", "null"}:
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_tool_call(response):
    """Parse a model tool call formatted as ``[tool_name key='value']``."""
    start = response.find("[")
    end = response.find("]", start + 1)
    if start == -1 or end == -1:
        return None

    try:
        parts = shlex.split(response[start + 1:end])
    except ValueError as error:
        raise ValueError(f"Commande d'outil invalide: {error}") from error

    if not parts:
        return None

    tool_name = parts[0]
    if not tool_name.replace("_", "").isalnum():
        raise ValueError("Nom d'outil invalide")

    arguments = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"Argument invalide: {part}")
        key, value = part.split("=", 1)
        if not key or not key.replace("_", "").isalnum():
            raise ValueError(f"Nom d'argument invalide: {key}")
        if key in arguments:
            raise ValueError(f"Argument dupliqué: {key}")
        arguments[key] = _coerce_value(value)

    return tool_name, arguments


@lru_cache(maxsize=None)
def _provider(module_name, class_name):
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()


def _lazy_method(module_name, class_name, method_name):
    def call(**kwargs):
        instance = _provider(module_name, class_name)
        return getattr(instance, method_name)(**kwargs)

    return call


def _normalize_tool_call(tool_name, arguments):
    """Map common legacy model tool names to the current Cortex registry."""
    if tool_name == "play_music":
        track_name = (
            arguments.get("track_name")
            or arguments.get("title")
            or arguments.get("song")
            or arguments.get("query")
        )
        if track_name:
            return "play_track", {"track_name": track_name}

        genre = arguments.get("genre") or arguments.get("genre_name")
        if genre:
            return "play_recommendations_track", {"genre_name": genre}

        return "resume_playback", {}

    if tool_name in {"add_task", "add_to_do", "create_task"}:
        task_title = (
            arguments.get("task_title")
            or arguments.get("title")
            or arguments.get("task")
            or arguments.get("list")
        )
        task_notes = arguments.get("task_notes") or arguments.get("notes") or ""
        if task_title:
            return "create_google_task", {
                "task_title": task_title,
                "task_notes": task_notes,
            }

    return tool_name, arguments


def _recommend_media(**kwargs):
    module = importlib.import_module(
        "assistant.films_and_series.films_and_series"
    )
    return module.recommend_media(**kwargs)


def _call_tool(tool, arguments):
    try:
        signature = inspect.signature(tool)
    except (TypeError, ValueError):
        return tool(**arguments)

    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return tool(**arguments)

    accepted_names = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind
        in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }
    compatible_arguments = {
        name: value
        for name, value in arguments.items()
        if name in accepted_names
    }
    return tool(**compatible_arguments)


@lru_cache(maxsize=1)
def get_tools():
    """Build the registry without authenticating external providers."""
    tools = {
        "get_current_time": functions.get_current_time,
        "generate_random_number": functions.generate_random_number,
        "recommend_media": _recommend_media,
    }

    providers = {
        "spotify": (
            "assistant.spotify.spotify_assistant",
            "SpotifyAssistant",
            [
                "play_track",
                "pause_playback",
                "resume_playback",
                "next_track",
                "previous_track",
                "set_volume",
                "get_current_playback",
                "play_recommendations_track",
            ],
        ),
        "apple": (
            "assistant.apple.iphone",
            "AppleAssistant",
            [
                "get_iphone_battery",
                "get_location",
                "get_weather",
                "get_contacts",
                "play_sound_on_iphone",
                "activate_lost_mode",
            ],
        ),
        "ratp": (
            "assistant.ratp.ratp_assistant",
            "IDFMAssistant",
            ["calculate_route"],
        ),
        "google": (
            "assistant.google.google_assistant",
            "GoogleAssistant",
            [
                "create_google_task",
                "create_calendar_event",
                "summarize_today_emails",
                "list_and_analyze_today_emails",
                "collect_emails",
                "mark_as_read",
                "trash_message",
                "archive_message",
                "reply_to_message",
                "create_email",
                "display_draft",
                "create_draft_reply",
                "send_draft",
            ],
        ),
    }

    for module_name, class_name, methods in providers.values():
        for method_name in methods:
            tools[method_name] = _lazy_method(
                module_name,
                class_name,
                method_name,
            )

    return tools


def execute_tool(response, tools=None):
    """Parse and execute one tool call from a model response."""
    try:
        parsed = parse_tool_call(response)
    except ValueError as error:
        return f"Commande invalide: {error}"

    if not parsed:
        return "Aucune commande reconnue dans la réponse."

    tool_name, arguments = _normalize_tool_call(*parsed)
    registry = tools if tools is not None else get_tools()
    tool = registry.get(tool_name)
    if tool is None:
        return f"Outil '{tool_name}' non reconnu."

    try:
        return _call_tool(tool, arguments)
    except TypeError as error:
        return f"Arguments invalides pour l'outil '{tool_name}': {error}"
    except Exception as error:
        return f"Erreur d'exécution pour l'outil '{tool_name}': {error}"


def execute_file(input_file):
    with open(input_file, encoding="utf-8") as source:
        data = json.load(source)

    for item in data:
        response = item["response"]
        user_input = input(
            f"Voulez-vous exécuter cette commande : {response} ? (oui/non)\n"
        )
        if user_input.strip().lower() == "oui":
            print(execute_tool(response))
        else:
            print("Commande ignorée.")


if __name__ == "__main__":
    print(execute_tool("[generate_random_number min_value=1 max_value=10]"))
