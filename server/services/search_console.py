import os
import json
from datetime import datetime, timedelta
import aiohttp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

class SearchConsoleService:
    """Service pour interagir avec l'API Google Search Console"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        self.scopes = ['https://www.googleapis.com/auth/webmasters.readonly']
        self.credentials = None
        self.service = None
    
    def get_auth_url(self):
        """Générer l'URL d'authentification Google"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url
    
    def authorize(self, code):
        """Autoriser l'application avec le code reçu de Google"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=code)
        self.credentials = flow.credentials
        self.service = build('searchconsole', 'v1', credentials=self.credentials)
        
        return True
    
    def get_sites(self):
        """Récupérer la liste des sites disponibles dans Search Console"""
        if not self.service:
            return []
        
        sites = self.service.sites().list().execute()
        return sites.get('siteEntry', [])
    
    def get_keywords_data(self, site_url, start_date, end_date, dimensions=None, max_rows=100000):
        """Récupérer les données de mots-clés depuis Search Console avec pagination
        
        Args:
            site_url (str): URL du site dans Search Console
            start_date (str): Date de début au format YYYY-MM-DD
            end_date (str): Date de fin au format YYYY-MM-DD
            dimensions (list): Dimensions à récupérer (par défaut: query et page)
            max_rows (int): Nombre maximum de lignes à récupérer (par défaut: 100000)
        
        Returns:
            list: Liste des données de mots-clés
        """
        if not self.service:
            return []
        
        if dimensions is None:
            dimensions = ['query', 'page']
        
        # Limite de l'API par requête
        api_limit = 25000
        
        # Nombre de requêtes nécessaires
        num_requests = (max_rows + api_limit - 1) // api_limit
        
        all_keywords_data = []
        
        for i in range(num_requests):
            start_row = i * api_limit
            
            # Si on a déjà atteint le maximum, on arrête
            if start_row >= max_rows:
                break
            
            # Calculer la limite pour cette requête
            current_limit = min(api_limit, max_rows - start_row)
            
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': current_limit,
                'startRow': start_row
            }
            
            try:
                response = self.service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                
                # Transformer les données pour notre analyse
                for row in response.get('rows', []):
                    keyword = None
                    url = None
                    
                    for i, dimension in enumerate(dimensions):
                        if dimension == 'query':
                            keyword = row['keys'][i]
                        elif dimension == 'page':
                            url = row['keys'][i]
                    
                    if keyword and url:
                        all_keywords_data.append({
                            'keyword': keyword,
                            'url': url,
                            'clicks': row.get('clicks', 0),
                            'impressions': row.get('impressions', 0),
                            'ctr': row.get('ctr', 0),
                            'position': row.get('position', 0)
                        })
                
                # Si la réponse contient moins de lignes que demandé, on a atteint la fin des données
                if len(response.get('rows', [])) < current_limit:
                    break
                    
            except Exception as e:
                print(f"Erreur lors de la récupération des données: {str(e)}")
                break
        
        return all_keywords_data
    
    def get_keywords_data_by_date_chunks(self, site_url, start_date, end_date, dimensions=None, max_rows=100000, chunk_size=7):
        """Récupérer les données de mots-clés en segmentant par périodes pour contourner la limite de l'API
        
        Args:
            site_url (str): URL du site dans Search Console
            start_date (str): Date de début au format YYYY-MM-DD
            end_date (str): Date de fin au format YYYY-MM-DD
            dimensions (list): Dimensions à récupérer (par défaut: query et page)
            max_rows (int): Nombre maximum de lignes à récupérer au total
            chunk_size (int): Taille des segments de dates en jours
            
        Returns:
            list: Liste des données de mots-clés
        """
        if not self.service:
            return []
            
        # Convertir les dates en objets datetime
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculer le nombre de jours entre les deux dates
        delta = (end - start).days + 1
        
        # Si la période est plus courte que chunk_size, faire une seule requête
        if delta <= chunk_size:
            return self.get_keywords_data(site_url, start_date, end_date, dimensions, max_rows)
        
        # Diviser la période en segments
        all_keywords_data = []
        unique_keyword_url_pairs = set()  # Pour éviter les doublons
        
        # Calculer combien de lignes par segment
        segment_max_rows = max(1000, max_rows // ((delta + chunk_size - 1) // chunk_size))
        
        current_date = start
        while current_date <= end:
            # Calculer la date de fin du segment
            segment_end = min(current_date + timedelta(days=chunk_size-1), end)
            
            # Formater les dates pour l'API
            segment_start_str = current_date.strftime('%Y-%m-%d')
            segment_end_str = segment_end.strftime('%Y-%m-%d')
            
            print(f"Récupération des données pour la période {segment_start_str} à {segment_end_str}")
            
            # Récupérer les données pour ce segment
            segment_data = self.get_keywords_data(
                site_url, 
                segment_start_str, 
                segment_end_str, 
                dimensions, 
                segment_max_rows
            )
            
            # Ajouter les données uniques au résultat
            for item in segment_data:
                # Créer une clé unique pour chaque paire mot-clé/URL
                key = (item['keyword'], item['url'])
                
                # Si cette paire n'a pas encore été ajoutée, l'ajouter
                if key not in unique_keyword_url_pairs:
                    unique_keyword_url_pairs.add(key)
                    all_keywords_data.append(item)
                    
                    # Si on a atteint le maximum, arrêter
                    if len(all_keywords_data) >= max_rows:
                        return all_keywords_data
            
            # Passer au segment suivant
            current_date = segment_end + timedelta(days=1)
        
        return all_keywords_data
    
    async def get_keywords_data_async(self, site_url, start_date, end_date, dimensions=None, max_rows=100000, use_date_chunks=True, chunk_size=7):
        """Version asynchrone pour récupérer les données de mots-clés depuis Search Console avec pagination"""
        # Pour l'instant, nous utilisons la méthode synchrone car Google API Client ne supporte pas nativement async
        # Dans une implémentation plus avancée, on pourrait utiliser aiohttp pour faire des requêtes HTTP asynchrones
        if use_date_chunks:
            return self.get_keywords_data_by_date_chunks(site_url, start_date, end_date, dimensions, max_rows, chunk_size)
        else:
            return self.get_keywords_data(site_url, start_date, end_date, dimensions, max_rows)
    
    def get_top_keywords_by_url(self, site_url, start_date, end_date, max_rows=100000):
        """Récupérer le mot-clé principal pour chaque URL"""
        keywords_data = self.get_keywords_data(site_url, start_date, end_date, max_rows=max_rows)
        
        # Regrouper par URL et trouver le mot-clé principal (celui avec le plus de clics)
        url_to_keywords = {}
        for data in keywords_data:
            url = data['url']
            if url not in url_to_keywords:
                url_to_keywords[url] = []
            url_to_keywords[url].append(data)
        
        # Pour chaque URL, trouver le mot-clé principal
        top_keywords = []
        for url, keywords in url_to_keywords.items():
            # Trier par clics (ou impressions si pas de clics)
            sorted_keywords = sorted(keywords, key=lambda x: (x['clicks'], x['impressions']), reverse=True)
            if sorted_keywords:
                top_keywords.append(sorted_keywords[0])
        
        return top_keywords
    
    async def get_top_keywords_by_url_async(self, site_url, start_date, end_date, max_rows=100000):
        """Version asynchrone pour récupérer le mot-clé principal pour chaque URL"""
        keywords_data = await self.get_keywords_data_async(site_url, start_date, end_date, max_rows=max_rows)
        
        # Regrouper par URL et trouver le mot-clé principal (celui avec le plus de clics)
        url_to_keywords = {}
        for data in keywords_data:
            url = data['url']
            if url not in url_to_keywords:
                url_to_keywords[url] = []
            url_to_keywords[url].append(data)
        
        # Pour chaque URL, trouver le mot-clé principal
        top_keywords = []
        for url, keywords in url_to_keywords.items():
            # Trier par clics (ou impressions si pas de clics)
            sorted_keywords = sorted(keywords, key=lambda x: (x['clicks'], x['impressions']), reverse=True)
            if sorted_keywords:
                top_keywords.append(sorted_keywords[0])
        
        return top_keywords
