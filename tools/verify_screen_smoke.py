import argparse
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


def corner_pixels(surface):
    width, height = surface.get_size()
    return [
        surface.get_at((0, 0)),
        surface.get_at((width - 1, 0)),
        surface.get_at((0, height - 1)),
        surface.get_at((width - 1, height - 1)),
    ]


def analyze_surface(surface, grid_size=24):
    width, height = surface.get_size()
    colors = set()
    bright_pixels = 0
    masked_corners = 0

    for x_index in range(grid_size):
        x = min(width - 1, round(x_index * (width - 1) / max(1, grid_size - 1)))
        for y_index in range(grid_size):
            y = min(height - 1, round(y_index * (height - 1) / max(1, grid_size - 1)))
            color = surface.get_at((x, y))
            colors.add((color.r, color.g, color.b, color.a))
            if max(color.r, color.g, color.b) >= 80 and color.a >= 128:
                bright_pixels += 1

    for color in corner_pixels(surface):
        if max(color.r, color.g, color.b) <= 8 and color.a >= 128:
            masked_corners += 1

    return {
        "width": width,
        "height": height,
        "unique_colors": len(colors),
        "bright_pixels": bright_pixels,
        "masked_corners": masked_corners,
    }


def validate_screen_image(
    path,
    min_width=300,
    min_height=300,
    min_unique_colors=8,
    min_bright_pixels=12,
    require_round_mask=False,
):
    image_path = Path(path)
    if not image_path.is_file():
        raise ValueError(f"Capture introuvable: {image_path}")

    surface = pygame.image.load(str(image_path))
    stats = analyze_surface(surface)
    if stats["width"] < min_width or stats["height"] < min_height:
        raise ValueError(
            f"Capture trop petite: {stats['width']}x{stats['height']} "
            f"(minimum {min_width}x{min_height})"
        )
    if stats["unique_colors"] < min_unique_colors:
        raise ValueError(
            f"Capture trop uniforme: {stats['unique_colors']} couleurs échantillonnées"
        )
    if stats["bright_pixels"] < min_bright_pixels:
        raise ValueError(
            f"Capture trop sombre: {stats['bright_pixels']} pixels clairs échantillonnés"
        )
    if require_round_mask and stats["masked_corners"] < 4:
        raise ValueError(
            "Masque rond absent ou incomplet: "
            f"{stats['masked_corners']}/4 coins noirs"
        )
    return stats


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérifie qu'une capture smoke test de Screen.py est lisible."
    )
    parser.add_argument("path", help="Chemin de la capture PNG générée.")
    parser.add_argument("--min-width", type=int, default=300)
    parser.add_argument("--min-height", type=int, default=300)
    parser.add_argument("--min-unique-colors", type=int, default=8)
    parser.add_argument("--min-bright-pixels", type=int, default=12)
    parser.add_argument(
        "--require-round-mask",
        action="store_true",
        help="Exige des coins noirs, signe que le framebuffer est masqué en cercle.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        stats = validate_screen_image(
            args.path,
            min_width=args.min_width,
            min_height=args.min_height,
            min_unique_colors=args.min_unique_colors,
            min_bright_pixels=args.min_bright_pixels,
            require_round_mask=args.require_round_mask,
        )
    except ValueError as error:
        print(f"Validation capture écran échouée: {error}")
        return 1

    print(
        "Capture écran OK: "
        f"{stats['width']}x{stats['height']}, "
        f"{stats['unique_colors']} couleurs, "
        f"{stats['bright_pixels']} pixels clairs échantillonnés, "
        f"{stats['masked_corners']}/4 coins noirs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
