import numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import pandas as pd
from datetime import datetime
import asyncio
import time

class SimilarityAnalyzer:
    """Service pour analyser la similarité entre les URLs basée sur les mots-clés"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """Initialiser l'analyseur de similarité avec un modèle Sentence Transformers"""
        self.model = SentenceTransformer(model_name)
    
    def compute_embeddings(self, texts):
        """Calculer les embeddings pour une liste de textes"""
        print(f"Calcul des embeddings pour {len(texts)} textes...")
        start_time = time.time()
        embeddings = self.model.encode(texts)
        end_time = time.time()
        print(f"Embeddings calculés en {end_time - start_time:.2f} secondes")
        return embeddings
    
    async def compute_embeddings_async(self, texts):
        """Calculer les embeddings pour une liste de textes de manière asynchrone"""
        # Utiliser un thread séparé pour l'encodage car sentence-transformers n'est pas nativement asynchrone
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.compute_embeddings, texts)
    
    def compute_similarity(self, embedding1, embedding2):
        """Calculer la similarité cosinus entre deux embeddings"""
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    
    async def compute_similarity_async(self, embedding1, embedding2):
        """Calculer la similarité cosinus entre deux embeddings de manière asynchrone"""
        # Cette opération est légère, donc nous pouvons simplement appeler la méthode synchrone
        return self.compute_similarity(embedding1, embedding2)
    
    def analyze_keywords(self, keywords_data, similarity_threshold=0.8, primary_keyword_only=False, scraped_data=None, min_clicks=0, min_impressions=0):
        """
        Analyser les données de mots-clés pour trouver la cannibalisation
        
        Args:
            keywords_data: Liste des données de mots-clés
            similarity_threshold: Seuil de similarité pour considérer qu'il y a cannibalisation
            primary_keyword_only: Si True, ne considère que les URLs dont le mot-clé principal est le même
            scraped_data: Données scrapées des pages (optionnel)
            min_clicks: Nombre minimum de clics pour inclure une URL dans l'analyse
            min_impressions: Nombre minimum d'impressions pour inclure une URL dans l'analyse
        """
        print(f"Démarrage de l'analyse de cannibalisation avec {len(keywords_data)} mots-clés...")
        print(f"Seuil de similarité: {similarity_threshold}")
        print(f"Analyse basée sur le contenu: {'Oui' if scraped_data else 'Non'}")
        
        # Filtrer les données pour exclure les URLs contenant un # et appliquer les filtres de clics et impressions
        filtered_keywords_data = []
        for item in keywords_data:
            # Nettoyer et convertir les valeurs en nombres entiers pour éviter les problèmes de type
            clicks_str = str(item.get('clicks', 0) or 0).replace(' ', '')
            impressions_str = str(item.get('impressions', 0) or 0).replace(' ', '')
            
            try:
                clicks = int(float(clicks_str))
                impressions = int(float(impressions_str))
            except ValueError:
                # En cas d'erreur, utiliser 0 comme valeur par défaut
                print(f"Erreur de conversion pour les clics/impressions: {item.get('clicks')}/{item.get('impressions')}")
                clicks = 0
                impressions = 0
            
            if '#' not in item['url'] and clicks >= min_clicks and impressions >= min_impressions:
                # Mettre à jour l'item avec les valeurs converties
                item_copy = item.copy()
                item_copy['clicks'] = clicks
                item_copy['impressions'] = impressions
                filtered_keywords_data.append(item_copy)
        
        print(f"Après filtrage: {len(filtered_keywords_data)} mots-clés")
        
        # Préparer les embeddings de contenu si des données scrapées sont fournies
        content_embeddings = {}
        if scraped_data:
            print(f"Préparation des embeddings de contenu pour {len(scraped_data)} URLs...")
            for url, data in scraped_data.items():
                # Ignorer les URLs contenant un #
                if '#' in url:
                    continue
                content = self._prepare_content_for_embedding(data)
                if content:
                    print(f"Préparation du contenu pour l'embedding: {url[:50]}...")
            
            # Calculer tous les embeddings en une seule fois pour plus d'efficacité
            urls = []
            contents = []
            for url, data in scraped_data.items():
                if '#' not in url:
                    content = self._prepare_content_for_embedding(data)
                    if content:
                        urls.append(url)
                        contents.append(content)
            
            if contents:
                print(f"Calcul des embeddings pour {len(contents)} URLs...")
                embeddings = self.compute_embeddings(contents)
                for i, url in enumerate(urls):
                    content_embeddings[url] = embeddings[i]
                print(f"Embeddings calculés pour {len(content_embeddings)} URLs")
            else:
                print("Aucun contenu valide trouvé pour calculer les embeddings")
        
        if primary_keyword_only:
            # Identifier le mot-clé principal pour chaque URL
            url_to_primary_keyword = self._identify_primary_keywords(filtered_keywords_data)
            
            # Regrouper par mot-clé principal
            primary_keyword_to_urls = defaultdict(list)
            for url, keyword_data in url_to_primary_keyword.items():
                keyword = keyword_data['keyword']
                primary_keyword_to_urls[keyword].append(keyword_data)
            
            # Analyser chaque groupe de mot-clé principal
            results = {
                'total_keywords': len(primary_keyword_to_urls),
                'similarity_threshold': similarity_threshold,
                'analyzed_keywords': 0,
                'cannibalized_keywords': 0,
                'groups': [],
                'analysis_type': 'primary_keyword'
            }
            
            for keyword, urls_data in primary_keyword_to_urls.items():
                # Ne considérer que les mots-clés avec au moins 2 URLs
                if len(urls_data) < 2:
                    continue
                
                results['analyzed_keywords'] += 1
                
                # Trier par position (meilleur classement en premier)
                urls_data = sorted(urls_data, key=lambda x: x['position'])
                
                # Créer un groupe pour ce mot-clé
                group = {
                    'keyword': keyword,
                    'url_count': len(urls_data),
                    'urls': [],
                    'pairs': []
                }
                
                # Ajouter les URLs au groupe
                for data in urls_data:
                    group['urls'].append({
                        'url': data['url'],
                        'position': data['position'],
                        'clicks': data.get('clicks', 0),
                        'impressions': data.get('impressions', 0),
                        'ctr': data.get('ctr', 0)
                    })
                
                # Calculer la similarité entre chaque paire d'URLs
                has_cannibalization = False
                for i in range(len(urls_data)):
                    for j in range(i + 1, len(urls_data)):
                        url1 = urls_data[i]['url']
                        url2 = urls_data[j]['url']
                        
                        # Calculer la similarité en combinant URL et contenu si disponible
                        similarity, similarity_details = self._calculate_combined_similarity(
                            url1, url2, content_embeddings
                        )
                        
                        pair = {
                            'url1': url1,
                            'url2': url2,
                            'similarity': similarity,
                            'similarity_details': similarity_details,
                            'risk': self._assess_risk(similarity, similarity_threshold)
                        }
                        
                        group['pairs'].append(pair)
                        
                        if similarity >= similarity_threshold:
                            has_cannibalization = True
                
                if has_cannibalization:
                    results['cannibalized_keywords'] += 1
                    results['groups'].append(group)
            
            return results
        else:
            # Comportement original - regrouper par mot-clé exact
            keyword_to_urls = defaultdict(list)
            for data in filtered_keywords_data:
                keyword = data['keyword']
                keyword_to_urls[keyword].append(data)
            
            # Analyser chaque groupe de mot-clé
            results = {
                'total_keywords': len(keyword_to_urls),
                'similarity_threshold': similarity_threshold,
                'analyzed_keywords': 0,
                'cannibalized_keywords': 0,
                'groups': [],
                'analysis_type': 'exact_keyword'
            }
            
            for keyword, urls_data in keyword_to_urls.items():
                # Ne considérer que les mots-clés avec au moins 2 URLs
                if len(urls_data) < 2:
                    continue
                
                results['analyzed_keywords'] += 1
                
                # Trier par position (meilleur classement en premier)
                urls_data = sorted(urls_data, key=lambda x: x['position'])
                
                # Créer un groupe pour ce mot-clé
                group = {
                    'keyword': keyword,
                    'url_count': len(urls_data),
                    'urls': [],
                    'pairs': []
                }
                
                # Ajouter les URLs au groupe
                for data in urls_data:
                    group['urls'].append({
                        'url': data['url'],
                        'position': data['position'],
                        'clicks': data.get('clicks', 0),
                        'impressions': data.get('impressions', 0),
                        'ctr': data.get('ctr', 0)
                    })
                
                # Calculer la similarité entre chaque paire d'URLs
                has_cannibalization = False
                for i in range(len(urls_data)):
                    for j in range(i + 1, len(urls_data)):
                        url1 = urls_data[i]['url']
                        url2 = urls_data[j]['url']
                        
                        # Calculer la similarité en combinant URL et contenu si disponible
                        similarity, similarity_details = self._calculate_combined_similarity(
                            url1, url2, content_embeddings
                        )
                        
                        pair = {
                            'url1': url1,
                            'url2': url2,
                            'similarity': similarity,
                            'similarity_details': similarity_details,
                            'risk': self._assess_risk(similarity, similarity_threshold)
                        }
                        
                        group['pairs'].append(pair)
                        
                        if similarity >= similarity_threshold:
                            has_cannibalization = True
                
                if has_cannibalization:
                    results['cannibalized_keywords'] += 1
                    results['groups'].append(group)
            
            return results
    
    async def analyze_keywords_async(self, keywords_data, similarity_threshold=0.8, primary_keyword_only=False, scraped_data=None, min_clicks=0, min_impressions=0):
        """
        Analyser les données de mots-clés pour trouver la cannibalisation de manière asynchrone
        
        Args:
            keywords_data: Liste des données de mots-clés
            similarity_threshold: Seuil de similarité pour considérer qu'il y a cannibalisation
            primary_keyword_only: Si True, ne considère que les URLs dont le mot-clé principal est le même
            scraped_data: Données scrapées des pages (optionnel)
            min_clicks: Nombre minimum de clics pour inclure une URL dans l'analyse
            min_impressions: Nombre minimum d'impressions pour inclure une URL dans l'analyse
        """
        # Pour cette méthode, nous pouvons simplement appeler la méthode synchrone car le traitement est principalement CPU-bound
        # et n'implique pas d'opérations d'I/O qui bénéficieraient de l'asynchronisme
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.analyze_keywords, keywords_data, similarity_threshold, primary_keyword_only, scraped_data, min_clicks, min_impressions)
    
    def _identify_primary_keywords(self, keywords_data):
        """
        Identifier le mot-clé principal pour chaque URL
        
        Le mot-clé principal est celui qui génère le plus de clics pour une URL donnée.
        En cas d'égalité, on utilise le nombre d'impressions comme critère secondaire.
        """
        # Regrouper les données par URL
        url_to_keywords = defaultdict(list)
        for data in keywords_data:
            url = data['url']
            url_to_keywords[url].append(data)
        
        # Pour chaque URL, trouver le mot-clé principal
        url_to_primary_keyword = {}
        for url, keywords in url_to_keywords.items():
            # Trier par clics (ou impressions si pas de clics)
            sorted_keywords = sorted(
                keywords, 
                key=lambda x: (x.get('clicks', 0), x.get('impressions', 0)), 
                reverse=True
            )
            if sorted_keywords:
                url_to_primary_keyword[url] = sorted_keywords[0]
        
        return url_to_primary_keyword
    
    def _calculate_url_similarity(self, url1, url2):
        """Calculer une similarité simple basée sur les URLs"""
        segments1 = url1.split('/')
        segments2 = url2.split('/')
        
        # Compter les segments communs
        common_segments = set(segments1) & set(segments2)
        total_segments = set(segments1) | set(segments2)
        
        if not total_segments:
            return 0.0
        
        return len(common_segments) / len(total_segments)
    
    def _calculate_content_similarity(self, embedding1, embedding2):
        """
        Calculer la similarité entre deux embeddings de contenu
        
        Args:
            embedding1: Premier embedding de contenu
            embedding2: Deuxième embedding de contenu
        
        Returns:
            Similarité entre les deux embeddings (float)
        """
        return float(self.compute_similarity(embedding1, embedding2))
    
    def _calculate_combined_similarity(self, url1, url2, content_embeddings):
        """
        Calculer une similarité combinée basée sur les URLs et le contenu
        
        Args:
            url1: Première URL
            url2: Deuxième URL
            content_embeddings: Dictionnaire des embeddings de contenu par URL
        
        Returns:
            Tuple (similarité combinée, détails de similarité)
        """
        # Calculer la similarité d'URL
        url_similarity = self._calculate_url_similarity(url1, url2)
        
        # Calculer la similarité de contenu si les embeddings sont disponibles
        content_similarity = None
        if content_embeddings and url1 in content_embeddings and url2 in content_embeddings:
            print(f"Calcul de similarité de contenu entre {url1} et {url2}")
            content_similarity = self._calculate_content_similarity(
                content_embeddings[url1], 
                content_embeddings[url2]
            )
            print(f"Similarité de contenu: {content_similarity:.4f}")
        
        # Si la similarité de contenu n'est pas disponible, utiliser uniquement la similarité d'URL
        if content_similarity is None:
            print(f"Pas d'embeddings disponibles pour {url1} ou {url2}, utilisation de la similarité d'URL uniquement: {url_similarity:.4f}")
            return float(url_similarity), {
                'url_similarity': float(url_similarity),
                'content_similarity': None,
                'combined_similarity': float(url_similarity)
            }
        
        # Si la similarité de contenu est disponible, l'utiliser à 100%
        combined_similarity = content_similarity
        
        print(f"Similarité combinée (100% contenu): {combined_similarity:.4f}")
        
        # Retourner la similarité combinée et les détails
        return float(combined_similarity), {
            'url_similarity': float(url_similarity),
            'content_similarity': float(content_similarity),
            'combined_similarity': float(combined_similarity)
        }
    
    def _prepare_content_for_embedding(self, scraped_data):
        """
        Préparer le contenu d'une page pour l'embedding
        
        Args:
            scraped_data: Données scrapées d'une page
        
        Returns:
            Texte préparé pour l'embedding
        """
        if not scraped_data:
            return ""
        
        # Combiner les éléments importants en un seul texte avec une pondération
        title = scraped_data.get('title', '')
        meta_description = scraped_data.get('meta_description', '')
        h1 = " ".join(scraped_data.get('h1', []))
        h2 = " ".join(scraped_data.get('h2', []))
        
        # Donner plus de poids aux éléments importants en les répétant
        content = f"{title} {title} {meta_description} {meta_description} {h1} {h1} {h2}"
        return content.strip()
    
    def _assess_risk(self, similarity, threshold):
        """Évaluer le niveau de risque basé sur la similarité"""
        if similarity >= threshold + 0.1:
            return "ÉLEVÉ"
        elif similarity >= threshold:
            return "MOYEN"
        elif similarity >= threshold - 0.1:
            return "FAIBLE"
        else:
            return "AUCUN"
    
    def analyze_content_similarity(self, scraped_data):
        """Analyser la similarité de contenu entre les pages scrapées"""
        urls = list(scraped_data.keys())
        contents = []
        
        for url in urls:
            content = self._prepare_content_for_embedding(scraped_data[url])
            contents.append(content)
        
        # Calculer les embeddings
        embeddings = self.compute_embeddings(contents)
        
        # Calculer la matrice de similarité
        similarity_matrix = np.zeros((len(urls), len(urls)))
        for i in range(len(urls)):
            for j in range(len(urls)):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarity_matrix[i][j] = self.compute_similarity(embeddings[i], embeddings[j])
        
        # Créer un DataFrame pour faciliter l'analyse
        df = pd.DataFrame(similarity_matrix, index=urls, columns=urls)
        
        return df
    
    async def analyze_content_similarity_async(self, scraped_data):
        """Analyser la similarité de contenu entre les pages scrapées de manière asynchrone"""
        urls = list(scraped_data.keys())
        contents = []
        
        for url in urls:
            content = self._prepare_content_for_embedding(scraped_data[url])
            contents.append(content)
        
        # Calculer les embeddings de manière asynchrone
        embeddings = await self.compute_embeddings_async(contents)
        
        # Calculer la matrice de similarité
        similarity_matrix = np.zeros((len(urls), len(urls)))
        for i in range(len(urls)):
            for j in range(len(urls)):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarity_matrix[i][j] = self.compute_similarity(embeddings[i], embeddings[j])
        
        # Créer un DataFrame pour faciliter l'analyse
        df = pd.DataFrame(similarity_matrix, index=urls, columns=urls)
        
        return df
    
    def generate_report(self, analysis_results):
        """Générer un rapport de cannibalisation"""
        now = datetime.now()
        
        report = {
            'generated_at': now.strftime('%Y-%m-%d à %H:%M:%S'),
            'total_keywords_analyzed': analysis_results['analyzed_keywords'],
            'cannibalized_keywords': analysis_results['cannibalized_keywords'],
            'similarity_threshold': analysis_results['similarity_threshold'],
            'analysis_type': analysis_results.get('analysis_type', 'exact_keyword'),
            'groups': []
        }
        
        # Trier les groupes par nombre d'URLs (du plus grand au plus petit)
        sorted_groups = sorted(analysis_results['groups'], key=lambda x: x['url_count'], reverse=True)
        
        for group in sorted_groups:
            report_group = {
                'keyword': group['keyword'],
                'url_count': group['url_count'],
                'urls': group['urls'],
                'pairs': []
            }
            
            # Ne garder que les paires avec une similarité au-dessus du seuil
            for pair in group['pairs']:
                if pair['similarity'] >= analysis_results['similarity_threshold']:
                    report_group['pairs'].append(pair)
            
            # Trier les paires par similarité (de la plus élevée à la plus basse)
            report_group['pairs'] = sorted(report_group['pairs'], key=lambda x: x['similarity'], reverse=True)
            
            report['groups'].append(report_group)
        
        return report
    
    async def generate_report_async(self, analysis_results):
        """Générer un rapport de cannibalisation de manière asynchrone"""
        # Cette méthode est légère en termes de calcul, donc nous pouvons simplement appeler la méthode synchrone
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.generate_report, analysis_results)
