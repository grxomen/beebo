import discord
from discord.ext import commands, tasks
from mcstatus import MinecraftServer

TOKEN = "YOUR_DISCORD_BOT_TOKEN"
SERVER_ADDRESS = "yourserver.aternos.me"
CHANNEL_ID = 1359910666722345211  # Replace with your Discord channel ID

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

last_status = "offline"

@bot.event
async def on_ready():
    print(f'{bot.user} reporting for duty!')
    check_server_status.start()

@tasks.loop(hours=3)
async def check_server_status():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)
    server = MinecraftServer.lookup(SERVER_ADDRESS)
    try:
        status = server.status()
        if last_status == "offline":
            embed = discord.Embed(title="**Minecraft Server is ONLINE!**", color=0x00ff00)
            embed.add_field(name="Address", value=SERVER_ADDRESS, inline=False)
            embed.add_field(name="Players", value=f"{status.players.online}/{status.players.max}", inline=False)
            if status.players.online > 0:
                players = ', '.join([player.name for player in status.players.sample]) if status.players.sample else "Unknown players"
                embed.add_field(name="Who's Online", value=players, inline=False)
            embed.set_footer(text="Summon the squad before Aternos falls asleep.")
            await channel.send(embed=embed)
            last_status = "online"
        else:
            print("Already online. Staying quiet.")
    except:
        print("Server offline or unreachable.")
        last_status = "offline"

@bot.command()
async def mcstatus(ctx):
    server = MinecraftServer.lookup(SERVER_ADDRESS)
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

bot.run(TOKEN)