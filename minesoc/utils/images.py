from io import BytesIO
from math import log, floor
from PIL import Image, ImageDraw, ImageFont, ImageOps


def human_format(number):
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    if magnitude == 0:
        return number
    else:
        return '%.2f%s' % (number / k ** magnitude, units[magnitude])


class Profile:
    def __init__(self):
        self.font = ImageFont.truetype("arialbd.ttf", 56)
        self.medium_font = ImageFont.truetype("arialbd.ttf", 44)
        self.small_font = ImageFont.truetype("arialbd.ttf", 32)

    def round_corner(self, radius, fill):
        corner = Image.new('RGBA', (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)
        return corner

    def round_rectangle(self, size, radius, fill):
        width, height = size
        rectangle = Image.new('RGBA', size, fill)
        corner = self.round_corner(radius, fill)
        rectangle.paste(corner, (0, 0))
        rectangle.paste(corner.rotate(90), (0, height - radius))  # Rotate the corner and paste it
        rectangle.paste(corner.rotate(180), (width - radius, height - radius))
        rectangle.paste(corner.rotate(270), (width - radius, 0))

        return rectangle

    def draw(self, user, lvl, xp, profile_bytes: BytesIO, color, bg):
        profile_bytes = Image.open(profile_bytes)
        w, h = (256, 256)
        profile_bytes = profile_bytes.resize((w, h))

        if bg is not None and bg != "default":
            bg_img = Image.open(f"backgrounds/{bg}.jpg")
            im = ImageOps.fit(bg_img, (800, 296), centering=(0.0, 0.0))
        else:
            im = Image.new("RGBA", (800, 296), (44, 44, 44, 255))

        im_draw = ImageDraw.Draw(im)

        # User name
        im_draw.text((350, 10), user, font=self.font, fill=color)

        # Level
        lvl_text = f"LEVEL {lvl}"
        im_draw.text((350, 74), lvl_text, font=self.medium_font, fill=(255, 255, 255, 255))

        # XP progress
        xp_text = f"{human_format(xp)} / {human_format(round((4 * (lvl ** 3) / 5)))} XP"
        im_draw.text((350, 124), xp_text, font=self.small_font, fill=(255, 255, 255, 255))

        # XP progress bar
        """im_draw.rectangle((350, 190, 750, 250), fill=(64, 64, 64, 255))
        progress = xp / round((4 * (lvl ** 3) / 5))
        im_draw.rectangle((350, 190, 350 + int(400 * progress), 250), fill=color)"""

        progress = xp / round((4 * (lvl ** 3) / 5))

        img = self.round_rectangle((400, 60), 30, (64, 64, 64, 255))
        im.paste(img, (350, 190), img)

        img2 = self.round_rectangle((int(400 * progress), 60), 30, color)
        im.paste(img2, (350, 190), img2)

        # Avatar border
        im_draw.ellipse((28, 0, w + 40 + 28, h + 40), fill=color)

        # Avatar
        circle = Image.open("images/circle.png")
        im.paste(profile_bytes, (48, 20), circle)

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer

    def circle(self, draw, center, radius, fill):
        draw.ellipse(
            (center[0] - radius + 1, center[1] - radius + 1, center[0] + radius - 1, center[1] + radius - 1),
            fill=fill, outline=None
        )
