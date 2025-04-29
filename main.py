
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

app = Flask('')

@app.route('/')
def home():
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"✨ Keep-alive pinged at {timestamp}")
    return f"MH LobbyLinker is alive! Last check: {timestamp}"

def run():
    ports = [8080, 8081, 5000]
    for port in ports:
        try:
            app.run(host='0.0.0.0', port=port)
            break
        except OSError as e:
            if port == ports[-1]:
                print(f"All ports failed. Last error: {e}")
            continue

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()

intents = discord.Intents.default()
intents.value = 76800
bot = commands.Bot(command_prefix="!", intents=intents)

active_lobby = None  # Store the single active lobby

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🧙 Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    check_expired_lobby.start()

@bot.tree.command(name="createlobby", description="Create a Monster Hunter Wilds lobby")
@app_commands.describe(lobby_id="Lobby ID")
async def createlobby(interaction: discord.Interaction, lobby_id: str):
    global active_lobby
    
    if active_lobby is not None:
        await interaction.response.send_message("❌ There's already an active lobby. Please wait until it expires or is closed.", ephemeral=True)
        return

    await interaction.response.defer()

    expires_at = datetime.utcnow() + timedelta(hours=6)

    embed = discord.Embed(
        title="🦖 Monster Hunter Wilds Lobby",
        description=f"**Lobby ID:** `{lobby_id}`\n**Expires in:** 6 hours",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Created by {interaction.user.name} | Expires at {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")

    view = LobbyView(lobby_id, expires_at, interaction.user)
    message = await interaction.followup.send(embed=embed, view=view)

    active_lobby = {
        "message": message,
        "lobby_id": lobby_id,
        "expires_at": expires_at,
        "user": interaction.user,
        "view": view
    }

@bot.tree.command(name="activelobby", description="Show the active Monster Hunter Wilds lobby")
async def activelobby(interaction: discord.Interaction):
    if active_lobby is None:
        await interaction.response.send_message("No active lobby right now. Create one with `/createlobby`!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🧭 Active Lobby",
        description=f"**Lobby ID:** `{active_lobby['lobby_id']}`\n**Expires at:** {active_lobby['expires_at'].strftime('%Y-%m-%d %H:%M UTC')}",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Created by {active_lobby['user'].name}")
    await interaction.response.send_message(embed=embed)

class LobbyView(discord.ui.View):
    def __init__(self, lobby_id, expires_at, creator):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.expires_at = expires_at
        self.creator = creator

    @discord.ui.button(label="🔄 Extend (4h)", style=discord.ButtonStyle.green)
    async def extend(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.creator:
            await interaction.response.send_message("Only the creator can extend this lobby.", ephemeral=True)
            return

        if datetime.utcnow() < self.expires_at:
            await interaction.response.send_message("Cannot extend - lobby hasn't expired yet!", ephemeral=True)
            return

        self.expires_at = datetime.utcnow() + timedelta(hours=4)
        if active_lobby and active_lobby["message"].id == interaction.message.id:
            active_lobby["expires_at"] = self.expires_at

        embed = interaction.message.embeds[0]
        embed.description = f"**Lobby ID:** `{self.lobby_id}`\n**Expires in:** 4 hours"
        embed.set_footer(text=f"Created by {self.creator.name} | Expires at {self.expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.message.edit(embed=embed)
        await interaction.channel.send(f"🎮 {self.creator.mention} Your lobby has been extended for 4 more hours! Happy hunting! 🦖")
        await interaction.response.send_message("Lobby extended!", ephemeral=True)

    @discord.ui.button(label="🙅 Expire Now", style=discord.ButtonStyle.red)
    async def expire(self, interaction: discord.Interaction, button: discord.ui.Button):
        global active_lobby
        
        # Check if user has permission (creator or mod/admin)
        has_permission = (
            interaction.user == self.creator or
            interaction.user.guild_permissions.administrator or
            interaction.user.guild_permissions.moderate_members
        )
        
        if not has_permission:
            await interaction.response.send_message("Only the creator, moderators, or admins can expire this lobby.", ephemeral=True)
            return

        try:
            # Clear active lobby first
            active_lobby = None
            
            # Update message content and remove embed
            await interaction.message.edit(content=f"❌ Lobby expired by {interaction.user.mention}", embed=None, view=None)
            await interaction.response.send_message("Lobby has been expired.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("Bot is missing required permissions. Please ensure it has 'Manage Messages' permission.", ephemeral=True)
        except Exception as e:
            print(f"Error in expire button: {e}")
            await interaction.response.send_message("Failed to expire lobby. Please try again.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_expired_lobby():
    global active_lobby
    if active_lobby and datetime.utcnow() >= active_lobby["expires_at"]:
        try:
            creator = active_lobby["user"]
            await active_lobby["message"].edit(content=f"⏰ Hey {creator.mention}! Your lobby has expired! Use `/createlobby` to start a new one or click Extend if you want to keep this one going! 🦖", embed=None, view=None)
            active_lobby = None
        except Exception as e:
            print(f"Error expiring lobby: {e}")

keep_alive()
bot.run(os.getenv("BOT_TOKEN"))
