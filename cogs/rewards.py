
import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "data/playtime_rewards.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class PlaytimeRewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_playtime.start()

    def cog_unload(self):
        self.check_playtime.cancel()

    @tasks.loop(minutes=5)
    async def check_playtime(self):
        # Placeholder: simulate Minecraft usernames currently online
        online_players = ["Vinny", "Lachie", "Toast"]
        now = datetime.utcnow()

        data = load_data()
        for player in online_players:
            if player not in data:
                data[player] = {
                    "total_minutes": 0,
                    "last_seen": now.isoformat()
                }
            else:
                last_seen = datetime.fromisoformat(data[player]["last_seen"])
                elapsed = int((now - last_seen).total_seconds() / 60)
                data[player]["total_minutes"] += elapsed
                data[player]["last_seen"] = now.isoformat()

        save_data(data)

    @commands.command(name="playtime")
    async def playtime(self, ctx, player_name: str = None):
        """Check your or another player's playtime."""
        data = load_data()
        player_name = player_name or ctx.author.display_name
        stats = data.get(player_name)

        if not stats:
            await ctx.send(f"⏳ No playtime tracked yet for `{player_name}`.")
            return

        total = stats["total_minutes"]
        hours = total // 60
        minutes = total % 60
        await ctx.send(f"🕹️ `{player_name}` has played for **{hours}h {minutes}m**.")

    @commands.command(name="topplaytime")
    async def topplaytime(self, ctx):
        """Show top 5 players by total playtime."""
        data = load_data()
        if not data:
            await ctx.send("🏜️ No playtime data available yet.")
            return

        top = sorted(data.items(), key=lambda x: x[1]["total_minutes"], reverse=True)[:5]
        embed = discord.Embed(title="🏆 Top Playtime", color=0x462f80)
        for i, (name, stats) in enumerate(top, start=1):
            total = stats["total_minutes"]
            hours = total // 60
            minutes = total % 60
            embed.add_field(name=f"#{i}: {name}", value=f"{hours}h {minutes}m", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PlaytimeRewards(bot))
