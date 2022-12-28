import discord
import util
import audio


token = util.get_token()
intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot = audio.MediaPlayer(client=client)


@client.event
async def on_message(msg):
    prefix = util.get_prefix()
    if msg.author != client.user and msg.content.lower().startswith(prefix):
        msg.content: str = msg.content.removeprefix(prefix)

        if msg.content.startswith("ping"):
            await msg.channel.send("pong!")
            
        elif msg.content.startswith("play"):
            await bot.play(msg)

        elif msg.content.startswith("pause"):
            await bot.pause(msg)

        elif msg.content.startswith("resume"):
            await bot.resume(msg)

        elif msg.content.startswith("skip"):
            await bot.skip(msg)

        elif msg.content.startswith("loop"):
            await bot.loop(msg)

        elif msg.content.startswith("leave"):
            await bot.disconnect(msg)

        elif msg.content.startswith("prefix"):
            await util.set_prefix(msg)

        elif msg.content.startswith("queue"):
            await bot.print_queue(msg)

client.run(token)
