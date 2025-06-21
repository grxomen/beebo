import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import json
import os
from playwright.async_api import async_playwright

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
            if self.last_status == "offline":
                embed = discord.Embed(title="**Minecraft Server is ONLINE!**", color=0x462f80)
                embed.add_field(name="Java IP", value=self.server_address, inline=False)
                embed.add_field(name="Bedrock Port", value="64886", inline=False)
                embed.add_field(name="Players", value=f"{status.players.online}/{status.players.max}", inline=False)
                if status.players.online > 0:
                    players = ', '.join([p.name for p in status.players.sample]) if status.players.sample else "Unknown players"
                    embed.add_field(name="Who's Online", value=players, inline=False)
                embed.set_footer(text="Summon the squad before Exaroton falls asleep.")
                await channel.send(content=self.role_to_tag, embed=embed)
                self.last_status = "online"
            else:
                print("Server still online. No alert sent.")
        except:
            print("Server is offline or unreachable.")
            if self.last_status == "online":
                embed = discord.Embed(title="**Minecraft Server is OFFLINE or SLEEPING**", color=0xff5555)
                embed.set_footer(text="Someone needs to manually start it or join to wake it up.")
                await channel.send(content=self.role_to_tag, embed=embed)
            self.last_status = "offline"

    @commands.command()
    @commands.is_owner()
    async def setcredits(self, ctx, amount: float):
        self.credit_balance = float(amount)
        save_data(DATA_FILE, {"balance": self.credit_balance})
        await ctx.send(f"✅ Credit balance set to **{amount}** credits.")

    @commands.command(name="credits", aliases=["creds"])
    async def credits(self, ctx):
        await ctx.send(f"💰 Current credit balance: **{self.credit_balance}** credits.")

    @commands.command()
    async def burn(self, ctx, hours: float = 1, ram: int = 10):
        rate = ram
        estimated = rate * hours
        await ctx.send(f"🔥 Estimated burn for **{hours}h** at **{ram}GB RAM**: **{estimated} credits**")

    @commands.command()
    @commands.is_owner()
    async def setpool(self, ctx, pool_code: str):
        self.credit_pool_code = pool_code.strip("#")
        save_data(POOL_FILE, {"pool": self.credit_pool_code})
        await ctx.send("✅ Credit pool link saved.")

    @commands.command()
    async def topup(self, ctx):
        if donor_role_id not in [role.id for role in ctx.author.roles]:
            await ctx.send("🚫 You don't have permission to access the donation panel.")
        code = self.credit_pool_code or load_data(POOL_FILE).get("pool")
        if not code:
            await ctx.send("❌ No credit pool link set.")
            return

        embed = discord.Embed(
            title="💳 Top Up Server Credits",
            description="Help keep the server running! Use the button below to donate credits.",
            color=0x462f80
        )
        embed.set_footer(text="Donations go directly into server uptime.")
        view = ServerControlView(code)
        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def donate(self, ctx):
        """Show donation embed if user has the proper role."""
        if donor_role_id not in [role.id for role in ctx.author.roles]:
            await ctx.send("🚫 You don't have permission to access the donation panel.")
            return
    
        code = self.credit_pool_code or load_data(POOL_FILE).get("pool")
        if not code:
            await ctx.send("❌ No credit pool link set.")
            return
    
        embed = discord.Embed(
            title="💸 Donate Server Credits",
            description="Thank you for supporting the server! Use the button below to add credits directly.",
            color=0x462f80
        )
        embed.set_footer(text="Credits go into uptime & more RAM for all of us 😌")
        view = ServerControlView(code)
        await ctx.send(embed=embed, view=view)

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
