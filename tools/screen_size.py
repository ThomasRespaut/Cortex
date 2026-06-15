import argparse


def parse_screen_size(value):
    normalized = value.lower().replace("*", "x")
    if "x" not in normalized:
        raise argparse.ArgumentTypeError("Format attendu: largeurxhauteur")
    width_text, height_text = normalized.split("x", 1)
    try:
        width = int(width_text.strip())
        height = int(height_text.strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("La taille doit contenir deux entiers") from error
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("La taille doit être positive")
    return width, height


def format_screen_size(value):
    width, height = parse_screen_size(value)
    return f"{width}x{height}"
