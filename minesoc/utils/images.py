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
        self.name_font = ImageFont.truetype("arialbd.ttf", 64)
        self.level_font = ImageFont.truetype("arialbd.ttf", 48)
        self.xp_font = ImageFont.truetype("arialbd.ttf", 32)

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
        profile_bytes = profile_bytes.resize((128, 128))

        im_w, im_h = (900, 300)
        im = Image.new("RGBA", (im_w, im_h), color)
        im_draw = ImageDraw.Draw(im)

        # Backdrop
        pad_x, pad_y = (10, 20)
        bd_w, bd_h = (im_w - pad_x, im_h - pad_y)  # 890x280
        backdrop = self.round_rectangle((bd_w, bd_h), 20, fill=(22, 22, 22, 255))
        if bg != "default":
            bg_img = Image.open(f"backgrounds/{bg}.jpg")
            im.paste(bg_img, (pad_x, pad_y), backdrop)
        else:
            im.paste(backdrop, (pad_x, pad_y), backdrop)

        # Avatar
        circle = Image.open("images/circle.png")
        im.paste(profile_bytes, (pad_x + 20, pad_y + 76), circle)

        # User name
        name_x, name_y = (pad_x + (im_w // 4), pad_y + (im_h // 4))
        im_draw.text((name_x, name_y), user, font=self.name_font, fill=color)

        # Level
        lvl_text = f"LEVEL {lvl}"
        lvl_x, lvl_y = (name_x, name_y + 25)
        im_draw.text((lvl_x, lvl_y), lvl_text, font=self.level_font, fill=(255, 255, 255, 255))

        # XP progress
        xp_text = f"{human_format(xp)} / {human_format(round((4 * (lvl ** 3) / 5)))} XP"
        xp_x, xp_y = (name_x + 25, name_y)
        im_draw.text((xp_x, xp_y), xp_text, font=self.xp_font, fill=(255, 255, 255, 255))

        # XP progress bar
        progress = xp / round((4 * (lvl ** 3) / 5))

        img = self.round_rectangle((400, 60), 30, (64, 64, 64, 255))
        im.paste(img, (name_x, name_y + 25), img)

        img2 = self.round_rectangle((int(400 * progress), 60), 30, color)
        im.paste(img2, (name_x, name_y + 25), img2)

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
