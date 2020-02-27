import aiohttp.client
import textwrap
import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO


class SpotifyImage:
    def __init__(self, bot):
        self.bot = bot
        self.session = self.bot.session
        self.font = ImageFont.truetype("arial-unicode-ms.ttf", 16)

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
            duration = f"{self.bot.seconds_to_hms(track_duration * percentage_played)} / {self.bot.seconds_to_hms(track_duration)}"
            im_draw.text((175, 130), duration, font=self.font, fill=(255, 255, 255, 255))
        else:
            im_draw.text((175, 130), self.bot.seconds_to_hms(track_duration), font=self.font, fill=(255, 255, 255, 255))

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


class RankImage:
    def __init__(self):
        self.font = ImageFont.truetype("arialbd.ttf", 56)
        self.medium_font = ImageFont.truetype("arialbd.ttf", 44)
        self.small_font = ImageFont.truetype("arialbd.ttf", 32)

    def draw(self, user, lvl, xp, profile_bytes: BytesIO, color, bg):
        xp_to_next = round((4 * (lvl ** 3) / 5))

        profile_bytes = Image.open(profile_bytes)
        size = (256, 256)
        profile_bytes = profile_bytes.resize(size)
        if bg is not None and bg != "default":
            bg_img = Image.open(f"backgrounds/{bg}.jpg")
            im = ImageOps.fit(bg_img, (800, 296), centering=(0.0, 0.0))
        else:
            im = Image.new("RGBA", (800, 296), (44, 44, 44, 255))

        im_draw = ImageDraw.Draw(im)
        im_draw.text((308, 10), user, font=self.font, fill=color)

        lvl_text = f"LEVEL {lvl}"
        im_draw.text((308, 74), lvl_text, font=self.medium_font, fill=(255, 255, 255, 255))

        xp_text = f"{xp}/{xp_to_next}"
        im_draw.text((308, 124), xp_text, font=self.small_font, fill=(255, 255, 255, 255))

        im_draw.rectangle((350, 190, 750, 250), fill=(64, 64, 64, 255))
        progress = xp / xp_to_next
        im_draw.rectangle((350, 190, 350 + int(400 * progress), 125*2), fill=color)

        im_draw.rectangle((0, 0, 296, 296), fill=color)

        # Rounded square mask.
        # rounded_square = Image.open("/opt/discord-v2/github/minesoc/square-rounded-256.png")
        # im.paste(profile_bytes, (10*2, 10*2), rounded_square)

        im.paste(profile_bytes, (20, 20))

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer
