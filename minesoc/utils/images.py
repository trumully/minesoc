import textwrap
import aiohttp
import datetime

from io import BytesIO
from math import log, floor
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path


def human_format(number):
    units = ["", "K", "M", "G", "T", "P"]
    k = 1000.0
    magnitude = int(floor(log(number, k))) if number > 0 else int(floor(log(1, k)))
    if magnitude == 0:
        return number
    else:
        return "%.2f%s" % (number / k ** magnitude, units[magnitude])


def seconds_to_hms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        return "%02d:%02d" % (minutes, seconds)
    return "%d:%02d:%02d" % (hour, minutes, seconds)


class Profile:
    def __init__(self):
        self.font = ImageFont.truetype("arialbd.ttf", 56)
        self.medium_font = ImageFont.truetype("arialbd.ttf", 44)
        self.small_font = ImageFont.truetype("arialbd.ttf", 32)

    def round_corner(self, radius, fill):
        corner = Image.new("RGBA", (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)
        return corner

    def round_rectangle(self, size, radius, fill):
        width, height = size
        rectangle = Image.new("RGBA", size, fill)
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

        if bg != "default":
            bg_img = False
            for img in Path("backgrounds/").iterdir():
                if img.name[:-4] == bg:
                    bg_img = Image.open(f"backgrounds/{img.name}")
            if bg_img:
                im = ImageOps.fit(bg_img, (800, 296), centering=(0.0, 0.0))
            else:
                im = Image.new("RGBA", (800, 296), (44, 44, 44, 255))
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


class SpotifyImage:
    def __init__(self):
        self.font = ImageFont.truetype("arial-unicode-ms.ttf", 16)
        self.session = aiohttp.ClientSession()

    def draw(self, name, artists, color, album_bytes: BytesIO, track_duration=None, time_end=None):
        album_bytes = Image.open(album_bytes)
        size = (160, 160)
        album_bytes = album_bytes.resize(size)

        w, h = (500, 170)
        im = Image.new("RGBA", (w, h), color)

        im_draw = ImageDraw.Draw(im)
        off_x, off_y, w, h = (5, 5, 495, 165)

        font_size = 1
        max_size = 20
        img_fraction = 0.75

        medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)
        while medium_font.getsize(name)[0] < img_fraction * im.size[0]:
            font_size += 1
            medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)

        if font_size >= max_size:
            font_size = max_size

        font_size -= 1
        medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)

        im_draw.rectangle((off_x, off_y, w, h), fill=(5, 5, 25))
        im_draw.text((175, 15), name, font=medium_font, fill=(255, 255, 255, 255))

        artist_text = ", ".join(artists)
        artist_text = "\n".join(textwrap.wrap(artist_text, width=35))
        im_draw.text((175, 45), artist_text, font=self.font, fill=(255, 255, 255, 255))

        if time_end is not None and track_duration is not None:
            now = datetime.datetime.utcnow()
            percentage_played = 1 - (time_end - now).total_seconds() / track_duration.total_seconds()
            im_draw.rectangle((175, 130, 375, 125), fill=(64, 64, 64, 255))
            im_draw.rectangle((175, 130, 175 + int(200 * percentage_played), 125), fill=(254, 254, 254, 255))

            track_duration = track_duration.total_seconds()
            duration = f"{seconds_to_hms(track_duration * percentage_played)} / {seconds_to_hms(track_duration)}"
            im_draw.text((175, 130), duration, font=self.font, fill=(255, 255, 255, 255))
        else:
            im_draw.text((175, 130), seconds_to_hms(track_duration), font=self.font, fill=(255, 255, 255, 255))

        im.paste(album_bytes, (5, 5))

        spotify_logo = Image.open("images/spotify-512.png")
        spotify_logo = spotify_logo.resize((48, 48))
        im.paste(spotify_logo, (437, 15), spotify_logo)

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer

    async def fetch_cover(self, cover_url):
        async with self.session as s:
            async with s.get(cover_url) as r:
                if r.status == 200:
                    return await r.read()
