import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
import json
import pandas as pd
from server.services.search_console import SearchConsoleService
from server.services.similarity import SimilarityAnalyzer
from server.services.scraper import WebScraper

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, 
            static_folder='client/static',
            template_folder='client/templates')

app.secret_key = os.getenv('SECRET_KEY', 'dev_key')
CORS(app)

# Initialiser les services
search_console_service = SearchConsoleService()
similarity_analyzer = SimilarityAnalyzer()
web_scraper = WebScraper()

@app.route('/')
def index():
    """Page d'accueil de l'application"""
    return render_template('index.html')

@app.route('/api/auth/url', methods=['GET'])
def get_auth_url():
    """Obtenir l'URL d'authentification Google"""
    auth_url = search_console_service.get_auth_url()
    return jsonify({'auth_url': auth_url})

@app.route('/auth/callback')
def auth_callback():
    """Callback après authentification Google"""
    code = request.args.get('code')
    search_console_service.authorize(code)
    return redirect('/')

@app.route('/api/sites', methods=['GET'])
def get_sites():
    """Récupérer la liste des sites disponibles dans Search Console"""
    sites = search_console_service.get_sites()
    return jsonify({'sites': sites})

@app.route('/api/analyze/search-console', methods=['POST'])
def analyze_search_console():
    """Analyser les données de Search Console"""
    data = request.json
    site_url = data.get('site_url')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    similarity_threshold = float(data.get('similarity_threshold', 0.8))
    max_rows = int(data.get('max_rows', 100000))
    use_date_chunks = data.get('use_date_chunks', True)
    chunk_size = int(data.get('chunk_size', 7))
    
    # Récupérer les données de Search Console avec pagination
    if use_date_chunks:
        keywords_data = search_console_service.get_keywords_data_by_date_chunks(
            site_url, 
            start_date, 
            end_date, 
            max_rows=max_rows,
            chunk_size=chunk_size
        )
    else:
        keywords_data = search_console_service.get_keywords_data(
            site_url, 
            start_date, 
            end_date, 
            max_rows=max_rows
        )
    
    # Ajouter des statistiques sur les données récupérées
    total_keywords = len(keywords_data)
    
    # Récupérer les données de scraping si nécessaire
    scraped_data = None
    if data.get('scrape_pages', False):
        urls = []
        for item in keywords_data:
            urls.append(item['url'])
        
        scraped_data = web_scraper.scrape_urls(urls)
    
    # Analyser la cannibalisation avec les données scrapées si disponibles
    results = similarity_analyzer.analyze_keywords(
        keywords_data, 
        similarity_threshold,
        primary_keyword_only=data.get('primary_keyword_only', False),
        scraped_data=scraped_data,
        min_clicks=data.get('min_clicks', 0),
        min_impressions=data.get('min_impressions', 0)
    )
    
    # Ajouter des statistiques sur les résultats
    cannibalization_count = sum(1 for group in results.get('groups', []) if len(group.get('urls', [])) > 1)
    
    # Ajouter les statistiques aux résultats
    results['stats'] = {
        'total_keywords': total_keywords,
        'cannibalization_count': cannibalization_count
    }
    
    # Ajouter les données scrapées aux résultats si elles existent
    if scraped_data:
        results['scraped_data'] = scraped_data
    
    return jsonify(results)

@app.route('/api/analyze/csv', methods=['POST'])
def analyze_csv():
    """Analyser les données d'un fichier CSV"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    similarity_threshold = float(request.form.get('similarity_threshold', 0.8))
    
    # Lire le fichier CSV
    try:
        encodings_to_try = ['latin1', 'utf-8', 'cp1252', 'iso-8859-1', 'utf-16']
        success = False
        
        # Essayer différents séparateurs et encodages, en commençant par ";" qui est le séparateur mentionné par l'utilisateur
        separators = [';', ',', '\t']
        
        for sep in separators:
            if success:
                break
                
            for encoding in encodings_to_try:
                try:
                    # Ajouter on_bad_lines='skip' pour ignorer les lignes problématiques
                    df = pd.read_csv(file, encoding=encoding, sep=sep, on_bad_lines='skip')
                    print(f"Fichier CSV lu avec succès en utilisant l'encodage {encoding} et le séparateur '{sep}'")
                    success = True
                    break
                except Exception as e:
                    print(f"Échec de lecture avec l'encodage {encoding} et le séparateur '{sep}': {str(e)}")
        
        if not success:
            # Dernière tentative avec des options plus permissives
            try:
                df = pd.read_csv(file, encoding='latin1', sep=None, engine='python', on_bad_lines='skip')
                print("Fichier CSV lu avec l'encodage latin1 et détection automatique du séparateur")
                success = True
            except Exception as final_e:
                return jsonify({'error': f"Impossible de lire le fichier CSV avec aucun encodage ou séparateur connu. Erreur: {str(final_e)}"}), 400
        
        # Vérifier que le fichier a les colonnes requises
        required_columns = ['keyword', 'url', 'position']
        if not all(col in df.columns for col in required_columns):
            missing_columns = [col for col in required_columns if col not in df.columns]
            return jsonify({'error': f"Colonnes manquantes dans le fichier CSV: {', '.join(missing_columns)}. Les colonnes requises sont: {', '.join(required_columns)}"}), 400
        
        # Convertir le DataFrame en format attendu par le service d'analyse
        keywords_data = df.to_dict('records')
        
        # Traiter le fichier de contenu s'il est fourni
        content_data = None
        if 'content_file' in request.files and request.files['content_file'].filename != '':
            content_file = request.files['content_file']
            
            # Si un fichier de contenu est fourni, activer l'analyse de contenu
            scrape_pages = True
            
            # Lire avec pandas
            try:
                encodings_to_try = ['latin1', 'utf-8', 'cp1252', 'iso-8859-1', 'utf-16']
                success = False
                
                # Essayer différents séparateurs et encodages, en commençant par ";" qui est le séparateur mentionné par l'utilisateur
                separators = [';']  # Prioriser le séparateur ";"
                
                for sep in separators:
                    if success:
                        break
                        
                    for encoding in encodings_to_try:
                        try:
                            # Ajouter on_bad_lines='skip' pour ignorer les lignes problématiques
                            content_df = pd.read_csv(content_file, encoding=encoding, sep=sep, on_bad_lines='skip')
                            print(f"Fichier de contenu CSV lu avec succès en utilisant l'encodage {encoding} et le séparateur '{sep}'")
                            success = True
                            break
                        except Exception as e:
                            print(f"Échec de lecture avec l'encodage {encoding} et le séparateur '{sep}': {str(e)}")
                
                if not success:
                    # Essayer d'autres séparateurs si ";" ne fonctionne pas
                    separators = [',', '\t']
                    for sep in separators:
                        if success:
                            break
                            
                        for encoding in encodings_to_try:
                            try:
                                # Ajouter on_bad_lines='skip' pour ignorer les lignes problématiques
                                content_df = pd.read_csv(content_file, encoding=encoding, sep=sep, on_bad_lines='skip')
                                print(f"Fichier de contenu CSV lu avec succès en utilisant l'encodage {encoding} et le séparateur '{sep}'")
                                success = True
                                break
                            except Exception as e:
                                print(f"Échec de lecture avec l'encodage {encoding} et le séparateur '{sep}': {str(e)}")
                    
                    if not success:
                        # Dernière tentative avec des options plus permissives
                        try:
                            content_df = pd.read_csv(content_file, encoding='latin1', sep=None, engine='python', on_bad_lines='skip')
                            print("Fichier de contenu CSV lu avec l'encodage latin1 et détection automatique du séparateur")
                            success = True
                        except Exception as final_e:
                            return jsonify({'error': f"Impossible de lire le fichier de contenu CSV avec aucun encodage ou séparateur connu. Erreur: {str(final_e)}"}), 400
            
            except Exception as e:
                return jsonify({'error': str(e)}), 400
            
            # Vérifier que le fichier a au moins les colonnes url et content
            if "url" not in content_df.columns or not any(col.startswith("content") for col in content_df.columns):
                return jsonify({'error': 'Content file must contain at least columns: url, content'}), 400
            
            # Préparer les données de contenu
            content_data = {}
            for _, row in content_df.iterrows():
                url = row["url"]
                
                # Récupérer toutes les colonnes de contenu
                content_cols = [col for col in content_df.columns if col.startswith("content")]
                
                # Préparer les données de contenu dans le format attendu par le service d'analyse
                content_values = []
                for col in content_cols:
                    if pd.notna(row.get(col)):
                        content_values.append(str(row[col]))
                
                # Si au moins une colonne de contenu a une valeur, ajouter à content_data
                if content_values:
                    # Simuler le format des données scrapées
                    content_data[url] = {
                        'title': content_values[0] if len(content_values) > 0 else "",
                        'meta_description': content_values[1] if len(content_values) > 1 else "",
                        'h1': [content_values[2]] if len(content_values) > 2 else [],
                        'h2': [content_values[3]] if len(content_values) > 3 else [],
                        'content': " ".join(content_values)
                    }
        
        # Récupérer les données de scraping si nécessaire et si aucun fichier de contenu n'est fourni
        scraped_data = None
        if scrape_pages:
            if content_file and 'content_df' in locals():
                # Utiliser les données de contenu fournies
                print("Utilisation des données de contenu fournies...")
                # Convertir les données de contenu au format attendu par le service d'analyse
                formatted_content_data = {}
                for _, row in content_df.iterrows():
                    url = row['URL']
                    
                    # Initialiser le contenu avec la colonne obligatoire
                    content = row['Contenu']
                    
                    # Ajouter le contenu des colonnes supplémentaires s'il y en a
                    additional_content = []
                    for col in content_df.columns:
                        if col not in ['URL', 'Contenu'] and pd.notna(row[col]):
                            additional_content.append(str(row[col]))
                    
                    # Fusionner tout le contenu
                    if additional_content:
                        content = content + " " + " ".join(additional_content)
                    
                    # Stocker dans le dictionnaire au format attendu
                    formatted_content_data[url] = {
                        'title': "",  # Par défaut, titre vide
                        'meta_description': "",  # Par défaut, meta description vide
                        'h1': [],  # Par défaut, h1 vide
                        'h2': [],  # Par défaut, h2 vide
                        'content': content  # Le contenu fusionné
                    }
                
                scraped_data = formatted_content_data
                print(f"Nombre d'URLs avec contenu: {len(scraped_data)}")
            else:
                # Extraire toutes les URLs uniques
                urls = set()
                for item in keywords_data:
                    urls.add(item['url'])
                
                # Scraper les URLs
                scraped_data = {}
                for url in urls:
                    try:
                        scraped_content = web_scraper.scrape_url(url)
                        if scraped_content:
                            scraped_data[url] = scraped_content
                    except Exception as e:
                        print(f"Erreur lors du scraping de {url}: {str(e)}")
        
        # Analyser la cannibalisation avec les données scrapées si disponibles
        primary_keyword_only = request.form.get('primary_keyword_only', 'false') == 'true'
        min_clicks = int(request.form.get('min_clicks', 0))
        min_impressions = int(request.form.get('min_impressions', 0))
        
        results = similarity_analyzer.analyze_keywords(
            keywords_data, 
            similarity_threshold,
            primary_keyword_only=primary_keyword_only,
            scraped_data=scraped_data,
            min_clicks=min_clicks,
            min_impressions=min_impressions
        )
        
        # Ajouter les données scrapées aux résultats si elles existent
        if scraped_data:
            results['scraped_data'] = scraped_data
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/report', methods=['POST'])
def generate_report():
    """Générer un rapport de cannibalisation"""
    data = request.json
    report = similarity_analyzer.generate_report(data)
    return jsonify(report)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
