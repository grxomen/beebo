import os
import discord
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
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
last_status = "offline"

@bot.event
async def on_ready():
    print(f'{bot.user} reporting for duty!')
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

@bot.command()
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

@bot.command()
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

@bot.command()
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

    import subprocess
    try:
        subprocess.run(["/root/beebo/reload_beebo.sh"], check=True)
        embed = discord.Embed(
            title="Restarting Beebo 🔁",
            description="Pulling latest code and restarting. Back in a sec...<:pixelGUY:1368269152334123049>",
            color=0xb0c0ff
        )
        await ctx.send(embed=embed)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"❌ Reload failed: {e}")

@bot.command()
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
