import discord 


async def send_embed(ctx, title, url, color, name, thumbnail, fields=None):
    embed=discord.Embed(title=title, url=url, color=color)
    embed.set_author(name=name)
    embed.set_thumbnail(url=thumbnail)

    if fields != None:
        for field in fields:
            embed.add_field(name=field, value = '\u200b', inline=False)

    await ctx.channel.send(embed=embed)


