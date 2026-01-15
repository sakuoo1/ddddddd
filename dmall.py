import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import logging
from datetime import datetime
import asyncio
import json

# Configuration du logging avec UTF-8
import sys
import locale

# Forcer l'encodage UTF-8 pour Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuration du bot
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("Fichier config.json non trouvé. Veuillez le créer.")
        exit(1)
    except json.JSONDecodeError:
        logging.error("Erreur de format dans config.json.")
        exit(1)

CONFIG = load_config()

# Priorité à la variable d'environnement si elle existe
TOKEN = os.getenv('DISCORD_TOKEN') or CONFIG.get('token')

# Vérification du token
if not TOKEN:
    logging.error("Token Discord non trouvé. Veuillez définir la variable d'environnement DISCORD_TOKEN ou ajouter le token dans config.json")
    exit(1)

# Configuration des intents avec membres privilégiés
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True  # Nécessaire pour voir les membres

bot = commands.Bot(command_prefix=CONFIG['prefix'], intents=intents)

@bot.event
async def on_ready():
    logging.info(f'{bot.user} est connecté à Discord!')
    logging.info(f'Bot présent dans {len(bot.guilds)} serveurs')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='!mpall help'))

class ServerSelectView(View):
    def __init__(self, bot_instance, message_content, author):
        super().__init__(timeout=60.0)
        self.bot = bot_instance
        self.message_content = message_content
        self.author = author  # Stocker l'auteur original
        self.selected_guild = None
        self.message = None
        
    async def on_timeout(self):
        """Désactive les boutons après timeout"""
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        
    async def send_server_selection(self, ctx):
        """Envoie le panel de sélection de serveur"""
        if not self.bot.guilds:
            await ctx.send("Le bot n'est présent sur aucun serveur.")
            return
            
        embed = discord.Embed(
            title="Sélectionnez un serveur",
            description=f"Message à envoyer: **{self.message_content}**\n\nChoisissez le serveur cible:",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Créer un bouton pour chaque serveur
        for guild in self.bot.guilds[:25]:  # Limite de 25 boutons par message
            member_count = len([m for m in guild.members if not m.bot])
            button = Button(
                label=f"{guild.name} ({member_count} membres)",
                style=discord.ButtonStyle.primary,
                custom_id=f"guild_{guild.id}"
            )
            button.callback = self.create_callback(guild)
            self.add_item(button)
            
        self.message = await ctx.send(embed=embed, view=self)
        
    def create_callback(self, guild):
        """Crée un callback pour chaque bouton de serveur"""
        async def callback(interaction):
            # Vérifier que c'est l'auteur original
            if interaction.user.id != self.author.id:
                await interaction.response.send_message("Vous ne pouvez pas utiliser cette sélection.", ephemeral=True)
                return
                
            self.selected_guild = guild
            
            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            # Lancer la confirmation
            await self.confirm_and_send(interaction)
            
        return callback
        
    async def confirm_and_send(self, interaction):
        """Confirme et envoie le message au serveur sélectionné"""
        guild_members = [m for m in self.selected_guild.members if not m.bot]
        
        confirm_embed = discord.Embed(
            title="Confirmation d'envoi",
            description=f"Vous allez envoyer un message à **{len(guild_members)} membres** du serveur **{self.selected_guild.name}**.\n\nMessage: `{self.message_content}`",
            color=discord.Color.orange()
        )
        
        confirm_view = View(timeout=30.0)
        
        async def confirm_callback(interaction):
            await interaction.response.edit_message(content="Envoi des messages en cours...", embed=None, view=None)
            await self.send_to_guild(interaction)
            
        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="Envoi annule.", embed=None, view=None)
            
        confirm_btn = Button(label="Confirmer", style=discord.ButtonStyle.green)
        confirm_btn.callback = confirm_callback
        confirm_view.add_item(confirm_btn)
        
        cancel_btn = Button(label="Annuler", style=discord.ButtonStyle.red)
        cancel_btn.callback = cancel_callback
        confirm_view.add_item(cancel_btn)
        
        await interaction.followup.send(embed=confirm_embed, view=confirm_view)
        
    async def send_to_guild(self, interaction):
        """Envoie le message à tous les membres du serveur sélectionné"""
        try:
            # Forcer le rafraîchissement des membres
            if not self.selected_guild.chunked:
                await self.selected_guild.chunk(cache=True)
            
            guild_members = [m for m in self.selected_guild.members if not m.bot]
            total_members = len(guild_members)
            success_count = 0
            failed_count = 0
            
            logging.info(f"Envoi vers {self.selected_guild.name} - {total_members} membres")
            
            for i, member in enumerate(guild_members):
                try:
                    await member.send(self.message_content)
                    success_count += 1
                    logging.info(f"OK Message envoyé à {member.name}#{member.discriminator}")
                    
                    if i % CONFIG['rate_limit'] == 0 and i > 0:
                        await asyncio.sleep(1)
                        
                except discord.Forbidden:
                    failed_count += 1
                    logging.warning(f"Messages privés désactivés pour {member.name}#{member.discriminator}")
                except Exception as e:
                    failed_count += 1
                    logging.error(f"Erreur lors de l'envoi à {member.name}#{member.discriminator}: {str(e)}")
            
            # Rapport final
            embed = discord.Embed(
                title="Rapport d'envoi massif",
                color=discord.Color.green() if failed_count == 0 else discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Succès", value=str(success_count), inline=True)
            embed.add_field(name="Échecs", value=str(failed_count), inline=True)
            embed.add_field(name="Total", value=str(total_members), inline=True)
            embed.set_footer(text=f"Serveur: {self.selected_guild.name}")
            
            await interaction.followup.send(embed=embed)
            logging.info(f"Campagne terminée: {success_count}/{total_members} messages envoyés")
            
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi: {str(e)}")
            await interaction.followup.send(f"Une erreur est survenue: {str(e)}")

@bot.command(name='mpall', help='Envoie un message privé avec sélection interactive du serveur')
@commands.has_permissions(administrator=True)
async def mpall(ctx, *, message: str = None):
    """Envoie un message privé avec sélection interactive du serveur"""
    
    if not message:
        await ctx.send("Usage: `!mpall votre message`\nExemple: `!mpall Bonjour à tous !`")
        return
    
    # Créer et envoyer le panel de sélection avec l'auteur
    view = ServerSelectView(bot, message, ctx.author)
    await view.send_server_selection(ctx)

@bot.command(name='serveurs', help='Liste tous les serveurs où le bot est présent')
@commands.has_permissions(administrator=True)
async def list_servers(ctx):
    """Liste tous les serveurs où le bot est présent"""
    
    if not bot.guilds:
        await ctx.send("Le bot n'est présent sur aucun serveur.")
        return
    
    embed = discord.Embed(
        title="Serveurs disponibles",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    for guild in bot.guilds:
        member_count = len([m for m in guild.members if not m.bot])
        embed.add_field(
            name=f"Serveur: {guild.name}",
            value=f"Membres: {member_count} (total: {len(guild.members)})\nID: {guild.id}",
            inline=False
        )
    
    embed.set_footer(text=f"Utilisez !mpall \"nom_serveur\" votre_message")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignorer les commandes non trouvées
    else:
        logging.error(f"Erreur de commande: {str(error)}")
        await ctx.send("Une erreur est survenue lors de l'exécution de la commande.")

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Token invalide. Veuillez vérifier votre token Discord.")
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot: {str(e)}")
