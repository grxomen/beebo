import os
import discord
import time
import random
from discord.ext import commands, tasks
from mcstatus import JavaServer
from python_aternos import Client
from dotenv import load_dotenv
from discord.ext.commands import cooldown, BucketType

# Load .env variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ROLE_TO_TAG = os.getenv("ROLE_TO_TAG")
ATERNO_EMAIL = os.getenv("ATERNO_EMAIL")
ATERNO_PASSWORD = os.getenv("ATERNO_PASSWORD")
ANNOUNCEMENT_CHANNEL_ID = 1359974211367469147

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
last_status = "offline"
boot_time = time.time()

@bot.event
async def on_ready():
    print(f'{bot.user} reporting for duty!')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="✅ Beebo has reloaded!",
            description="We're Back <:pixelGUY:1368269152334123049>",
            color=0xb0c0ff
        )
        await channel.send(embed=embed)
    check_server_status.start()

@tasks.loop(hours=3)
async def check_server_status():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)
    server = JavaServer.lookup(SERVER_ADDRESS)

    try:
        status = server.status()
        if last_status == "offline":
            embed = discord.Embed(title="**Minecraft Server is ONLINE!**", color=0xb0c0ff)
            embed.add_field(name="Java IP", value="officialserv.aternos.me", inline=False)
            embed.add_field(name="Bedrock Port", value="64886", inline=False)
            embed.add_field(name="Console Join Code", value="eBhVrUWmUN_xVYo", inline=False)
            embed.add_field(name="Players", value=f"{status.players.online}/{status.players.max}", inline=False)

            if status.players.online > 0:
                players = ', '.join([player.name for player in status.players.sample]) if status.players.sample else "Unknown players"
                embed.add_field(name="Who's Online", value=players, inline=False)

            embed.set_footer(text="Summon the squad before Aternos falls asleep.")
            await channel.send(content=ROLE_TO_TAG, embed=embed)
            last_status = "online"
        else:
            print("Server still online. No alert sent.")
    except:
        print("Server is offline or unreachable.")
        if last_status == "online":
            embed = discord.Embed(title="**Minecraft Server is OFFLINE or SLEEPING**", color=0xff5555)
            embed.set_footer(text="Someone needs to manually start it or join to wake it up.")
            await channel.send(content="<@&1368225900486721616>", embed=embed)
        last_status = "offline"

@bot.command(aliases=["status", "serverstatus"])
async def mcstatus(ctx):
    server = JavaServer.lookup(SERVER_ADDRESS)
    try:
        status = server.status()
        embed = discord.Embed(title="**Minecraft Server Status**", color=0x00ff00)
        embed.add_field(name="Status", value="ONLINE", inline=True)
        embed.add_field(name="Players", value=f"{status.players.online}/{status.players.max}", inline=True)

        if status.players.online > 0:
            players = ', '.join([player.name for player in status.players.sample]) if status.players.sample else "Players hidden"
            embed.add_field(name="Who's Online", value=players, inline=False)

        await ctx.send(embed=embed)
    except:
        embed = discord.Embed(title="**Minecraft Server Status**", color=0xff0000)
        embed.add_field(name="Status", value="OFFLINE or Sleeping", inline=True)
        embed.set_footer(text="Reminder: Aternos servers need manual starting.")
        await ctx.send(embed=embed)


@bot.command(name="𝑩𝒆𝒆𝒃𝒐", aliases=["beebo", "ping"])
async def beebo_ping(ctx):
    start = time.perf_counter()
    msg = await ctx.send("🏓 Pinging Beebo...")
    end = time.perf_counter()
    latency_ms = (end - start) * 1000
    embed = discord.Embed(description="<:pixel_cake_blk:1368286757094949056> Did someone call for Beebo?", color=0xffefb0)
    embed.set_footer(text=f"Latency: {latency_ms:.2f} ms ({latency_ms/1000:.2f} sec)")
    await msg.edit(content=None, embed=embed)

@bot.command(aliases=["upt", "alive"])
async def uptime(ctx):
    uptime_seconds = int(time.time() - boot_time)
    minutes, seconds = divmod(uptime_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    embed = discord.Embed(
        title="🕒 Beebo Uptime",
        description=f"I've been alive for {hours}h {minutes}m {seconds}s",
        color=0xb0c0ff
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["ver", "commit"])
async def version(ctx):
    import subprocess
    try:
        commit = subprocess.check_output(["git", "log", "-1", "--pretty=format:%h - %s"]).decode().strip()
        embed = discord.Embed(
            title="📦 Beebo Version",
            description=f"`{commit}`",
            color=0xb0c0ff
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Could not retrieve version: {e}")       

@bot.command(aliases=["awake", "wakeserver"])
async def startserver(ctx):
    if 1366796508288127066 not in [role.id for role in ctx.author.roles]:
        await ctx.send("🚫 You don't have permission to use this command.")
        return

    try:
        atclient = Client()
        atclient.login(ATERNO_EMAIL, ATERNO_PASSWORD)
        servers = atclient.list_servers()

        if not servers:
            await ctx.send("No Aternos servers found for this account.")
            return

        myserver = servers[0]
        myserver.start()

        embed = discord.Embed(title="Server Startup Initiated!", color=0x00ff00)
        embed.add_field(name="Launching", value="Beebo has triggered Aternos startup.", inline=False)
        embed.set_footer(text="Give it a minute. Queue times vary.")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Failed to start server: `{str(e)}`")

@bot.command(aliases=["offping", "cacaw"])
@cooldown(1, 300, BucketType.channel)  # once every 5 minutes per channel
async def pingoffline(ctx):
    server = JavaServer.lookup(SERVER_ADDRESS)
    try:
        status = server.status()
        await ctx.send("The server is currently online — no need to ping the squad.")
    except:
        embed = discord.Embed(title="**Heads Up! The Server Seems to Be Offline or Sleeping**", color=0xff0000)
        embed.set_footer(text="Someone needs to hop in or start it manually.")
        await ctx.send(content="<@&1368225900486721616>", embed=embed)

@pingoffline.error
async def pingoffline_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = int(error.retry_after)
        minutes, seconds = divmod(retry_after, 60)
        time_left = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
        await ctx.send(f"\u23F3 That command is on cooldown. Try again in `{time_left}`.")

@bot.command()
async def cakecheck(ctx):
    cake_id = 546650815297880066
    cake_user = ctx.guild.get_member(cake_id)

    if not cake_user:
        description = "Can't find Cake...probably lost in notifications again."
    else:
        status = str(cake_user.status)
        if status == "online":
            description = "🟢 Cake is online...maybe watching, maybe ignoring."
        elif status == "idle":
            description = "🌙 Cake is idle. She's drifting through frosting fog."
        elif status == "dnd":
            description = "⛔ Do not disturb: probably battling her DM pile."
        else:
            description = "⚫ Cake is offline...or is she?"

    unread_messages = f"{random.randint(3000, 9000):,}"
    embed = discord.Embed(
        title="<:pixel_cake:1368264542064345108> Cake Status Scan",
        description=description,
        color=0xffaad4
    )
    embed.set_thumbnail(url="attachment://pixel_cake.png")
    embed.set_footer(text="Unread messages: 8,042. DMs: yes, but no.")
    file = discord.File("/root/beebo/assets/pixel_cake.png", filename="pixel_cake.png")
    await ctx.send(file=file, embed=embed)

def get_presence_description(member, lines):
    if not member:
        return lines["not_found"]
    status = str(member.status)
    return lines.get(status, lines["default"])

@bot.command(aliases=["vivera", "vscan"])
async def viveracheck(ctx):
    member = ctx.guild.get_member(533680872747171841)
    desc = get_presence_description(member, {
        "online": "🟢 Vivera is vibing online. Possibly watching everything in silence.",
        "idle": "🌙 Vivera is idle... probably lost in deep lore.",
        "dnd": "⛔ Do not disturb. Vivera’s in another dimension.",
        "offline": "⚫ Vivera is offline... or just too cool to be seen.",
        "not_found": "Couldn’t locate Vivera. Too ethereal.",
        "default": "Vivera exists in a state beyond presence."
    })
    embed = discord.Embed(title="✨ Vivera Status", description=desc, color=0xd8b3ff)
    await ctx.send(embed=embed)

@bot.command(aliases=["jenna", "jscan", "statsqueen"])
async def jennacheck(ctx):
    member = ctx.guild.get_member(715950635282858094)
    desc = get_presence_description(member, {
        "online": "🟢 Jenna is online and probably checking five dashboards.",
        "idle": "🌙 Jenna is idle. Give her a stat to monitor.",
        "dnd": "⛔ Jenna is deep in analytics mode.",
        "offline": "⚫ Jenna is offline. Stats are on their own now.",
        "not_found": "Can’t find Jenna. Maybe she's optimizing the guild.",
        "default": "Jenna is in stealth analyst mode."
    })
    embed = discord.Embed(title="📊 Jenna Scan", description=desc, color=0xffeaa7)
    await ctx.send(embed=embed)

@bot.command(aliases=["toast", "toastlord"])
async def toastcheck(ctx):
    member = ctx.guild.get_member(858462569043722271)
    desc = get_presence_description(member, {
        "online": "🟢 Toast is here — and Minecraft trembles.",
        "idle": "🌙 Toast is idle. Possibly brewing potions.",
        "dnd": "⛔ Toast is busy defending the realm.",
        "offline": "⚫ Toast is offline. The chunk has unloaded.",
        "not_found": "Toast is nowhere to be found. Server lag?",
        "default": "Toast is in ghost mode."
    })
    embed = discord.Embed(title="🔥 Toast Tracker", description=desc, color=0xffc300)
    await ctx.send(embed=embed)

@bot.command(aliases=["asiasen", "asiapower"])
async def asiasencheck(ctx):
    member = ctx.guild.get_member(568577192682848267)
    desc = get_presence_description(member, {
        "online": "🟢 Asiasen is online. Eyes sharp, moves sharper.",
        "idle": "🌙 Asiasen is idle. Awaiting the next call.",
        "dnd": "⛔ Do not disturb. Probably doing boss things.",
        "offline": "⚫ Asiasen is offline. Power-saving mode engaged.",
        "not_found": "Asiasen is missing from the grid.",
        "default": "Asiasen is operating from the shadows."
    })
    embed = discord.Embed(title="💼 Asiasen Ops Check", description=desc, color=0x7ed6df)
    await ctx.send(embed=embed)

@bot.command(aliases=["gooby", "sus", "loud"])
async def goobycheck(ctx):
    member = ctx.guild.get_member(883446198579634177)
    desc = get_presence_description(member, {
        "online": "🟢 Gooby is online. Probably yelling SUS at someone.",
        "idle": "🌙 Gooby is idle. The calm before the scream.",
        "dnd": "⛔ Do not disturb. Emergency meeting in progress.",
        "offline": "⚫ Gooby is offline. Mic cooldown active.",
        "not_found": "Gooby couldn’t be found. Sabotage?",
        "default": "Gooby is venting through the shadows."
    })
    embed = discord.Embed(title="🔊 Gooby Voice Check", description=desc, color=0xf8a5c2)
    await ctx.send(embed=embed)

@bot.command(aliases=["meow", "simpstar", "brainfan"])
async def meowstarcheck(ctx):
    member = ctx.guild.get_member(1148630927686254602)
    desc = get_presence_description(member, {
        "online": "🟢 Meowstar is online — probably admiring your Among Us genius.",
        "idle": "🌙 Meowstar is idle. Thinking about how big-brained you are.",
        "dnd": "⛔ Do not disturb. Braincell charging in progress.",
        "offline": "⚫ Meowstar is offline... maybe writing a fanfic about your galaxy brain.",
        "not_found": "Meowstar not detected. Has he stopped praising you?",
        "default": "Meowstar is AFK but spiritually simping."
    })
    embed = discord.Embed(title="🌟 Meowstar Worship Log", description=desc, color=0xa29bfe)
    await ctx.send(embed=embed)


@bot.command(aliases=["talk", "broadcast", "bcast"])
async def say(ctx, *, message: str):
    if 1366796508288127066 not in [role.id for role in ctx.author.roles]:
        await ctx.send("🚫 You don't have permission to use this command.")
        return

    embed = discord.Embed(description=message, color=0xb0c0ff)
    channel = bot.get_channel(1359974211367469147)
    await channel.send(content="<@&1368225900486721616>", embed=embed)

@bot.command(aliases=["rle"])
async def reloadenv(ctx):
    if ctx.author.id not in [546650815297880066, 448896936481652777]:
        await ctx.send("🚫 You don't have permission to reload the environment.")
        return

    load_dotenv(override=True)
    embed = discord.Embed(
        title="Environment Reloaded ✅",
        description="Configuration has been reloaded from .env. Beebo’s got the latest settings <:pixel_cake:1368264542064345108>.",
        color=0xb0c0ff
    )
    await ctx.send(embed=embed)

@bot.command()
async def reload(ctx):
    if ctx.author.id != 448896936481652777:
        await ctx.send("🚫 You don't have permission to perform a full reload.")
        return

    import subprocess, asyncio
    embed = discord.Embed(
        title="Restarting Beebo 🔁",
        description="Pulling latest code and restarting. Back in a sec...<:pixelGUY:1368269152334123049>",
        color=0xb0c0ff
    )
    await ctx.send(embed=embed)
    await asyncio.sleep(1)
    try:
        subprocess.run(["/root/beebo/reload_beebo.sh"], check=True)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"❌ Reload failed: {e}")


@bot.command(aliases=["bhelp", "beebohelp"])
async def help(ctx):
    embed = discord.Embed(title="Beebo Command List", color=0xb0c0ff)
    embed.add_field(name="!mcstatus", value="Check if the Minecraft server is online and who's on.", inline=False)
    embed.add_field(name="!pingoffline", value="If the server is offline, alert the squad to start it.", inline=False)
    embed.add_field(name="!startserver", value="Attempts to start the server using Aternos (restricted to ☁️ 𝓥𝓲𝓼𝓬𝓵𝓸𝓾𝓭 role).", inline=False)
    embed.add_field(name="!say", value="Send a custom message with an embed and ping MCSquad (restricted).", inline=False)
    embed.add_field(name="!reloadenv / !rle", value="Reloads the environment settings <:pixel_cake:1368264542064345108>. Restricted.", inline=False)
    embed.add_field(name="!reload", value="Pulls latest code and restarts Beebo <:pixelGUY:1368269152334123049>. Restricted.", inline=False)
    embed.add_field(name="!help", value="You're looking at it.", inline=False)
    embed.set_footer(text="Bot made for keeping the realm alive and the squad notified.")
    await ctx.send(embed=embed)

bot.run(TOKEN)
