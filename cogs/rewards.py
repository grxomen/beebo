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
REWARD_HISTORY_FILE = "data/reward_history.json"
DEV_USER_ID = [448896936481652777, 858462569043722271]
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

class ExtendedRewardsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unlinkmc")
    async def unlinkmc(self, ctx):
        links = load_json(LINK_FILE)
        user_id = str(ctx.author.id)
        if user_id in links:
            del links[user_id]
            save_json(LINK_FILE, links)
            await ctx.send("❎ Your Minecraft link has been removed.")
        else:
            await ctx.send("⚠️ You don't have a Minecraft account linked.")

    @commands.command(name="rewardhistory")
    async def rewardhistory(self, ctx):
        history = load_json(REWARD_HISTORY_FILE)
        user_id = str(ctx.author.id)
        entries = history.get(user_id, [])
        if not entries:
            await ctx.send("📭 No reward history found.")
            return

        embed = discord.Embed(title="🎁 Reward History", color=0x462f80)
        for entry in entries[-5:]:
            embed.add_field(name=entry["reward"], value=f"<t:{entry['timestamp']}:R>", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="checkuuid")
    async def checkuuid(self, ctx, mc_username: str):
        url = f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
        response = requests.get(url)
        if response.status_code != 200:
            await ctx.send(f"❌ No player found with name `{mc_username}`.")
            return

        data = response.json()
        formatted_uuid = f"{data['id'][:8]}-{data['id'][8:12]}-{data['id'][12:16]}-{data['id'][16:20]}-{data['id'][20:]}"
        await ctx.send(f"🆔 UUID for `{mc_username}` is `{formatted_uuid}`.")

    @commands.command(name="pooladd")
    @commands.has_permissions(administrator=True)
    async def pooladd(self, ctx, amount: float):
        pool = load_json(POOL_FILE)
        pool["credits"] = pool.get("credits", 0.0) + amount
        save_json(POOL_FILE, pool)
        await ctx.send(f"💸 Added **{amount:.2f}** credits. New pool balance: **{pool['credits']:.2f}**")

    @commands.command(name="linkstatus", aliases=["mclink", "linked"])
    async def link_status(self, ctx):
        """Check your current linked Minecraft username and UUID."""
        links = load_json(LINK_FILE)
        user_data = links.get(str(ctx.author.id))
    
        if not user_data:
            await ctx.send("🔍 You haven't linked your Minecraft account yet. Use `!linkmc <username>` to do so.")
            return
    
        username = user_data.get("username", "Unknown")
        uuid = user_data.get("uuid", "N/A")
    
        embed = discord.Embed(
            title="🔗 Minecraft Link Status",
            description=f"You are linked to **{username}**",
            color=color=0x3d5e8e
        )
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.set_footer(text="Use !unlinkmc to disconnect if needed.")
        await ctx.send(embed=embed)


    @commands.command(name="devlinkmc")
    async def devlinkmc(self, ctx, member: discord.Member, mc_username: str):
        if ctx.author.id not in DEV_USER_ID:
            await ctx.send("🚫 You don’t have permission to use this.")
            return

        url = f"https://api.mojang.com/users/profiles/minecraft/{mc_username}"
        response = requests.get(url)
        if response.status_code != 200:
            await ctx.send(f"❌ Minecraft user `{mc_username}` not found.")
            return

        raw = response.json()["id"]
        formatted_uuid = f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
        links = load_json(LINK_FILE)
        links[str(member.id)] = {
            "username": mc_username,
            "uuid": raw
        }
        save_json(LINK_FILE, links)

        await ctx.send(f"🔧 Linked **{member.display_name}** to **{mc_username}**.")
        log_channel = self.bot.get_channel(MC_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="🔐 Dev Linked MC", color=discord.Color.gold())
            embed.add_field(name="Dev", value=ctx.author.mention, inline=False)
            embed.add_field(name="Target User", value=member.mention, inline=False)
            embed.add_field(name="MC Username", value=mc_username, inline=False)
            embed.add_field(name="UUID", value=formatted_uuid, inline=False)
            embed.set_footer(text="Manual link action")
            await log_channel.send(embed=embed)

    # -- Pool Credits Check --
    @commands.command(name="pool", aliases=["creditpool", "donorpool"])
    async def credit_pool(self, ctx):
        pool = load_json(POOL_FILE)
        balance = pool.get("credits", 0.0)
        await ctx.send(f"💰 Current server credit pool balance: **{balance:.2f}** credits.")

async def setup(bot):
    await bot.add_cog(RewardsCog(bot))
