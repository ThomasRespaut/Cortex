from pathlib import Path
from PIL import Image, ImageDraw


SIZE = 512
CENTER = SIZE // 2
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "Images" / "app_icons_v2"


APPS = {
    "icone_cortex.png": ("cortex", "#7A5CFF", "#36C7FF"),
    "icone_horloge.png": ("clock", "#202124", "#050505"),
    "icone_musique.png": ("music", "#FF375F", "#E6003D"),
    "icone_transport.png": ("train", "#32A7FF", "#006BE6"),
    "icone_sante.png": ("health", "#FF7895", "#FF2D55"),
    "icone_reseau_social.png": ("network", "#A56EFF", "#6F36E8"),
    "icone_calendrier.png": ("calendar", "#FF5B57", "#E63030"),
    "icone_message.png": ("message", "#5BE46C", "#18B83E"),
    "icone_jeu.png": ("game", "#FF6B62", "#EE3028"),
    "icone_actualites.png": ("news", "#5AAEFF", "#1479EE"),
    "icone_bdd.png": ("database", "#36D6C4", "#08A99B"),
    "icone_divertissement.png": ("play", "#FF72C6", "#D839A0"),
    "icone_domotique.png": ("home", "#FFB44A", "#F07819"),
    "icone_finance.png": ("finance", "#9AD83F", "#54A91D"),
    "icone_mot_de_passe.png": ("lock", "#FFB54C", "#F0781C"),
    "icone_reglage.png": ("settings", "#AAB2BD", "#68717D"),
    "icone_restauration.png": ("food", "#FF9F43", "#F05A25"),
    "icone_vetement.png": ("shirt", "#51A8FF", "#236CE1"),
    "icone_education.png": ("book", "#9B7BFF", "#6347D9"),
    "icone_meteo.png": ("weather", "#55C8FF", "#1688F2"),
    "icone_supermarche.png": ("cart", "#54D878", "#17A84D"),
    "icone_traduction.png": ("translate", "#54B8FF", "#3872E8"),
}


def point(draw, xy, radius, color):
    x, y = xy
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def line(draw, points, color, width=22, joint="curve"):
    draw.line(points, fill=color, width=width, joint=joint)


def rounded(draw, box, radius, outline, width=18, fill=None):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def symbol(draw, name, color):
    c = color
    pale = "#EAFBFF"

    if name == "cortex":
        for angle in range(0, 360, 45):
            import math
            x = CENTER + math.cos(math.radians(angle)) * 92
            y = CENTER + math.sin(math.radians(angle)) * 92
            line(draw, [(CENTER, CENTER), (x, y)], c, 18)
            point(draw, (x, y), 17, pale)
        point(draw, (CENTER, CENTER), 52, c)
        point(draw, (CENTER, CENTER), 20, pale)
    elif name == "clock":
        draw.ellipse((145, 145, 367, 367), outline=c, width=22)
        line(draw, [(256, 256), (256, 188)], pale, 20)
        line(draw, [(256, 256), (312, 288)], c, 20)
        point(draw, (256, 256), 14, pale)
    elif name == "music":
        line(draw, [(225, 180), (225, 310)], c, 24)
        line(draw, [(225, 185), (327, 160), (327, 280)], c, 24)
        point(draw, (188, 322), 38, pale)
        point(draw, (290, 292), 38, pale)
    elif name == "train":
        rounded(draw, (170, 125, 342, 340), 54, c, 20)
        rounded(draw, (198, 160, 314, 235), 18, pale, 14)
        point(draw, (215, 285), 17, c)
        point(draw, (297, 285), 17, c)
        line(draw, [(195, 380), (235, 336)], pale, 18)
        line(draw, [(317, 380), (277, 336)], pale, 18)
    elif name == "health":
        line(draw, [(130, 265), (195, 265), (222, 205), (265, 323), (296, 247), (382, 247)], c, 20)
        draw.arc((155, 122, 357, 350), 205, 335, fill=pale, width=18)
    elif name == "network":
        nodes = [(170, 190), (342, 190), (256, 322)]
        line(draw, nodes + [nodes[0]], c, 18)
        for node in nodes:
            point(draw, node, 34, pale)
            point(draw, node, 14, c)
    elif name == "calendar":
        rounded(draw, (140, 155, 372, 360), 30, c, 20)
        line(draw, [(140, 215), (372, 215)], c, 18)
        for x in (195, 256, 317):
            for y in (260, 315):
                point(draw, (x, y), 12, pale)
        line(draw, [(195, 125), (195, 180)], pale, 18)
        line(draw, [(317, 125), (317, 180)], pale, 18)
    elif name == "message":
        rounded(draw, (125, 155, 387, 330), 58, c, 20)
        draw.polygon([(195, 325), (172, 386), (254, 330)], fill=c)
        for x in (205, 256, 307):
            point(draw, (x, 244), 13, pale)
    elif name == "game":
        rounded(draw, (125, 185, 387, 330), 60, c, 20)
        line(draw, [(190, 235), (190, 285)], pale, 18)
        line(draw, [(165, 260), (215, 260)], pale, 18)
        point(draw, (310, 238), 14, pale)
        point(draw, (338, 278), 14, pale)
    elif name == "news":
        rounded(draw, (140, 145, 372, 360), 24, c, 20)
        rounded(draw, (175, 180, 250, 255), 12, pale, 12)
        for y in (190, 225, 270, 310):
            line(draw, [(275 if y < 260 else 175, y), (335, y)], pale, 14)
    elif name == "database":
        for y in (165, 245, 325):
            draw.ellipse((150, y - 42, 362, y + 42), outline=c, width=18)
        line(draw, [(150, 165), (150, 325)], c, 18)
        line(draw, [(362, 165), (362, 325)], c, 18)
    elif name == "play":
        draw.ellipse((135, 135, 377, 377), outline=c, width=20)
        draw.polygon([(225, 190), (225, 322), (330, 256)], fill=pale)
    elif name == "home":
        line(draw, [(135, 250), (256, 145), (377, 250)], c, 24)
        rounded(draw, (175, 235, 337, 365), 12, pale, 18)
        rounded(draw, (238, 285, 285, 365), 8, c, 12)
    elif name == "finance":
        line(draw, [(155, 330), (225, 260), (275, 290), (360, 185)], c, 24)
        line(draw, [(310, 185), (360, 185), (360, 235)], pale, 18)
        for x, h in ((175, 60), (240, 100), (305, 145)):
            rounded(draw, (x, 350 - h, x + 38, 350), 8, pale, 0, pale)
    elif name == "lock":
        rounded(draw, (160, 220, 352, 365), 30, c, 20)
        draw.arc((195, 125, 317, 285), 180, 360, fill=pale, width=22)
        point(draw, (256, 280), 18, pale)
        line(draw, [(256, 295), (256, 325)], pale, 14)
    elif name == "settings":
        draw.ellipse((170, 170, 342, 342), outline=c, width=32)
        point(draw, (256, 256), 45, pale)
        for x, y in ((256, 125), (256, 387), (125, 256), (387, 256)):
            rounded(draw, (x - 17, y - 38, x + 17, y + 38), 10, c, 0, c)
    elif name == "food":
        line(draw, [(195, 150), (195, 360)], c, 20)
        for x in (165, 195, 225):
            line(draw, [(x, 150), (x, 235)], pale, 13)
        line(draw, [(165, 235), (225, 235)], pale, 13)
        draw.ellipse((275, 145, 342, 252), outline=pale, width=16)
        line(draw, [(309, 240), (309, 360)], c, 20)
    elif name == "shirt":
        draw.polygon(
            [(180, 155), (225, 135), (256, 180), (287, 135), (332, 155), (380, 225),
             (330, 260), (330, 370), (182, 370), (182, 260), (132, 225)],
            outline=c,
            fill=None,
        )
        line(draw, [(180, 155), (225, 135), (256, 180), (287, 135), (332, 155)], c, 20)
        line(draw, [(180, 155), (132, 225), (182, 260), (182, 370), (330, 370), (330, 260), (380, 225), (332, 155)], c, 20)
    elif name == "book":
        rounded(draw, (130, 155, 252, 355), 18, c, 18)
        rounded(draw, (260, 155, 382, 355), 18, c, 18)
        line(draw, [(256, 175), (256, 360)], pale, 14)
        for y in (210, 255, 300):
            line(draw, [(160, y), (225, y)], pale, 12)
            line(draw, [(287, y), (352, y)], pale, 12)
    elif name == "weather":
        point(draw, (205, 205), 58, c)
        for angle in range(0, 360, 45):
            import math
            x1 = 205 + math.cos(math.radians(angle)) * 82
            y1 = 205 + math.sin(math.radians(angle)) * 82
            x2 = 205 + math.cos(math.radians(angle)) * 108
            y2 = 205 + math.sin(math.radians(angle)) * 108
            line(draw, [(x1, y1), (x2, y2)], c, 12)
        rounded(draw, (185, 255, 375, 340), 42, pale, 0, pale)
        point(draw, (235, 270), 55, pale)
        point(draw, (310, 250), 72, pale)
    elif name == "cart":
        line(draw, [(135, 165), (170, 165), (205, 310), (345, 310), (375, 215), (190, 215)], c, 20)
        point(draw, (225, 355), 20, pale)
        point(draw, (325, 355), 20, pale)
    elif name == "translate":
        rounded(draw, (125, 150, 290, 315), 28, c, 18)
        rounded(draw, (230, 205, 387, 365), 28, pale, 18)
        line(draw, [(160, 205), (255, 205)], pale, 12)
        line(draw, [(207, 180), (207, 280)], pale, 12)
        line(draw, [(165, 255), (250, 215)], pale, 12)
        line(draw, [(285, 320), (320, 240), (355, 320)], c, 14)
        line(draw, [(296, 292), (344, 292)], c, 12)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def make_icon(filename, spec):
    name, top_color, bottom_color = spec
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    top = hex_rgb(top_color)
    bottom = hex_rgb(bottom_color)
    gradient = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for y in range(SIZE):
        ratio = y / (SIZE - 1)
        rgb = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        gradient_draw.line((0, y, SIZE, y), fill=(*rgb, 255))

    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((24, 24, 488, 488), fill=255)
    image.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(image)
    symbol(draw, name, "#FFFFFF")
    image.save(OUTPUT / filename)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, spec in APPS.items():
        make_icon(filename, spec)
        print(filename)


if __name__ == "__main__":
    main()
