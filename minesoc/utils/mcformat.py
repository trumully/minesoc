import discord


def status_embed(status, context):

    raw = status.raw
    req = {"description": raw["description"]["text"], "player_count": raw["players"]["online"],
           "player_max": raw["players"]["max"], "version": raw["version"]["name"], "latency": status.latency,
           "title": raw["title"]}

    player_list = []
    try:
        for i in raw["players"]["sample"]:
            player_list.append(i["name"])
    except KeyError:
        pass

    embed = discord.Embed(title=req["title"], description=req["description"], colour=0x00ff00)
    embed.add_field(name="Version", value=req["version"])
    embed.add_field(name="Players", value=f"{req['player_count']}/{req['player_max']}")
    embed.add_field(name="Latency", value=f"{req['latency']} ms")
    embed.set_footer(text=context.author.name, icon_url=context.author.avatar_url)

    return embed
