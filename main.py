import discord
import json
from audio import MediaPlayer
import json

settings_path = "src/settings.json"

with open(settings_path ,"r") as file:
    info = json.loads(file.read())


token = info["private"]["discord"]["token"]
intents = discord.Intents.all()
client = discord.Client(intents=intents)

bot = MediaPlayer(client=client)



def get_prefix():
    with open(settings_path ,"r") as file:
        info = json.loads(file.read())
    return info["prefix"]


async def set_prefix(ctx):
    new_prefix = ctx.content.split(" ")[1]

    if len(new_prefix) == 1:
        
        with open("src/settings.json","r") as file:
            info = json.loads(file.read())
        
        info["prefix"] = new_prefix

        with open("src/settings.json","w") as file:
            json.dump(info, file, indent=4)

        await ctx.channel.send(f'"{new_prefix}" has been set as a new prefix!')

    else:
        await ctx.channel.send(f'You cannot set "{new_prefix}" as a prefix!')



@client.event
async def on_message(msg):
    prefix = get_prefix()
    if msg.author != client.user and msg.content.lower().startswith(prefix):
        msg.content: str = msg.content.removeprefix(prefix)

        if msg.content.startswith("ping"):
            await msg.channel.send("pong!")
            print(msg.channel)

            
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
            await set_prefix(msg)

        elif msg.content.startswith("queue"):
            await bot.print_queue(msg)




client.run(token)
