# PinPoint.py

import discord
from discord.ext import commands
from typing import Union
import json
import os
import csv
from datetime import datetime

PIN_DATA_FILE = "data/pins.json"
SUBMITTER_MAP = {
    "1": 448896936481652777,  # you
    "2": 1234744521393307678, # vinny
    "3": 587900974669103104   # lachie
}
DEV_IDS = [448896936481652777]  # you

def load_pins():
    if not os.path.exists(PIN_DATA_FILE):
        return {}
    with open(PIN_DATA_FILE, "r") as f:
        return json.load(f)

def save_pins(data):
    os.makedirs(os.path.dirname(PIN_DATA_FILE), exist_ok=True)
    with open(PIN_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class PinPoint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mark")
    async def mark(self, ctx, x: int, z: int, *, description: str):
        pins = load_pins()
        pin_id = str(max([int(k) for k in pins.keys()] + [0]) + 1)
        timestamp = datetime.utcnow().isoformat()
        submitter_id = str(ctx.author.id)
        attributed_id = str(ctx.author.id)

        pins[pin_id] = {
            "x": x,
            "z": z,
            "description": description,
            "submitter_id": submitter_id,
            "attributed_user_id": attributed_id,
            "timestamp": timestamp
        }

        save_pins(pins)
        embed = discord.Embed(title="📍 New Pin Added", color=0x462f80)
        embed.add_field(name="🧭 Coordinates", value=f"x: {x}, z: {z}", inline=False)
        embed.add_field(name="💬 Description", value=description, inline=False)
        embed.set_footer(text=f"Submitted by {ctx.author.display_name} • ID: {pin_id}")
        await ctx.send(embed=embed)

    @commands.command(name="pins")
    async def pins(self, ctx):
        pins = load_pins()
        if not pins:
            await ctx.send("📭 No pins found.")
            return

        embed = discord.Embed(title="📌 Recent Pins", color=0x462f80)
        for pid in sorted(pins, key=lambda k: int(k))[-5:]:
            p = pins[pid]
            user = self.bot.get_user(int(p["attributed_user_id"])) or f"<@{p['attributed_user_id']}>"
            embed.add_field(name=f"📍 {p['description']} (ID {pid})",
                            value=f"x: {p['x']}, z: {p['z']} — by {user}",
                            inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="pin")
    async def pin(self, ctx, pin_id: str):
        pins = load_pins()
        pin = pins.get(pin_id)
        if not pin:
            await ctx.send("❌ Pin not found.")
            return
        submitter = self.bot.get_user(SUBMITTER_MAP.get(pin["submitter_id"], 0)) or f"<@{pin['submitter_id']}>"
        attributed = self.bot.get_user(int(pin["attributed_user_id"])) or f"<@{pin['attributed_user_id']}>"
        embed = discord.Embed(title=f"📍 {pin['description']}", color=0x462f80)
        embed.add_field(name="🧭 Coordinates", value=f"x: {pin['x']}, z: {pin['z']}", inline=False)
        embed.add_field(name="👤 Submitted by", value=f"{submitter}", inline=True)
        embed.add_field(name="🙋 Attributed to", value=f"{attributed}", inline=True)
        embed.set_footer(text=f"Pin ID: {pin_id} • {pin['timestamp']}")
        await ctx.send(embed=embed)

    @commands.command(name="filterpins")
    async def filterpins(self, ctx, *, query: str):
        pins = load_pins()
        results = []

        for pid, pin in pins.items():
            if (
                query in pin["description"]
                or query in pid
                or query in pin["submitter_id"]
                or query in pin["attributed_user_id"]
            ):
                results.append((pid, pin))

        if not results:
            await ctx.send("❌ No pins matched your filter.")
            return

        embed = discord.Embed(title="🔎 Filtered Pins", color=0x462f80)
        for pid, pin in results[:10]:
            user = self.bot.get_user(int(pin["attributed_user_id"])) or f"<@{pin['attributed_user_id']}>"
            embed.add_field(name=f"{pin['description']} (ID {pid})",
                            value=f"x: {pin['x']}, z: {pin['z']} — by {user}",
                            inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="editpin")
    async def editpin(self, ctx, pin_id: str, *, new_desc: str):
        pins = load_pins()
        pin = pins.get(pin_id)
        if not pin:
            await ctx.send("❌ Pin not found.")
            return

        user_id = str(ctx.author.id)
        is_owner = pin["submitter_id"] == user_id or user_id in map(str, DEV_IDS)

        if not is_owner:
            await ctx.send("🚫 You can't edit this pin.")
            return

        pin["description"] = new_desc
        save_pins(pins)
        await ctx.send(f"✏️ Pin `{pin_id}` updated.")

    @commands.command(name="deletepin")
    async def deletepin(self, ctx, pin_id: str):
        pins = load_pins()
        pin = pins.get(pin_id)
        if not pin:
            await ctx.send("❌ Pin not found.")
            return

        user_id = str(ctx.author.id)
        is_owner = pin["submitter_id"] == user_id or user_id in map(str, DEV_IDS)

        if not is_owner:
            await ctx.send("🚫 You can't delete this pin.")
            return

        del pins[pin_id]
        save_pins(pins)
        await ctx.send(f"🗑️ Pin `{pin_id}` deleted.")

    @commands.command(name="exportpins")
    async def exportpins(self, ctx):
        pins = load_pins()
        if not pins:
            await ctx.send("📭 No pins to export.")
            return

        json_path = "/mnt/data/pin_export.json"
        csv_path = "/mnt/data/pin_export.csv"

        with open(json_path, "w") as f:
            json.dump(pins, f, indent=4)

        with open(csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ID", "X", "Z", "Description", "Submitter", "Attributed", "Timestamp"])
            for pid, pin in pins.items():
                writer.writerow([
                    pid,
                    pin["x"],
                    pin["z"],
                    pin["description"],
                    pin["submitter_id"],
                    pin["attributed_user_id"],
                    pin["timestamp"]
                ])

        await ctx.send("📦 Pins exported:", files=[
            discord.File(json_path),
            discord.File(csv_path)
        ])

async def setup(bot):
    await bot.add_cog(PinPoint(bot))
