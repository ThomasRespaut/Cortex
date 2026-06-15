import argparse


TOUCH_ROTATIONS = (0, 90, 180, 270)


def parse_touch_rotation(value):
    try:
        parsed = int(str(value).strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("La rotation doit être un entier") from error
    if parsed not in TOUCH_ROTATIONS:
        raise argparse.ArgumentTypeError("La rotation tactile doit être 0, 90, 180 ou 270")
    return parsed
