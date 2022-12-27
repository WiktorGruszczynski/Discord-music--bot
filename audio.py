import urllib.request as request
import asyncio
import discord
import youtube_dl
import spotipy
import json
import re
import message
from processor import *
import unidecode
import math


def youtube_search(quote:str):
    words = quote.split(' ')

    scope = [f"{i}+" for i in words]
    scope[-1] = scope[-1][:-1]

    url = "https://www.youtube.com/results?search_query=" + "".join(scope)
        
    html = request.urlopen(url).read().decode("utf-8")

    videos = re.findall(r"watch\?v=(\S{11})", html)

    video_url = f"https://www.youtube.com/watch?v={videos[0]}"
        
    return video_url

def spotify_credentials():
    with open("src/settings.json","r") as file: info = json.loads(file.read())
    client_secret = info["private"]["spotify"]["api key"]
    client_id = info["private"]["spotify"]["client id"]
    return client_id, client_secret


class YoutubeSource:
    def __init__(self, options=None) -> None:
        self.id = None
        self.audio = None
        self.title = None
        self.duration = None
        self.options = options
        self.thumbnail = None
        self.platform = "youtube"
        self.url = None

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

    async def youtube_playlist(self, url:str) -> list:
        html = request.urlopen(url).read().decode("utf-8")
        videos = re.findall(r"watch\?v=(\S{57})", html)

        url_list = ["https://www.youtube.com/watch?v="+id[:11] for id in videos if id.endswith("\\")]
        
        return url_list


class SpotifySource(YoutubeSource):
    def __init__(self, credentials, options=None) -> None:
        super().__init__(options)
        self.client_id, self.client_secret = credentials
        self.client()

    def client(self):
        client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(self.client_id, self.client_secret)
        self.sp_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


    async def spotify_audio(self, url:str):
        try:
            track_id = url.removeprefix("https://open.spotify.com/track/")[:22]
            track = self.sp_client.track(track_id)
            duration = track["duration_ms"]
            if duration==0:
                return 1

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
        except:
            return 1

    def page(self, items):
        list = []
        for track in items:
            try:
                author = ", ".join([i["name"] for i in track["track"]["artists"]])
                name = track["track"]["name"]
                title = f"{author} - {name}"
                track_url = track["track"]["external_urls"]["spotify"]
                list.append([title, track_url])
            except:
                pass

        return list


    async def spotify_playlist(self, url:str):
        id = url.removeprefix("https://open.spotify.com/playlist/")[:22]
        playlist = self.sp_client.playlist_items(id)
        total = int(playlist["total"])
        next_pages = math.ceil((total-100)/100)

        songs = []
        r = playlist["items"]
        x = self.page(r)
        for i in x:
            songs.append(i)

        for i in range(next_pages):
            playlist = self.sp_client.next(playlist)
            r = playlist["items"]
            x = self.page(r)
            for i in x: 
                songs.append(i)

        return songs


 

class SoundCloudSource:
    def __init__(self, options=None) -> None:
        self.id = None
        self.audio = None
        self.title = None
        self.duration = None
        self.options = options
        self.thumbnail = None
        self.platform = "soundcloud"

        if options == None:
            self.options = {'format': 'bestaudio'}

    async def soundcloud_audio(self, url:str):
        try:
            ytdl = youtube_dl.YoutubeDL(self.options)
            loop = asyncio.get_event_loop()
    
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            self.id = data["id"]
            self.audio = data["url"]
            self.title = data["title"]
            self.duration = data["duration"]
            self.thumbnail = data["thumbnails"][5]["url"]
            self.url = url

            if self.duration > 14400:
                return 1
        except:
            return 1

        return self


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
        self.sp_creds = spotify_credentials()
    

    async def extract_playlist(self, ctx, url):
        if url.startswith("https://www.youtube.com/playlist?"):
            playlist = await YoutubeSource().youtube_playlist(url)
            threads = []
               
            for url in playlist:
                threads.append(BetterThread(target=asyncio.run, args=(YoutubeSource().youtube_audio(url))))
                threads[-1].start()
                
            while any([thread.is_alive() for thread in threads]): await asyncio.sleep(0.1)

            for result in threads:
                if result.value != 1 and result.value.audio != None:
                    self.queue.append(result.value)

        elif url.startswith("https://open.spotify.com/playlist"):
            playlist = await SpotifySource(credentials=self.sp_creds).spotify_playlist(url)
            threads = []
            for track in playlist:
                threads.append(BetterThread(target=asyncio.run, args=(SpotifySource(credentials=self.sp_creds).spotify_audio(track[1]))))
                threads[-1].start()

                
            while any([thread.is_alive() for thread in threads]): await asyncio.sleep(0.1)

            for result in threads:
                if result.value != 1 and result.value.audio != None:
                    self.queue.append(result.value)


    async def extract_source(self, ctx, url):
        if url.startswith("https://www.youtube.com/watch?v="):
            if "&index=" in url:
                url, index = url.split("&index=")
                playlist_id = url[-30:]
                url = f"https://www.youtube.com/playlist?list=PLY-{playlist_id}"
                index = int(index)-1
                source = YoutubeSource()
                video = await source.youtube_playlist(url)
                await source.youtube_audio(video[index])

            else:        
                source = YoutubeSource()
                await source.youtube_audio(url)

            self.queue.append(source)

        elif url.startswith('https://soundcloud.com'):
            track = SoundCloudSource()
            await track.soundcloud_audio(url)
            self.queue.append(track)

        elif url.startswith("https://open.spotify.com/track/"):
            track = SpotifySource(credentials=self.sp_creds)
            await track.spotify_audio(url)
            self.queue.append(track)
            

        elif "playlist" in url:
            from time import time
            t0=time()
            await self.extract_playlist(ctx, url)
            print(time()-t0)


    async def join(self, ctx):
        if self.voice_client == None or self.voice_client.is_connected()==False:
            if self.voice_client == None:
                self.voice_client = await ctx.author.voice.channel.connect()
            else:
                self.voice_client = await ctx.author.voice.channel.connect()

            self.voice_clients[self.voice_client.guild.id] = self.voice_client


    async def play_audio(self, ctx, source: YoutubeSource|SpotifySource|SoundCloudSource):
        
        player = discord.FFmpegPCMAudio(source.audio, executable=self.ffmpeg_path,**self.opts)
        self.voice_clients[ctx.guild.id].play(player)

        await asyncio.sleep(0.25)
        if self.voice_clients[ctx.guild.id].is_playing():
            if source.platform == "youtube":
                color = 0xff0000
            elif source.platform == "spotify":
                color = 0x00a815
            elif source.platform == "soundcloud":
                color=0xff5b0d

            await message.send_embed(ctx,title=source.title,url=source.url,color=color,name="Playing now",thumbnail=source.thumbnail)
        else:
            await message.send_embed(ctx,title=f"Couldn't play track '{source.title}'",url=None, color=0xff0000,name= "Error",thumbnail=None)


    async def play_queue(self, ctx):
        if not self.voice_clients[ctx.guild.id].is_playing():
            for source in self.queue: 
                if source == 1:
                    continue
                try:
                    await self.play_audio(ctx, source)
                except:
                    await message.send_embed(ctx,title=f"Couldn't play track '{source.title}'",url=None, color=0xff0000,name= "Error", thumbnail=None)

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

        await self.extract_source(ctx, url)
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
        words = ctx.content.split(" ")
        if len(words) > 1:
            page = int(words[1])
        else:
            page = 1

        b = self.iter+(25*page)
        if b > len(self.queue):
            b = len(self.queue)

        fields = [f"{i+1}. {self.queue[i].title}" for i in range(self.iter+(25*page-25), b)]
        await message.send_embed(ctx, title=f"Queued songs page {page}", url=None, color=0xff0000, fields=fields, name="", thumbnail=None)

        
