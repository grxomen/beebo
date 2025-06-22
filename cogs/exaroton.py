import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import json
import time
import os
from playwright.async_api import async_playwright
from discord.ext.commands import Cooldown, BucketType, CommandOnCooldown


DATA_FILE = "data/exaroton_data.json"
POOL_FILE = "data/exaroton_pool.json"
donor_role_id = 1386101967297843270
EXAROTON_TRUSTED = [448896936481652777, 546650815297880066, 858462569043722271]
CHECK_INTERVAL_HOURS = 3

def load_data(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_data(filename, data):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

class ServerControlView(discord.ui.View):
    def __init__(self, credit_code):
        super().__init__()
        self.add_item(discord.ui.Button(
            label="💸 Donate Credits",
            url=f"https://exaroton.com/credits/#{credit_code}",
            style=discord.ButtonStyle.link
        ))
        self.add_item(discord.ui.Button(
        label="🛠️ Adjust RAM (Coming Soon)",
        style=discord.ButtonStyle.gray,
        disabled=True
    ))

def get_topup_embed(dev_footer=None):
    embed = discord.Embed(
        title="💳 Top Up Server Credits",
        description="Help keep the server running! Use the button below to donate credits.",
        color=0x462f80
    )
    if dev_footer:
        embed.set_footer(text=dev_footer)
    else:
        embed.set_footer(text="Donations go directly into server uptime.")
    return embed


DONORBOARD_COOLDOWN_SECONDS = 300  # 5 minutes
last_donorboard_time = 0
DEV_USER_IDS = [448896936481652777, 546650815297880066, 858462569043722271]

class DonateButton(discord.ui.View):
    def __init__(self, pool_code):
        super().__init__()
        if pool_code:
            self.add_item(discord.ui.Button(
                label="💸 Donate Credits",
                url=f"https://exaroton.com/credits/#{pool_code}",
                style=discord.ButtonStyle.link
            ))

    
class ExarotonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.credit_balance = load_data(DATA_FILE).get("balance", 0.0)
        self.credit_pool_code = load_data(POOL_FILE).get("pool", "")
        self.server_address = os.getenv("SERVER_ADDRESS")
        self.channel_id = int(os.getenv("CHANNEL_ID"))
        self.role_to_tag = os.getenv("ROLE_TO_TAG")
        self.last_status = "offline"
        self.check_server_status.start()

    @tasks.loop(hours=CHECK_INTERVAL_HOURS)
    async def check_server_status(self):
        channel = self.bot.get_channel(self.channel_id)
        server = JavaServer.lookup(self.server_address)

        try:
            status = server.status()

            # ─── Server Just Came Online ─────────────────────────
            if self.last_status == "offline":
                embed = discord.Embed(title="**Minecraft Server is ONLINE!**", color=0x462f80)
                embed.add_field(name="Java IP", value=self.server_address, inline=False)
                embed.add_field(name="Players", value=f"{status.players.online}/{status.players.max}", inline=False)

                if status.players.online > 0:
                    players = ', '.join([p.name for p in status.players.sample]) if status.players.sample else "Unknown players"
                    embed.add_field(name="Who's Online", value=players, inline=False)

                embed.set_footer(text="Summon the squad before Exaroton falls asleep.")
                await channel.send(content=self.role_to_tag, embed=embed)
                self.last_status = "online"

                # ─── Burn Warning Embed ─────────────────────────────
                if self.credit_balance <= 1030.8:
                    try:
                        warn_embed = discord.Embed(
                            title="⚠️ Low Server Credits!",
                            description=f"Current balance: **{self.credit_balance} credits**\nTop up soon to avoid downtime.",
                            color=0xffaa00
                        )
                        hours_left = round(self.credit_balance / 10, 1)
                        warn_embed.add_field(name="Burn Estimate", value=f"~{hours_left}h left @ 10GB RAM", inline=False)
                        warn_embed.set_footer(text="Use !topup to donate credits.")
                        view = ServerControlView(self.credit_pool_code)
                        await channel.send(embed=warn_embed, view=view)
                    except Exception as e:
                        print(f"[⚠️ Burn Warning Error] {e}")

            else:
                print("[Status Check] Server still online, no alert sent.")

        except Exception as e:
            print(f"[🔻 Server Down Check] {e}")
            if self.last_status == "online":
                embed = discord.Embed(
                    title="**Minecraft Server is OFFLINE or SLEEPING**",
                    color=0xff5555
                )
                embed.set_footer(text="Someone needs to manually start it or join to wake it up.")
                await channel.send(content=self.role_to_tag, embed=embed)
            self.last_status = "offline"


    @commands.command()
    @commands.cooldown(1, 20, BucketType.user)
    @commands.is_owner()
    async def setcredits(self, ctx, amount: float, member: discord.Member = None):
        user = member or ctx.author
        user_id = str(user.id)
    
        # Update credit balance (you can customize whether this affects server logic or is just for stats)
        self.credit_balance = float(amount) if user == ctx.author else self.credit_balance
    
        # Update personal donation record
        donations = load_data("data/exaroton_donations.json")
        donations[user_id] = donations.get(user_id, 0) + amount
        save_data("data/exaroton_donations.json", donations)
    
        await ctx.send(f"✅ Set **{amount} credits** for {user.mention}.")
    
        # Optionally: show leaderboard position
        leaderboard = sorted(donations.items(), key=lambda x: x[1], reverse=True)
        position = [uid for uid, _ in leaderboard].index(user_id) + 1
        await ctx.send(f"🏆 {user.display_name} is now **#{position}** on the donor leaderboard!")


    @commands.command(name="dboard", aliases=["donors"])
    async def donorboard(self, ctx, top: int = 5):
        global last_donorboard_time
        now = time.time()
        is_dev = ctx.author.id in DEV_USER_IDS
    
        if not is_dev and now - last_donorboard_time < DONORBOARD_COOLDOWN_SECONDS:
            remaining = int(DONORBOARD_COOLDOWN_SECONDS - (now - last_donorboard_time))
            embed = discord.Embed(
                title="⏳ Slow down there!",
                description=f"`!donorboard` is on cooldown for **{remaining}** more seconds.",
                color=0xffaa00
            )
            embed.set_footer(text="Try again later.")
            await ctx.send(embed=embed)
            return
    
        last_donorboard_time = now
    
        donations = load_data("data/exaroton_donations.json")
        if not donations:
            await ctx.send("📭 No donation data yet!")
            return
    
        leaderboard = sorted(donations.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(
            title="🏆 Top Server Donors",
            description="Most generous credit contributors ❤️",
            color=0x462f80
        )
    
        for i, (user_id, total) in enumerate(leaderboard[:top], start=1):
            user = self.bot.get_user(int(user_id)) or f"<@{user_id}>"
            name = user.display_name if hasattr(user, 'display_name') else str(user)
            embed.add_field(
                name=f"{i}. {name}",
                value=f"💰 {total:.2f} credits",
                inline=False
            )
    
        if is_dev:
            embed.set_footer(text="<:pixelGUY:1368269152334123049> Dev bypass")
    
        view = DonateButton(self.credit_pool_code)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="credits", aliases=["creds"])
    async def credits(self, ctx):
        await ctx.send(f"💰 Current credit balance: **{self.credit_balance}** credits.")

    @commands.command()
    async def burn(self, ctx, hours: float = 1, ram: int = 10):
        rate_per_gb_hour = 1.0  # Exaroton's current rate
        session_burn = round(rate_per_gb_hour * ram * hours, 2)
        daily_burn = round(rate_per_gb_hour * ram * 24, 2)
        weekly_burn = round(daily_burn * 7, 2)
    
        # Estimate runtime left based on current credit balance
        if ram > 0:
            hours_left = self.credit_balance / (rate_per_gb_hour * ram)
            days_left = hours_left / 24
            lifespan = f"<:beebo:1383282292478312519> Estimated uptime left: **{hours_left:.1f}h** (~{days_left:.1f} days)"
        else:
            lifespan = "⚠️ Invalid RAM config for burn estimate."
    
        embed = discord.Embed(
            title="🔥 Exaroton Burn Estimate",
            description=f"Using **{ram}GB RAM**...",
            color=0x462f80
        )
        embed.add_field(name=f"Per {hours}h session", value=f"💸 **{session_burn} credits**", inline=False)
        embed.add_field(name="Per 24h/day (1 day)", value=f"🕒 **{daily_burn} credits**", inline=False)
        embed.add_field(name="Per 7d/week", value=f"📅 **{weekly_burn} credits**", inline=False)
        embed.add_field(name="Lifespan at current balance", value=lifespan, inline=False)
        embed.set_footer(text="Estimates assume 1 credit/GB/hour.")
    
        await ctx.send(embed=embed)


    @commands.command()
    @commands.is_owner()
    async def setpool(self, ctx, pool_code: str):
        self.credit_pool_code = pool_code.strip("#")
        save_data(POOL_FILE, {"pool": self.credit_pool_code})
        await ctx.send("✅ Credit pool link saved.")

    @commands.command()
    @commands.cooldown(2, 60, BucketType.guild)
    async def topup(self, ctx):
        user_id = ctx.author.id
        code = self.credit_pool_code or load_data(POOL_FILE).get("pool")
        if not code:
            await ctx.send("❌ No credit pool link set.")
            return

        # ─── Dev Footers 
        if user_id == 546650815297880066:
            embed = get_topup_embed("<:pixel_cake:1368264542064345108> Dev bypass")
        elif user_id == 858462569043722271:
            embed = get_topup_embed("<:pixel_toast:1386118938714177649> Dev bypass")
        else:
            # ─── Donor Role Check 
            if donor_role_id not in [role.id for role in ctx.author.roles]:
                await ctx.send("🚫 You don't have permission to access the donation panel.")
                return
            embed = get_topup_embed()

        view = ServerControlView(code)
        await ctx.send(embed=embed, view=view)


    @commands.command()
    async def donate(self, ctx):
        if ctx.author.id not in DEV_USER_IDS:
            bucket = commands.CooldownMapping.from_cooldown(1, 300, BucketType.guild).get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                raise commands.CommandOnCooldown(bucket, retry_after)

        if donor_role_id not in [role.id for role in ctx.author.roles]:
            await ctx.send("🚫 You don't have permission to access the donation panel.")
            return

        code = self.credit_pool_code or load_data(POOL_FILE).get("pool")
        if not code:
            await ctx.send("❌ No credit pool link set.")
            return

        embed = discord.Embed(
            title="<:pixel_toast:1386118938714177649> 💸 Donate Server Credits",
            description="Thank you for supporting the server! Use the button below to add credits directly.",
            color=0x462f80
        )
        embed.set_footer(text="Credits go into uptime & more RAM for all of us 😌")
        view = ServerControlView(code)
        await ctx.send(embed=embed, view=view)


    # ⛔ Cooldown error handler
    @donate.error
    async def donate_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Slow down, donation demon! Cooldown: {error.retry_after:.1f}s.")

    @commands.command(name="help_exaroton", aliases=["exahelp"])
    async def help_exaroton(self, ctx):
        if ctx.author.id not in EXAROTON_TRUSTED:
            await ctx.send("🚫 You’re not allowed to view this command list.")
            return

        embed = discord.Embed(
            title="📦 Exaroton Commands",
            description="Commands for managing and supporting the Termite server.",
            color=0x462f80
        )

        embed.add_field(
            name="💰 Credit Management",
            value="`!credits` — View credit balance\n"
                "`!setcredits <amount>` — Set balance (owner only)",
            inline=False
        )

        embed.add_field(
            name="🔥 Burn Estimate",
            value="`!burn <hours> <ram>` — Estimate burn cost for server usage (e.g. `!burn 3 10`)",
            inline=False
        )

        embed.add_field(
            name="💸 Credit Pool",
            value="`!setpool <code>` — Save donation pool code (owner only)\n"
                "`!topup` — Send button to donate credits",
            inline=False
        )

        embed.add_field(
            name="🔔 Status Pings",
            value="Server alerts for online/offline run every 3 hours.\nNo command needed.",
            inline=False
        )

        embed.set_footer(text="Only trusted users can see this.")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ExarotonCog(bot))
