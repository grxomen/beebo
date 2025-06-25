import discord
from discord.ext import commands, tasks
import json
import time
import os
from datetime import datetime, timedelta
import requests

LINK_FILE = "data/mc_links.json"
TIME_FILE = "data/mc_time.json"
POOL_FILE = "data/credit_pool.json"
PLAYTIME_FILE = "data/playtime_rewards.json"
DEV_USER_ID = [448896936481652777, 858462569043722271]  # Replace with your own dev ID(s)
COOLDOWN_SECONDS = 60
cooldowns = {}
MC_LOG_CHANNEL_ID = 1387232069205233824

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class RewardsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_playtime.start()

    def cog_unload(self):
        self.check_playtime.cancel()

    # -- UUID Linking --
    @commands.command(name="linkmc", aliases=["uuidlink", "setuuid"])
    async def linkmc(self, ctx, mc_username: str):
        user_id = ctx.author.id
        now = time.time()

        # Cooldown check
        if user_id not in DEV_USER_ID:
            last_time = cooldowns.get(user_id, 0)
            if now - last_time < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - (now - last_time))
                embed = discord.Embed(
                    title="⏳ Slow down!",
                    description=f"You're on cooldown. Try again in **{remaining}** seconds.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Only devs can bypass this.")
                await ctx.send(embed=embed)
                return
            cooldowns[user_id] = now  # Update cooldown timestamp

        # UUID fetch
        url = f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            uuid = data["id"]
            formatted_uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

            links = load_json(LINK_FILE)
            links[str(user_id)] = {
                "username": mc_username,
                "uuid": uuid
            }
            save_json(LINK_FILE, links)

            await ctx.send(f"🔗 Successfully linked your account to **{mc_username}**.")

            # Logging
            log_channel = self.bot.get_channel(MC_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="📝 Minecraft UUID Linked",
                    color=discord.Color.blurple()
                )
                embed.add_field(name="User", value=f"{ctx.author} ({ctx.author.mention})", inline=False)
                embed.add_field(name="User ID", value=f"{ctx.author.id}", inline=True)
                embed.add_field(name="Minecraft Username", value=f"{mc_username}", inline=True)
                embed.add_field(name="UUID", value=f"`{formatted_uuid}`", inline=False)
                embed.set_footer(text=f"Submitted in #{ctx.channel}", icon_url=ctx.author.display_avatar.url)
                embed.timestamp = datetime.utcnow()
                await log_channel.send(embed=embed)
        else:
            await ctx.send(f"❌ Could not find Minecraft user `{mc_username}`. Please double-check spelling.")



    # -- Simulated Playtime Tracker --
    @tasks.loop(minutes=5)
    async def check_playtime(self):
        online_players = ["Vinny", "Lachie", "Toast"]  # Replace with real data pull when Exaroton key is in
        now = datetime.utcnow()

        data = load_json(PLAYTIME_FILE)
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

        save_json(PLAYTIME_FILE, data)

    @commands.command(name="playtime", aliases=["mctime", "timeplayed"])
    async def playtime(self, ctx, player_name: str = None):
        data = load_json(PLAYTIME_FILE)
        player_name = player_name or ctx.author.display_name
        stats = data.get(player_name)

        if not stats:
            await ctx.send(f"⏳ No playtime tracked yet for `{player_name}`.")
            return

        total = stats["total_minutes"]
        hours = total // 60
        minutes = total % 60
        await ctx.send(f"🕹️ `{player_name}` has played for **{hours}h {minutes}m**.")

    @commands.command(name="topplaytime", aliases=["leaderboard", "tophours"])
    async def topplaytime(self, ctx):
        data = load_json(PLAYTIME_FILE)
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

    # -- Pool Credits Check --
    @commands.command(name="pool", aliases=["creditpool", "donorpool"])
    async def credit_pool(self, ctx):
        pool = load_json(POOL_FILE)
        balance = pool.get("credits", 0.0)
        await ctx.send(f"💰 Current server credit pool balance: **{balance:.2f}** credits.")

async def setup(bot):
    await bot.add_cog(RewardsCog(bot))
