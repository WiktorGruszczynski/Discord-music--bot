import json

settings_path = "src/settings.json"

def get_prefix():
    with open(settings_path ,"r") as file:
        info = json.loads(file.read())
    return info["prefix"]

def get_token():
    with open(settings_path ,"r") as file:
        info = json.loads(file.read())
    return info["private"]["discord"]["token"]


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