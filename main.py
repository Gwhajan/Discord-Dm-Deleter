
import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os
import time


logging.getLogger("discord.http").setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO)

chotu = commands.Bot(command_prefix="chotu", self_bot=True, intents=discord.Intents.all())

async def prompt_user(prompt):
    print(prompt, end='', flush=True)
    return await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

def format_seconds(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        return f"{seconds//3600}h {(seconds%3600)//60}m {seconds%60}s"

@chotu.event
async def on_ready():
    print(f"Logged in as {chotu.user}")

    user_id = (await prompt_user("Enter the User ID of the person to clear DMs with: ")).strip()

    try:
        dm = None
        for channel in chotu.private_channels:
            if isinstance(channel, discord.DMChannel) and channel.recipient and channel.recipient.id == int(user_id):
                dm = channel
                break

        if dm is None:
            print("No existing DM found with that user. Send them a message first.")
            return

        print(f"Estimating messages to delete in DM with {dm.recipient}...")

        min_delay = 0.5
        max_delay = 15
        delay = min_delay
        delay_step = 0.5
        success_streak = 0
        streak_to_speedup = 5  

        messages_to_delete = []
        async for message in dm.history(limit=None):
            if message.author == chotu.user:
                messages_to_delete.append(message)
        total = len(messages_to_delete)
        print(f"Found {total} messages to delete.")

        deleted = 0
        times = []
        start_time = time.time()
        for idx, message in enumerate(messages_to_delete, 1):
            t0 = time.time()
            try:
                await message.delete()
                deleted += 1
                success_streak += 1
                print(f"Deleted message: {message.content[:50]}")
                if success_streak >= streak_to_speedup:
                    delay = max(min_delay, delay - delay_step)
                    success_streak = 0
            except discord.errors.HTTPException as e:
                if e.status == 429 or "rate limited" in str(e).lower():
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after is None:
                        import re
                        match = re.search(r"retry_after['\"]?:?\s*([0-9.]+)", str(e))
                        if match:
                            retry_after = float(match.group(1))
                        else:
                            retry_after = delay * 2 
                    print(f"Rate limited! Sleeping for {retry_after:.2f} seconds.")
                    delay = min(max_delay, delay + delay_step * 2)
                    success_streak = 0
                    await asyncio.sleep(retry_after)
                else:
                    print(f"Failed to delete message: {e}")
            except Exception as e:
                print(f"Failed to delete message: {e}")
            await asyncio.sleep(delay)
            t1 = time.time()
            times.append(t1 - t0)
            avg_time = sum(times) / len(times)
            left = total - idx
            eta = avg_time * left
            print(f"Progress: {idx}/{total} | Estimated time left: {format_seconds(eta)}")

        total_time = time.time() - start_time
        print(f"\nAll messages have been removed (or attempted). Deleted {deleted} messages.")
        print(f"Total time taken: {format_seconds(total_time)}")

    except Exception as e:
        print(f"Failed to fetch DM with user ID {user_id}: {e}")

if __name__ == "__main__":
    chotu.run("token", bot=False)
