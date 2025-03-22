import requests
import aiohttp
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import asyncio
import time
import random
from urllib.parse import urlparse

class WebScraper:
    """Service pour scraper les éléments importants des pages web"""
    
    def __init__(self, max_workers=5, timeout=10, user_agent=None):
        """Initialiser le scraper avec des paramètres configurables"""
        self.max_workers = max_workers
        self.timeout = timeout
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    def scrape_urls(self, urls):
        """Scraper plusieurs URLs en parallèle"""
        results = {}
        
        print(f"Démarrage du scraping pour {len(urls)} URLs...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_url, url): url for url in urls}
            for future in future_to_url:
                url = future_to_url[future]
                try:
                    data = future.result()
                    results[url] = data
                    print(f"✅ URL scrapée avec succès: {url}")
                except Exception as e:
                    results[url] = {'error': str(e)}
                    print(f"❌ Erreur lors du scraping de {url}: {str(e)}")
        
        end_time = time.time()
        print(f"Scraping terminé pour {len(urls)} URLs en {end_time - start_time:.2f} secondes")
        
        return results
    
    async def scrape_urls_async(self, urls):
        """Scraper plusieurs URLs en parallèle de manière asynchrone"""
        results = {}
        tasks = []
        
        # Créer une session aiohttp pour réutiliser les connexions
        async with aiohttp.ClientSession() as session:
            # Créer une tâche pour chaque URL
            for url in urls:
                tasks.append(self.scrape_url_async(session, url))
            
            # Exécuter toutes les tâches en parallèle
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Traiter les résultats
            for i, url in enumerate(urls):
                if isinstance(completed_tasks[i], Exception):
                    results[url] = {'error': str(completed_tasks[i])}
                else:
                    results[url] = completed_tasks[i]
        
        return results
    
    def scrape_url(self, url):
        """Scraper une URL et extraire les éléments importants"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Ajouter un délai aléatoire pour éviter d'être bloqué
        time.sleep(random.uniform(0.5, 2.0))
        
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire les éléments importants
        data = {
            'title': self._get_title(soup),
            'meta_description': self._get_meta_description(soup),
            'h1': self._get_headings(soup, 'h1'),
            'h2': self._get_headings(soup, 'h2'),
            'h3': self._get_headings(soup, 'h3'),
            'content_length': len(response.text),
            'domain': self._get_domain(url)
        }
        
        return data
    
    async def scrape_url_async(self, session, url):
        """Scraper une URL de manière asynchrone et extraire les éléments importants"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Ajouter un délai aléatoire pour éviter d'être bloqué
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        async with session.get(url, headers=headers, timeout=self.timeout) as response:
            response.raise_for_status()
            html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraire les éléments importants
            data = {
                'title': self._get_title(soup),
                'meta_description': self._get_meta_description(soup),
                'h1': self._get_headings(soup, 'h1'),
                'h2': self._get_headings(soup, 'h2'),
                'h3': self._get_headings(soup, 'h3'),
                'content_length': len(html),
                'domain': self._get_domain(url)
            }
            
            return data
    
    def _get_title(self, soup):
        """Extraire le titre de la page"""
        title_tag = soup.find('title')
        return title_tag.text.strip() if title_tag else ''
    
    def _get_meta_description(self, soup):
        """Extraire la meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '').strip() if meta_desc else ''
    
    def _get_headings(self, soup, tag):
        """Extraire les balises de titre (h1, h2, etc.)"""
        headings = soup.find_all(tag)
        return [h.text.strip() for h in headings]
    
    def _get_domain(self, url):
        """Extraire le domaine de l'URL"""
        parsed_url = urlparse(url)
        return parsed_url.netloc
