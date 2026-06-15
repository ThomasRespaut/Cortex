import argparse
import os


TOUCH_ROTATIONS = (0, 90, 180, 270)
TRUTHY = {"1", "true", "yes", "on", "oui"}
FALSY = {"0", "false", "no", "off", "non"}


def parse_touch_rotation(value):
    try:
        parsed = int(str(value).strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("La rotation doit être un entier") from error
    if parsed not in TOUCH_ROTATIONS:
        raise argparse.ArgumentTypeError("La rotation tactile doit être 0, 90, 180 ou 270")
    return parsed


def parse_touch_bool(value, default=False):
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in TRUTHY:
        return True
    if normalized in FALSY:
        return False
    return default


def parse_required_touch_bool(value):
    parsed = parse_touch_bool(value, default=None)
    if parsed is None:
        raise argparse.ArgumentTypeError(
            "La valeur tactile booléenne doit être true/false, 1/0, oui/non"
        )
    return parsed


def env_touch_bool(name, default=False):
    return parse_touch_bool(os.getenv(name), default=default)
