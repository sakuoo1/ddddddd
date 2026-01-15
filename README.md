# Bot Discord MPALL

## Hébergement gratuit recommandé

### 1. Replit (Plus simple)
1. Allez sur https://replit.com
2. Créez un compte
3. Importez ce projet
4. Ajoutez votre token dans les secrets Replit (`DISCORD_TOKEN`)
5. Activez "Always On" dans les paramètres

### 2. Railway
1. Allez sur https://railway.app
2. Connectez votre GitHub
3. Importez ce repository
4. Ajoutez les variables d'environnement
5. Déployez

### 3. Render
1. Allez sur https://render.com
2. Connectez votre GitHub
3. Créez un "Web Service"
4. Configurez le build command: `pip install -r requirements.txt`
5. Configurez le start command: `python dmall.py`

## Configuration requise

### Discord Bot Portal
1. Allez sur https://discord.com/developers/applications
2. Activez "SERVER MEMBERS INTENT"
3. Copiez le token

### Variables d'environnement
- `DISCORD_TOKEN`: Votre token Discord

## Fichiers nécessaires
- `dmall.py`: Code principal du bot
- `config.json`: Configuration du bot
- `requirements.txt`: Dépendances Python
