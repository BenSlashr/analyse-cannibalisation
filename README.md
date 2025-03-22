# Analyse de Cannibalisation SEO

Cette application permet d'analyser la cannibalisation SEO entre vos pages web en fonction des mots-clés. Elle utilise l'API Google Search Console pour récupérer les données, puis analyse la similarité entre les pages en utilisant Sentence Transformers pour identifier les problèmes de cannibalisation.

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture du projet](#architecture-du-projet)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Structure détaillée du code](#structure-détaillée-du-code)
- [Flux de données](#flux-de-données)
- [API et endpoints](#api-et-endpoints)
- [Algorithme de détection de cannibalisation](#algorithme-de-détection-de-cannibalisation)
- [Interface utilisateur](#interface-utilisateur)
- [Dépendances principales](#dépendances-principales)
- [Résolution des problèmes courants](#résolution-des-problèmes-courants)
- [Contribution](#contribution)

## Fonctionnalités

- **Authentification OAuth2** avec l'API Google Search Console
- **Récupération des données de mots-clés** depuis Google Search Console
- **Analyse de similarité** entre les URLs basée sur les mots-clés
- **Détection automatique de la cannibalisation** entre les pages
- **Calcul des scores de similarité** via Sentence Transformers
- **Visualisation des paires d'URLs cannibalisées** avec métriques importantes
- **Filtrage des résultats** par seuil de similarité
- **Interface utilisateur intuitive** pour analyser les résultats
- **API asynchrone** avec FastAPI pour de meilleures performances

## Architecture du projet

L'application suit une architecture en couches:

```
+------------------+
|  Interface Web   |  <- HTML/CSS/JS (client/templates, client/static)
+------------------+
         |
+------------------+
|   API FastAPI    |  <- main.py, app.py
+------------------+
         |
+------------------+
|    Services      |  <- server/services/
+------------------+
         |
+------------------+
|  Intégrations    |  <- Google Search Console API, Sentence Transformers
+------------------+
```

- **Couche présentation**: Interface utilisateur HTML/CSS/JS
- **Couche API**: FastAPI pour exposer les endpoints
- **Couche services**: Logique métier et traitement des données
- **Couche intégration**: Communication avec les APIs externes

## Installation

### Prérequis

- Python 3.8+
- pip
- Compte Google avec accès à Google Search Console
- Projet Google Cloud Platform avec l'API Search Console activée

### Étapes d'installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/analyse-cannibalisation.git
cd analyse-cannibalisation

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer le fichier .env avec vos identifiants Google Search Console
```

## Configuration

Créez un fichier `.env` à la racine du projet avec les variables suivantes:

```
GOOGLE_CLIENT_ID=votre_client_id
GOOGLE_CLIENT_SECRET=votre_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/callback
SENTENCE_TRANSFORMERS_MODEL=all-MiniLM-L6-v2
```

Pour obtenir les identifiants Google:
1. Créez un projet dans la [Console Google Cloud](https://console.cloud.google.com/)
2. Activez l'API Google Search Console
3. Créez des identifiants OAuth2 pour une application Web
4. Ajoutez l'URI de redirection `http://localhost:5000/auth/callback`

## Utilisation

### Lancement de l'application

```bash
# Activer l'environnement virtuel si ce n'est pas déjà fait
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Lancer l'application
python main.py
```

L'application sera accessible à l'adresse http://localhost:5000

### Workflow d'utilisation

1. **Connexion**: Authentifiez-vous avec votre compte Google
2. **Sélection du site**: Choisissez un site dans Google Search Console
3. **Configuration de l'analyse**: Définissez la période et le seuil de similarité
4. **Lancement de l'analyse**: Cliquez sur "Analyser" pour démarrer
5. **Visualisation des résultats**: Explorez les groupes de mots-clés et les paires d'URLs cannibalisées
6. **Export des résultats**: Exportez les résultats au format JSON

## Structure détaillée du code

### Fichiers principaux

- `main.py`: Point d'entrée de l'application, configuration FastAPI et routes principales
- `app.py`: Configuration de l'application et initialisation des services
- `uvicorn_config.py`: Configuration du serveur Uvicorn

### Backend (server/)

- `server/services/`:
  - `search_console.py`: Service pour interagir avec l'API Google Search Console
  - `similarity.py`: Service d'analyse de similarité et détection de cannibalisation
  - `scraper.py`: Service pour extraire des données des pages web

### Frontend (client/)

- `client/templates/`:
  - `index.html`: Page principale de l'application
  - `auth.html`: Page d'authentification
- `client/static/`:
  - `js/main.js`: Logique JavaScript principale
  - `css/styles.css`: Styles CSS de l'application
  - `img/`: Images et icônes

### Utilitaires (utils/)

- `utils/auth.py`: Fonctions d'authentification
- `utils/helpers.py`: Fonctions utilitaires diverses

## Flux de données

1. **Récupération des données**:
   - L'utilisateur s'authentifie via OAuth2
   - L'application récupère les données de Search Console via l'API
   - Les données sont structurées en format JSON

2. **Traitement et analyse**:
   - Les données sont filtrées selon les critères de l'utilisateur
   - Les mots-clés sont regroupés
   - Les embeddings sont calculés pour mesurer la similarité
   - Les paires d'URLs cannibalisées sont identifiées

3. **Présentation des résultats**:
   - Les résultats sont envoyés au frontend
   - L'interface affiche les groupes de mots-clés et les paires d'URLs
   - Les métriques importantes sont mises en évidence

## API et endpoints

### Endpoints principaux

- `GET /`: Page d'accueil
- `GET /auth/login`: Redirection vers l'authentification Google
- `GET /auth/callback`: Callback après authentification
- `GET /api/sites`: Liste des sites disponibles dans Search Console
- `POST /api/analyze`: Lance l'analyse de cannibalisation
- `GET /api/export`: Exporte les résultats au format JSON

### Exemple de requête d'analyse

```
POST /api/analyze
{
  "site_url": "https://example.com/",
  "start_date": "2023-01-01",
  "end_date": "2023-01-31",
  "similarity_threshold": 0.8,
  "min_clicks": 10,
  "min_impressions": 100
}
```

## Algorithme de détection de cannibalisation

L'algorithme de détection de cannibalisation fonctionne en plusieurs étapes:

1. **Regroupement des mots-clés**: Les mots-clés similaires sont regroupés
2. **Filtrage des données**: Les URLs avec trop peu de clics ou d'impressions sont filtrées
3. **Calcul des embeddings**: Conversion des mots-clés en vecteurs via Sentence Transformers
4. **Calcul de similarité**: Utilisation de la similarité cosinus entre les vecteurs
5. **Identification des paires**: Les paires d'URLs avec une similarité supérieure au seuil sont identifiées
6. **Évaluation du risque**: Calcul du niveau de risque basé sur les métriques SEO

Le code principal de cet algorithme se trouve dans `server/services/similarity.py`.

## Interface utilisateur

L'interface utilisateur est conçue pour être intuitive et informative:

- **En-tête**: Navigation et informations sur l'utilisateur connecté
- **Formulaire de configuration**: Paramètres pour l'analyse
- **Section des résultats**: Affichage des groupes de mots-clés
- **Cartes de mots-clés**: Chaque carte contient:
  - Le mot-clé principal
  - L'URL de référence (avec le plus de clics)
  - Les URLs qui se cannibalisent avec l'URL de référence
  - Les métriques importantes (position, clics, impressions, CTR)
  - Le score de similarité entre les URLs

## Dépendances principales

- **FastAPI**: Framework API asynchrone haute performance
- **Uvicorn**: Serveur ASGI pour FastAPI
- **Google API Client**: Client pour l'API Google Search Console
- **Sentence Transformers**: Modèles pour calculer les embeddings
- **aiohttp**: Client HTTP asynchrone
- **Pydantic**: Validation des données et sérialisation
- **python-dotenv**: Gestion des variables d'environnement
- **Bootstrap**: Framework CSS pour l'interface utilisateur

## Résolution des problèmes courants

### Erreur d'authentification Google

Si vous rencontrez des erreurs d'authentification:
1. Vérifiez que vos identifiants dans le fichier `.env` sont corrects
2. Assurez-vous que l'API Search Console est activée dans votre projet Google Cloud
3. Vérifiez que les URIs de redirection sont correctement configurées

### Erreur "Insufficient Permission"

Cette erreur se produit lorsque l'utilisateur n'a pas les permissions nécessaires pour accéder aux données d'un site dans Search Console:
1. Assurez-vous que l'utilisateur a accès au site dans Google Search Console
2. Vérifiez que le format de l'URL du site est correct (par exemple, essayez avec "https://www.example.com/" au lieu de "sc-domain:example.com")

### Limite de 5000 URLs

L'application utilise une limite de 5000 lignes de données lors de la récupération des informations depuis l'API Google Search Console. Cette limite est définie dans la méthode `get_keywords_data` du fichier `server/services/search_console.py`. Pour modifier cette limite:

```python
# Dans server/services/search_console.py
def get_keywords_data(self, site_url, start_date, end_date, dimensions=None, row_limit=10000):
    # ...
```

## Contribution

Les contributions sont les bienvenues! Pour contribuer:

1. Forkez le dépôt
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committez vos changements (`git commit -m 'Ajout d'une nouvelle fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrez une Pull Request
