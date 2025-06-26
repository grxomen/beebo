import discord
from discord.ext import commands
import time

class UtilsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # {(user_id, command_name): [timestamp, warned]}

    def check_command_cooldown(self, user_id: int, command_name: str, cooldown_time: int, dev_ids: list[int]) -> (bool, str):
        """
        Check cooldown for a user-command pair.
        Returns:
            (True, None) if allowed
            (False, msg) if warning should be shown
            (False, None) if ignored silently
        """
        if user_id in dev_ids:
            return True, None

        now = time.time()
        key = (user_id, command_name)
        last_entry = self.cooldowns.get(key)

        if not last_entry:
            self.cooldowns[key] = [now, False]
            return True, None

        last_used, warned = last_entry
        elapsed = now - last_used

        if elapsed >= cooldown_time:
            self.cooldowns[key] = [now, False]
            return True, None

        if not warned:
            self.cooldowns[key][1] = True
            return False, f"⏳ You're on cooldown! Try again in **{int(cooldown_time - elapsed)}s**."

        return False, None

async def setup(bot):
    await bot.add_cog(UtilsCog(bot))
