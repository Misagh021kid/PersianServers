import asyncio
import os
import json
from datetime import datetime
from server_manager_selector import *
import discord
from discord.ext import commands
from discord import Button, app_commands, ui, View

TOKEN = "---- Paste Your Token Here ----"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

server_creation_cooldown =  {}

def get_uptime(user_id: str) -> str:
    data = load_data()
    if user_id not in data or data[user_id]["status"] != "running":
        return "❗ Server Roshan Nist."

    try:
        start_time_str = data[user_id].get("start_time")
        if not start_time_str:
            return "❗ Start time Peyda Nashod."

        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        uptime = datetime.now() - start_time
        return str(uptime).split('.')[0]

    except Exception as e:
        return f"❗ Error: {e}"

@tree.command(name="createserver", description="Sakhte server Minecraft")
@app_commands.describe(version="Version Minecraft (Faght 1.20)")
async def createserver(interaction: discord.Interaction, version: str):
    user_id = str(interaction.user.id)
    await interaction.response.send_message("🔧 Dar hale sakht server hastim...", ephemeral=True)

    try:
        response = create_server(user_id, version)
        if response is None or response.startswith("❌"):
            await interaction.followup.send(
                f"⚠️ Server sakhte nashod: {response or 'Error nameaelum'}",
                ephemeral=True
            )
            return
    except Exception as e:
        await interaction.followup.send(
            f"❌ Khatayi rokh dad: {e}",
            ephemeral=True
        )
        return

    await interaction.followup.send(response, ephemeral=True)


@tree.command(name="serverpanel", description="Panel Modiriyat Server")
async def serverpanel(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    status = get_server_status(user_id)
    uptime_result = get_uptime(user_id)

    if status['status'] == "not_found":
        await interaction.response.send_message("❗ Serveri sabt nashode. Aval server besaz. ya ```/register``` kon", ephemeral=True)
        return

    async def generate_embed():

        color = discord.Color.green() if status["status"] == "running" else discord.Color.orange()
        embed = discord.Embed(title=f"🖥️ Persian Servers Panel", color=color)
        embed.add_field(name="📡Status", value=status["status"], inline=True)
        embed.add_field(name="📍Address", value=f"Play.PersianCraft.Top:{status['port']}", inline=True)
        embed.add_field(name="🧩Version", value=f"`{status['version']}`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"{uptime_result}", inline=True)
        embed.set_footer(text="📦 PersianServers | 1.0.0v Panel", icon_url="https://cdn-icons-png.flaticon.com/512/190/190411.png")
        return embed

    embed = await generate_embed()
    view = ServerControlButtons(user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    message = await interaction.original_response()
    for _ in range(6):
        await asyncio.sleep(5)
        updated_embed = await generate_embed()
        await message.edit(embed=updated_embed, view=view)

class PluginControlButtons(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    @discord.ui.button(label="✅ OnePlayerSleep", style=discord.ButtonStyle.success, row=0)
    async def oneplayersleep(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = toggle_plugin(self.user_id, "OnePlayerSleep")
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="✅ LuckPerms", style=discord.ButtonStyle.success, row=0)
    async def luckperms(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = toggle_plugin(self.user_id, "LuckPerms")
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="✅ ViaVersion", style=discord.ButtonStyle.success, row=1)
    async def viaversion(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = toggle_plugin(self.user_id, "ViaVersion")
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="✅ ViaBackwards", style=discord.ButtonStyle.success, row=1)
    async def viabackwards(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = toggle_plugin(self.user_id, "ViaBackwards")
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="✅ Essentials", style=discord.ButtonStyle.success, row=1)
    async def essentials(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = toggle_plugin(self.user_id, "Essentials")
        await interaction.response.send_message(result, ephemeral=True)

class WhitelistEditorView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.update_buttons()
    def update_buttons(self):
        self.clear_items()
        self.add_item(AddPlayerButton(self.user_id))
        for name in get_whitelisted_players(self.user_id):
            self.add_item(WhitelistToggleButton(self.user_id, name))

class WhitelistToggleButton(Button):
    def __init__(self, user_id: str, player_name: str):
        super().__init__(label=player_name, style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.player_name = player_name
    async def callback(self, interaction: discord.Interaction):
        result = toggle_whitelist_player(self.user_id, self.player_name)
        await interaction.response.edit_message(content=result, view=WhitelistEditorView(self.user_id))

class AddPlayerButton(Button):
    def __init__(self, user_id: str):
        super().__init__(label="➕ Add Player", style=discord.ButtonStyle.success)
        self.user_id = user_id
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddPlayerModal(self.user_id))

class AddPlayerModal(discord.ui.Modal, title="Add Player to Whitelist"):
    player_name = discord.ui.TextInput(label="Player Name", placeholder="Masalan: Misagh")

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
    async def on_submit(self, interaction: discord.Interaction):
        result = toggle_whitelist_player(self.user_id, self.player_name.value)
        await interaction.response.send_message(result, ephemeral=True, view=WhitelistEditorView(self.user_id))

class ServerSettingsView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
    @discord.ui.button(label="✅ Online Mode", style=discord.ButtonStyle.secondary)
    async def toggle_online_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_online_mode
        result = toggle_online_mode(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="📦 Command Block", style=discord.ButtonStyle.secondary)
    async def toggle_cmd_block(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_command_block
        result = toggle_command_block(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="⚔️ PvP", style=discord.ButtonStyle.secondary)
    async def toggle_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_pvp
        result = toggle_pvp(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="💀 Hardcore", style=discord.ButtonStyle.secondary)
    async def toggle_hardcore(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_hardcore
        result = toggle_hardcore(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="👥 Whitelist", style=discord.ButtonStyle.secondary)
    async def toggle_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_white_list
        result = toggle_white_list(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="👻 Monsters", style=discord.ButtonStyle.secondary)
    async def toggle_monsters(self, interaction: discord.Interaction, button: discord.ui.Button):
        from server_manager_linux import toggle_monster
        result = toggle_monster(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)
    @discord.ui.button(label="📏 View Distance", style=discord.ButtonStyle.primary)
    async def set_view_distance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
        "🔢 Yek View Distance entekhab kon:",
        view=ViewDistanceSelector(self.user_id),
        ephemeral=True
    )
    @discord.ui.button(label="👥 Edit Whitelist", style=discord.ButtonStyle.primary)
    async def edit_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
        content="🎮 Player ha ro edite konid:",
        view=WhitelistEditorView(self.user_id),
        ephemeral=True
    )
    @discord.ui.button(label="📢 Set MOTD", style=discord.ButtonStyle.primary)
    async def set_motd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetMotdModal(self.user_id))
        
class ViewDistanceButton(discord.ui.Button):
    def __init__(self, user_id: str, value: int):
        super().__init__(label=str(value), style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.value = value
    async def callback(self, interaction: discord.Interaction):
        from server_manager_linux import set_view_distance
        result = set_view_distance(self.user_id, self.value)
        await interaction.response.send_message(result, ephemeral=True)

class ViewDistanceSelector(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        for i in range(1, 6):
            self.add_item(ViewDistanceButton(user_id, i))

class SetMotdModal(discord.ui.Modal, title="Set MOTD"):
    motd = discord.ui.TextInput(label="MOTD Jadid", placeholder="Welcome to my server!")
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
    async def on_submit(self, interaction: discord.Interaction):
        from server_manager_linux import set_motd
        result = set_motd(self.user_id, self.motd.value)
        await interaction.response.send_message(result, ephemeral=True)

class ServerControlButtons(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    @discord.ui.button(label="▶️ Start", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = start_server(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = stop_server(self.user_id)
        await interaction.response.send_message(result, ephemeral=True)

    @discord.ui.button(label="❌ Delete", style=discord.ButtonStyle.secondary)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        delete_server(self.user_id)
        await interaction.response.send_message("🗑️ Server Shoma Delete Shod.", ephemeral=True)
    @discord.ui.button(label="🧩 Plugins", style=discord.ButtonStyle.primary)
    async def plugins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
        "🔌 Plugin ha ra entekhab konid:", 
        view=PluginControlButtons(self.user_id),
        ephemeral=True
    )
        
    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.primary)
    async def settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔧 Server Settings:",
            view=ServerSettingsView(self.user_id),
            ephemeral=True
    )
        
    @discord.ui.button(label="🔁 Restart Server", style=discord.ButtonStyle.danger)
    async def restart_server_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = restart_server(self.user_id)
        await interaction.followup.send(result, ephemeral=True)

@tree.command(name="servers", description="Liste serverha baraye modir ha")
async def servers(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if not interaction.user.guild_permissions.administrator and user_id not in ["530561445528731648", "1370031391412326591"]:
        await interaction.response.send_message("⛔ Shoma dastresi be in dastor nadarid.", ephemeral=True)
        return
    if not os.path.exists("data/servers.json"):
        await interaction.response.send_message("❗ Hich serveri sabt nashode.", ephemeral=True)
        return
    with open("data/servers.json", "r") as f:
        servers = json.load(f)
    if not servers:
        await interaction.response.send_message("❗ Hich serveri sabt nashode.", ephemeral=True)
        return
    embed = discord.Embed(title="🗂️ Liste Server-ha", color=discord.Color.blurple())
    view = ui.View()
    for idx, (uid, data) in enumerate(sorted(servers.items(), key=lambda x: x[1]["port"])):
        mention = f"<@{uid}>"
        status = data.get("status", "unknown").capitalize()
        version = data.get("version", "N/A")
        port = data.get("port", "???")
        server_id = idx + 1

        embed.add_field(
            name=f"🆔 Server {server_id}",
            value=f"{mention} | **{status}** | `{version}` | Port: `{port}`",
            inline=False
        )

        view.add_item(ServerManageButton(user_id=uid, label=f"Manage Server {server_id}"))

    embed.set_footer(text="🎛️ Panel Modiriyat Serverha | PersianServers")
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ServerManageButton(ui.Button):
    def __init__(self, user_id: str, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.green)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⛔ Shoma dastresi be in server nadarid.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        status = get_server_status(user_id)
        uptime_result = get_uptime(user_id)

        if status['status'] == "not_found":
            await interaction.response.send_message("❗ Serveri baraye in user sabt nashode.", ephemeral=True)
            return

        color = discord.Color.green() if status["status"] == "running" else discord.Color.orange()
        embed = discord.Embed(title="🖥️ Server Panel", color=color)
        embed.add_field(name="📡Status", value=status["status"], inline=True)
        embed.add_field(name="📍Address", value=f"Play.PersianCraft.Top:{status['port']}", inline=True)
        embed.add_field(name="🧩Version", value=f"`{status['version']}`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"{uptime_result}", inline=True)
        embed.set_footer(text="📦 PersianServers | 1.0.0v Panel", icon_url="https://cdn-icons-png.flaticon.com/512/190/190411.png")

        view = ServerControlButtons(self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)
