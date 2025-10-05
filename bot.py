import discord
from discord.ext import commands
import json
import random
import os
from pathlib import Path
from threading import Thread
from flask import Flask

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

DATA_FILE = Path(__file__).parent / 'data.json'

HALLOWEEN_EMOJIS = [
    {'emoji': '👻', 'probability': 0.4000, 'points': 4, 'name': 'fantôme'},
    {'emoji': '🧟', 'probability': 0.3500, 'points': 7, 'name': 'zombie'},
    {'emoji': '💀', 'probability': 0.1500, 'points': 10, 'name': 'crâne'},
    {'emoji': '🔪', 'probability': 0.0909, 'points': 12, 'name': 'couteau'},
    {'emoji': '🐺', 'probability': 0.0082, 'points': 17, 'name': 'loup'},
    {'emoji': '🎃', 'probability': 0.0009, 'points': 31, 'name': 'citrouille'},
]

message_count = 0
next_reaction_at = random.randint(15, 30)
user_data = {}

app = Flask(__name__)

@app.route('/')
def home():
    return '🎃 Bot Discord Halloween est en ligne! 👻', 200

@app.route('/health')
def health():
    return {'status': 'alive', 'bot': str(bot.user) if bot.user else 'starting'}, 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def select_random_emoji():
    random_value = random.random()
    cumulative_probability = 0
    
    for emoji_data in HALLOWEEN_EMOJIS:
        cumulative_probability += emoji_data['probability']
        if random_value < cumulative_probability:
            return emoji_data
    
    return HALLOWEEN_EMOJIS[-1]

def load_data():
    global user_data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        print('✅ Données chargées avec succès')
    except FileNotFoundError:
        user_data = {}
        print('📝 Nouveau fichier de données créé')

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'❌ Erreur lors de la sauvegarde: {e}')

def get_user_data(user_id):
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = {
            'points': 0,
            'healthBoost': 0,
            'reactions': {}
        }
    return user_data[user_id_str]

@bot.event
async def on_ready():
    print(f'🎃 Bot connecté en tant que {bot.user}')
    print(f'👻 Prêt à réagir tous les {next_reaction_at} messages')
    print(f'🏥 Health Boost ACTIVÉ en permanence - Points x1.5!')
    load_data()

@bot.event
async def on_message(message):
    global message_count, next_reaction_at
    
    if message.author.bot:
        return
    
    message_count += 1
    
    if message_count >= next_reaction_at:
        selected_emoji = select_random_emoji()
        
        try:
            await message.add_reaction(selected_emoji['emoji'])
            
            user = get_user_data(message.author.id)
            points_earned = int(selected_emoji['points'] * 1.5)
            user['healthBoost'] += points_earned - selected_emoji['points']
            user['points'] += points_earned
            
            if selected_emoji['name'] not in user['reactions']:
                user['reactions'][selected_emoji['name']] = 0
            user['reactions'][selected_emoji['name']] += 1
            
            save_data()
            
            await message.reply(
                f"{selected_emoji['emoji']} Tu as gagné **{points_earned} points** avec {selected_emoji['name']}! (Health Boost x1.5 actif!) "
                f"Total: **{user['points']} points**"
            )
            
            print(f"🎃 Réaction {selected_emoji['emoji']} ({selected_emoji['points']}pts) sur message de {message.author}")
        except Exception as e:
            print(f'❌ Erreur lors de la réaction: {e}')
        
        message_count = 0
        next_reaction_at = random.randint(15, 30)
        print(f'⏳ Prochaine réaction dans {next_reaction_at} messages')
    
    await bot.process_commands(message)

@bot.command(name='points')
async def points_command(ctx):
    await leaderboard_command(ctx)

@bot.command(name='leaderboard')
async def leaderboard_command(ctx):
    if not user_data:
        await ctx.reply('🎃 Aucun joueur n\'a encore de points!')
        return
    
    sorted_users = sorted(
        [(user_id, data) for user_id, data in user_data.items()],
        key=lambda x: x[1]['points'],
        reverse=True
    )[:10]
    
    leaderboard = '🎃 **CLASSEMENT HALLOWEEN** 🎃\n\n'
    
    for i, (user_id, data) in enumerate(sorted_users):
        try:
            user = await bot.fetch_user(int(user_id))
            medal = '🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else f'{i + 1}.'
            leaderboard += f'{medal} **{user.name}**: {data["points"]} points\n'
        except:
            leaderboard += f'{i + 1}. Utilisateur inconnu: {data["points"]} points\n'
    
    await ctx.reply(leaderboard)

@bot.command(name='healthboost')
async def healthboost_command(ctx):
    await ctx.reply('🏥 Health Boost est ACTIVÉ EN PERMANENCE ✅\n💪 Tous les points sont toujours multipliés par 1.5!')

@bot.command(name='stats')
async def stats_command(ctx):
    user = get_user_data(ctx.author.id)
    stats_msg = f'📊 **Tes statistiques Halloween** 📊\n\n'
    stats_msg += f'💰 Points totaux: **{user["points"]}**\n'
    stats_msg += f'🏥 Points de Health Boost: **{user["healthBoost"]}**\n\n'
    stats_msg += f'🎃 **Réactions reçues:**\n'
    
    if user['reactions']:
        for emoji_name, count in user['reactions'].items():
            emoji_data = next((e for e in HALLOWEEN_EMOJIS if e['name'] == emoji_name), None)
            emoji_icon = emoji_data['emoji'] if emoji_data else '❓'
            stats_msg += f'{emoji_icon} {emoji_name}: {count}x\n'
    else:
        stats_msg += 'Aucune réaction pour le moment!\n'
    
    await ctx.reply(stats_msg)

@bot.command(name='help')
async def help_command(ctx):
    help_msg = """🎃 **BOT HALLOWEEN - AIDE** 🎃

**Fonctionnement:**
Le bot réagit automatiquement tous les 15-30 messages avec un emoji Halloween!

**🏥 Health Boost ACTIVÉ en permanence - Tous les points sont multipliés par 1.5!**

**Emojis et Points (avec Health Boost x1.5):**
👻 Fantôme: 6 points (40% de chance)
🧟 Zombie: 10 points (35% de chance)
💀 Crâne: 15 points (15% de chance)
🔪 Couteau: 18 points (10% de chance)
🐺 Loup: 25 points (9% de chance)
🎃 Citrouille: 46 points (1% de chance)

**Commandes:**
`!points` ou `!leaderboard` - Affiche le classement
`!stats` - Affiche tes statistiques
`!healthboost` - Affiche le statut du Health Boost
`!help` - Affiche cette aide"""
    
    await ctx.reply(help_msg)

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print('❌ ERREUR: DISCORD_TOKEN non défini dans les variables d\'environnement!')
        print('📝 Veuillez ajouter votre token Discord dans les Secrets')
        exit(1)
    
    print('🌐 Démarrage du serveur web...')
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print('🤖 Démarrage du bot Discord...')
    try:
        bot.run(token)
    except Exception as e:
        print(f'❌ Erreur de connexion: {e}')
        exit(1)
