import urllib.request as request
import asyncio
import discord
import youtube_dl
import spotipy
import json
import re
import message
from processor import BetterThread as Thread
import unidecode


def youtube_search(quote:str):
    words = quote.split(' ')

    scope = [f"{i}+" for i in words]
    scope[-1] = scope[-1][:-1]

    url = "https://www.youtube.com/results?search_query=" + "".join(scope)
        
    html = request.urlopen(url).read().decode("utf-8")

    videos = re.findall(r"watch\?v=(\S{11})", html)

    video_url = f"https://www.youtube.com/watch?v={videos[0]}"
        
    return video_url



async def youtube_playlist(url:str) -> list:
    html = request.urlopen(url).read().decode("utf-8")
    videos = re.findall(r"watch\?v=(\S{57})", html)

    url_list = ["https://www.youtube.com/watch?v="+id[:11] for id in videos if id.endswith("\\")]
    
    return url_list




class YoutubeSource:
    def __init__(self, options=None) -> None:
        self.id = None
        self.audio = None
        self.title = None
        self.duration = None
        self.options = options
        self.thumbnail = None
        self.platform = "youtube"

        if options == None:
            self.options = {'format': 'bestaudio'}

    async def youtube_audio(self, url:str):
        try:
            ytdl = youtube_dl.YoutubeDL(self.options)
            loop = asyncio.get_event_loop()
        
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            metadata = data["formats"][0]["url"].split("&")
            self.duration = float([i for i in metadata if i.startswith("dur")][0].split('=')[1])
            self.audio = data["formats"][0]["url"]
            self.title = data["title"]
            self.id = data["id"]
            self.thumbnail = data["thumbnail"]
            self.url = url

            if self.duration > 14400:
                return 1

        except:
            return 1

        del metadata
        return self



class SpotifySource(YoutubeSource):
    def __init__(self, options=None) -> None:
        super().__init__(options)
        self.client()


    def credentials(self):
        with open("src/settings.json","r") as file: info = json.loads(file.read())
        client_secret = info["private"]["spotify"]["api key"]
        client_id = info["private"]["spotify"]["client id"]
        return client_id, client_secret


    def client(self):
        client_id, client_secret = self.credentials()
        client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id, client_secret)
        self.sp_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


    async def spotify_audio(self, url:str):
        track_id = url.removeprefix("https://open.spotify.com/track/")[:22]
        track = self.sp_client.track(track_id)
        
        self.name = track["name"]
        self.author = ", ".join([i["name"] for i in track["artists"]])


        title = unidecode.unidecode(f"{self.author} - {self.name}")
        song_url = youtube_search(quote=title)
        await self.youtube_audio(song_url)
        self.title = title
        self.thumbnail = track["album"]["images"][2]["url"]
        self.url = url
        self.platform = "spotify"

        return self


    async def spotify_playlist(self, url:str):
        id = url.removeprefix("https://open.spotify.com/playlist/")[:22]
        playlist = self.sp_client.playlist(id)
        track_list = playlist["tracks"]["items"]

        songs = []
        for track in track_list:
            name = track["track"]["name"]
            author = ", ".join([i["name"] for i in track["track"]["artists"]])
            title = f"{author} - {name}"
            track_url = track["track"]["external_urls"]["spotify"]
            songs.append([title, track_url])

        return songs
        


class MediaPlayer:
    def __init__(self, client) -> None:
        self.client = client
        self.voice_client = None
        self.voice_clients = {}
        self.queue = []
        self.ffmpeg_path = r"src\ffmpeg\ffmpeg.exe"
        self.opts = {'options': '-vn -loglevel trace',
                    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"}
        self._loop = False
        self.paused = False
        self.iter = 0
    


    async def join(self, ctx):
        if self.voice_client == None or self.voice_client.is_connected()==False:
            if self.voice_client == None:
                self.voice_client = await ctx.author.voice.channel.connect()
            else:
                self.voice_client = await ctx.author.voice.channel.connect()

            self.voice_clients[self.voice_client.guild.id] = self.voice_client



    async def play_audio(self, ctx, source: YoutubeSource|SpotifySource):
        player = discord.FFmpegPCMAudio(source.audio, executable=self.ffmpeg_path,**self.opts)
        self.voice_clients[ctx.guild.id].play(player)

        await asyncio.sleep(0.3)
        if self.voice_client.is_playing():
            if source.platform == "youtube":
                color = 0xff0000
            elif source.platform == "spotify":
                color = 0x00a815

            await message.send_embed(ctx,title=source.title,url=source.url,color=color,name="Playing now",thumbnail=source.thumbnail)
        else:
            await message.send_embed(ctx,title=f"Couldn't play track '{source.title}'",url=None, color=0xff0000,name= "Error",thumbnail=None)


    async def play_queue(self, ctx):
        if not self.voice_clients[ctx.guild.id].is_playing():
            for source in self.queue: 
                if source == 1:
                    continue
                
                await self.play_audio(ctx, source)
                while self.paused != self.voice_clients[ctx.guild.id].is_playing(): 
                    await asyncio.sleep(0.2)

                self.iter+=1
                if self._loop:
                    self.queue.insert(self.iter, self.queue[self.iter-1])

            if self.voice_clients[ctx.guild.id].is_playing()==False and self.paused==False:
                self.queue.clear()


    async def play(self, ctx):
        if ctx.author.voice == None: return 
        words = ctx.content.split(" ")
        if len(words) <= 1: return
        url = "".join(words[1:])

        if not url.startswith("http"):
            scope = unidecode.unidecode(url)
            url = youtube_search(scope)

        if url.startswith("https://www.youtube.com/watch?v="):
            video = YoutubeSource()
            await video.youtube_audio(url)
            self.queue.append(video)
            try:
                if self.voice_clients[ctx.guild.id].is_playing():
                    await message.send_embed(ctx,title=video.title,url=video.url,color=0xff0000,name="Added to queue",thumbnail=video.thumbnail)
            except: pass

        elif url.startswith("https://open.spotify.com/track/"):
            track = SpotifySource()
            await track.spotify_audio(url)
            self.queue.append(track)

        elif url.startswith("https://www.youtube.com/playlist?") or "&index=" in url:
            url_list = await youtube_playlist(url)
            threads = []
            for url in url_list:
                threads.append(Thread(target=asyncio.run, args=(YoutubeSource().youtube_audio(url))))
                
            [th.start() for th in threads]
            while any([thread.is_alive() for thread in threads]): await asyncio.sleep(0.1)
            for result in threads:
                if result.value != 1:
                    self.queue.append(result.value)

        elif url.startswith("https://open.spotify.com/playlist"):
            playlist = await SpotifySource().spotify_playlist(url)
            threads = []

            for track in playlist:
                threads.append(Thread(target=asyncio.run, args=(SpotifySource().spotify_audio(track[1]))))

            [thread.start() for thread in threads]
            while any([thread.is_alive() for thread in threads]): await asyncio.sleep(0.1)
            for result in threads:
                if result.value != 1:
                    self.queue.append(result.value)

        await self.join(ctx)
        await self.play_queue(ctx)


    async def loop(self, ctx):
        if self._loop == False:
            self._loop = True
            words = ctx.content.split(' ')

            if len(words) > 1:
                url = "".join(words[1:])

                if not url.startswith("http"):
                    url = youtube_search(url)
            else:
                url = self.queue[self.iter]
                self.queue.insert(self.iter, url)
            
            self.iter += 1
            await self.join(ctx)
            if self.voice_clients[ctx.guild.id].is_playing() == False:
                await self.play(ctx)

        elif self._loop:
            self._loop = False
            self.queue.pop(self.iter)
            

    async def pause(self, ctx):
        if self.voice_clients[ctx.guild.id] != None:
            if self.voice_clients[ctx.guild.id].is_playing():
                self.voice_clients[ctx.guild.id].pause()
                self.paused = True


    async def resume(self, ctx):
        if self.voice_clients[ctx.guild.id] != None:
            self.voice_clients[ctx.guild.id].resume()
            self.paused = False


    async def skip(self, ctx):
        if self.voice_clients[ctx.guild.id] != None:
            if self.voice_clients[ctx.guild.id].is_playing():
                self.voice_clients[ctx.guild.id].stop()

                
            
    async def disconnect(self, ctx):
        if self.voice_clients[ctx.guild.id] != None:
            self.voice_clients[ctx.guild.id].stop()
            await self.voice_clients[ctx.guild.id].disconnect()
            self.queue.clear()
            self.iter = 0


    async def print_queue(self, ctx):
        fields = [f"{i+1}. {self.queue[i].title}" for i in range(self.iter, len(self.queue))]
        await message.send_embed(ctx, title="Queue songs", url=None, color=0xff0000, fields=fields, name="", thumbnail=None)
        
