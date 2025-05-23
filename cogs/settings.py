from main import *
import json
import os
import discord
from discord.ext import commands
class EditConfigModal(discord.ui.Modal):
    def __init__(self, config):
        super().__init__(title="Edit Configuration")
        self.config = config
        for key, value in config.items():
            full_path = f"{self.config.get('path', '.')}.{key}"
            self.add_item(discord.ui.InputText(
                label=full_path,
                value=str(value),
                custom_id=full_path
            ))
        self.key = key
        self.value = value

    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.children[0].value  
        await interaction.response.send_message(f"`{self.key}` updated to `{new_value}`", ephemeral=True)

class InitConfigView(discord.ui.View):
    def __init__(self, config, interaction):
        super().__init__()
        self.config = config
        self.interaction = interaction

    @discord.ui.button(label="Edit Configuration", style=discord.ButtonStyle.blurple, custom_id="edit_config_button")
    async def edit_config_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditConfigModal(self.config)
        await interaction.response.send_modal(modal)
def recursive_update(original: dict, template: dict) -> dict:
    """Recursively update a dictionary with missing keys from a template."""
    for key, value in template.items():
        if isinstance(value, dict):
            original[key] = recursive_update(original.get(key, {}), value)
        else:
            original.setdefault(key, value)
    return original

class InitHomeView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="init_button")
    async def init_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ensure only administrators can run this
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="Access Denied",
                description="### You must have admin to run this, silly!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        stage1 = discord.Embed(
            title="Initialization in Progress... Hang on!",
            description="This message will update once it's done :3",
            color=0xff0000
        )
        await interaction.response.send_message(embed=stage1, ephemeral=True)

        guild = interaction.guild
        bot_member = guild.me

        required_permissions = discord.Permissions(
            manage_roles=True,
            manage_channels=True,
            manage_guild=True,
            view_audit_log=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            mention_everyone=True,
            use_external_emojis=True,
            add_reactions=True
        )

        if not bot_member.guild_permissions.is_superset(required_permissions):
            missing_perms = [
                perm for perm, value in required_permissions
                if not getattr(bot_member.guild_permissions, perm)
            ]
            error_embed = discord.Embed(
                title="Init Failed: Missing Permissions",
                description=f"### Missing the following permissions: `{', '.join(missing_perms)}`\nPlease fix the permissions and try again!",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        with open("config.json", "r") as f:
            template_config = json.load(f)["template"]["guild"]
        config_path = f"data/guilds/{guild.id}.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        if os.path.exists(config_path):
            # Merge missing keys from template
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
                updated_config = recursive_update(existing_config, template_config)
            with open(config_path, 'w') as f:
                json.dump(updated_config, f, indent=4)
            config_message = "A configuration already exists and has been updated with missing keys."
        else:
            with open(config_path, 'w') as f:
                json.dump(template_config, f, indent=4)
            config_message = "A configuration has been created for your guild!"

        stage2 = discord.Embed(
            title="Initialization Finished!",
            description="No errors found",
            color=0x00ff00
        )
        stage2.add_field(
            name="Tests Passed",
            value="Permissions\n> The bot has sufficient permissions to work!\n"
                  f"Config\n> {config_message}"
        )

        await interaction.followup.send(embed=stage2, ephemeral=True)

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Settings commands to manage your bot instance."

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(name="settings", description="Settings commands to manage your bot instance.")
    async def settings(self, ctx):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="config", description="Change the configurations for your guild. Usage: settings config <key> <value>")
    async def config(self, ctx):
        config = get_guild_config(ctx.guild.id)
        path = f"data/guilds/{ctx.guild.id}.json"
        config_patched = {k: v for k, v in config.items() if k != "level"}
        formatted_config = json.dumps(config_patched, indent=4)

        embed = discord.Embed(
            title="Configure Codygen",
            description=(
                f"Path to your config file: `{path}`\n"
                f"Current config: ```json\n{formatted_config}```\n"
                "## Use the navigation menu below to change your config"
            ),
            color=0xf1f1f1
        )
        await ctx.reply(embed=embed, ephemeral=True, view=InitConfigView(config, ctx.interaction))

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="init", description="Check if the bot has valid permissions and create a config.")
    async def init(self, ctx):
        if not ctx.interaction:
            await ctx.reply(
                "## A prefixed command won't work for this.\n### Please use the </settings init:1338195438494289964> command instead.",
                ephemeral=True
            )
            return
        embed = discord.Embed(
            title="Codygen - Initialization",
            description="## Hi! Welcome to Codygen :3\nPress the button below to start the initialization"
        )
        await ctx.reply(embed=embed, ephemeral=True, view=InitHomeView())

async def setup(bot):
    await bot.add_cog(Settings(bot))

