import os
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import json
import pandas as pd
import uvicorn
from pathlib import Path
from server.services.search_console import SearchConsoleService
from server.services.similarity import SimilarityAnalyzer
from server.services.scraper import WebScraper
from pydantic import BaseModel
import logging

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(
    title="Analyse de Cannibalisation SEO",
    description="API pour analyser la cannibalisation SEO entre les pages web",
    version="1.0.0",
    root_path="/analyse-cannibalisation"
)


# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurer les fichiers statiques et les templates
app.mount("/static", StaticFiles(directory="client/static"), name="static")
templates = Jinja2Templates(directory="client/templates")

# Ajouter une fonction url_for personnalisée aux templates Jinja2
templates.env.globals["url_for"] = lambda name, **path_params: f"/{name}" + (f"/{path_params['filename']}" if 'filename' in path_params else "")

# Initialiser les services
search_console_service = SearchConsoleService()
similarity_analyzer = SimilarityAnalyzer()
web_scraper = WebScraper()

# Modèles de données Pydantic
class SearchConsoleRequest(BaseModel):
    site_url: str
    start_date: str
    end_date: str
    similarity_threshold: float = 0.8
    scrape_pages: bool = False
    primary_keyword_only: bool = False
    min_clicks: int = 0
    min_impressions: int = 0

class ReportRequest(BaseModel):
    total_keywords: int
    similarity_threshold: float
    analyzed_keywords: int
    cannibalized_keywords: int
    groups: List[Dict[str, Any]]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil de l'application"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/auth/url")
async def get_auth_url():
    """Obtenir l'URL d'authentification Google"""
    auth_url = search_console_service.get_auth_url()
    return {"auth_url": auth_url}

@app.get("/auth/callback")
async def auth_callback(code: str):
    """Callback après authentification Google"""
    search_console_service.authorize(code)
    return RedirectResponse(url="/")

@app.get("/api/sites")
async def get_sites():
    """Récupérer la liste des sites disponibles dans Search Console"""
    sites = search_console_service.get_sites()
    return {"sites": sites}

@app.post("/api/analyze/search-console")
async def analyze_search_console(data: dict):
    """
    Analyser les données de la Search Console
    """
    try:
        logging.info(f"Analyse des données de la Search Console pour {data}")
        
        site_url = data.get('site_url')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        similarity_threshold = float(data.get('similarity_threshold', 0.8))
        primary_keyword_only = data.get('primary_keyword_only', False)
        min_clicks = int(data.get('min_clicks', 0))
        min_impressions = int(data.get('min_impressions', 0))
        max_rows = int(data.get('max_rows', 100000))
        use_date_chunks = data.get('use_date_chunks', True)
        chunk_size = int(data.get('chunk_size', 7))
        
        # Récupérer les données de la Search Console
        try:
            keywords_data = await search_console_service.get_keywords_data_async(
                site_url, 
                start_date, 
                end_date, 
                ['query', 'page'],
                max_rows=max_rows,
                use_date_chunks=use_date_chunks,
                chunk_size=chunk_size
            )
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données de la Search Console: {e}")
            error_message = str(e)
            
            # Vérifier si c'est une erreur d'autorisation
            if "User does not have sufficient permission for site" in error_message:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Erreur d'autorisation",
                        "message": f"Vous n'avez pas les permissions suffisantes pour accéder aux données de {site_url}. Veuillez vérifier que vous êtes bien propriétaire ou avez des droits d'utilisateur sur cette propriété dans Google Search Console."
                    }
                )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Erreur lors de la récupération des données",
                    "message": f"Une erreur s'est produite lors de la récupération des données de la Search Console: {error_message}"
                }
            )
        
        print(f"Nombre de mots-clés récupérés: {len(keywords_data)}")
        
        # Vérifier si les données contiennent les champs 'clicks' et 'impressions'
        sample_data = keywords_data[0] if keywords_data else {}
        print(f"Exemple de données: {sample_data}")
        
        # Récupérer les données de scraping si nécessaire
        scraped_data = None
        if data.get('scrape_pages', False):
            # Extraire toutes les URLs uniques
            urls = set()
            for item in keywords_data:
                urls.add(item['url'])
            
            # Scraper les URLs
            scraped_data = await web_scraper.scrape_urls_async(list(urls))
        
        # Analyser la cannibalisation
        try:
            results = await similarity_analyzer.analyze_keywords_async(
                keywords_data, 
                similarity_threshold,
                primary_keyword_only,
                scraped_data,
                min_clicks,
                min_impressions
            )
            
            # Ajouter les données de scraping aux résultats si elles ont été récupérées
            if scraped_data:
                results["scraped_data"] = scraped_data
            
            return results
        except Exception as e:
            print(f"Erreur lors de l'analyse des mots-clés: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")
    except Exception as e:
        print(f"Erreur générale: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/csv")
async def analyze_csv(
    file: UploadFile = File(...),
    content_file: Optional[UploadFile] = File(None),
    similarity_threshold: float = Form(0.8),
    analyze_content: bool = Form(False),
    primary_keyword_only: bool = Form(False),
    min_clicks: int = Form(0),
    min_impressions: int = Form(0)
):
    """Analyser les données d'un fichier CSV"""
    if not file:
        raise HTTPException(status_code=400, detail="No file part")
    
    if file.filename == "":
        raise HTTPException(status_code=400, detail="No selected file")
    
    # Lire le fichier CSV
    try:
        contents = await file.read()
        # Sauvegarder temporairement le fichier
        temp_file = Path("temp_upload.csv")
        with open(temp_file, "wb") as f:
            f.write(contents)
        
        # Lire avec pandas
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
                    df = pd.read_csv(temp_file, encoding=encoding, sep=sep, on_bad_lines='skip')
                    print(f"Fichier CSV lu avec succès en utilisant l'encodage {encoding} et le séparateur '{sep}'")
                    success = True
                    break
                except Exception as e:
                    print(f"Échec de lecture avec l'encodage {encoding} et le séparateur '{sep}': {str(e)}")
        
        if not success:
            # Dernière tentative avec des options plus permissives
            try:
                df = pd.read_csv(temp_file, encoding='latin1', sep=None, engine='python', on_bad_lines='skip')
                print("Fichier CSV lu avec l'encodage latin1 et détection automatique du séparateur")
                success = True
            except Exception as final_e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Impossible de lire le fichier CSV avec aucun encodage ou séparateur connu. Erreur: {str(final_e)}"
                )
        
        # Vérifier que le fichier a les colonnes requises
        print(f"Colonnes trouvées dans le CSV: {list(df.columns)}")
        
        # Définir les mappings de colonnes possibles (pour différents formats d'export)
        column_mappings = {
            # Format attendu par défaut
            'standard': {
                'Mot-clé': 'keyword',
                'URL': 'url',
                'Position': 'position',
                'Clics': 'clicks'
            },
            # Format Google Search Console
            'gsc': {
                'Query': 'keyword',
                'Page': 'url',
                'Position': 'position',
                'Clicks': 'clicks'
            }
        }
        
        # Détecter quel mapping utiliser
        selected_mapping = None
        for mapping_name, mapping in column_mappings.items():
            if all(col in df.columns for col in mapping.keys()):
                selected_mapping = mapping
                print(f"Utilisation du mapping de colonnes '{mapping_name}'")
                break
        
        if not selected_mapping:
            # Aucun mapping ne correspond, afficher un message d'erreur détaillé
            all_possible_columns = set()
            for mapping in column_mappings.values():
                all_possible_columns.update(mapping.keys())
            
            missing_columns = [col for col in all_possible_columns if col not in df.columns]
            print(f"Colonnes manquantes: {missing_columns}")
            
            # Construire un message d'erreur clair
            error_message = "Format de fichier CSV non reconnu. Le fichier doit contenir l'un des ensembles de colonnes suivants :\n"
            for mapping_name, mapping in column_mappings.items():
                error_message += f"- Format {mapping_name}: {', '.join(mapping.keys())}\n"
            
            raise HTTPException(
                status_code=400, 
                detail=error_message
            )
        
        # Créer un nouveau DataFrame avec uniquement les colonnes requises et renommées
        df_processed = pd.DataFrame()
        for old_col, new_col in selected_mapping.items():
            df_processed[new_col] = df[old_col]
        
        # Supprimer le fichier temporaire
        os.remove(temp_file)
        
        # Convertir le DataFrame en format attendu par le service d'analyse
        try:
            keywords_data = df_processed.to_dict("records")
            print(f"Nombre d'enregistrements dans le CSV: {len(keywords_data)}")
            if len(keywords_data) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Le fichier CSV ne contient aucune donnée valide."
                )
        except Exception as e:
            print(f"Erreur lors de la conversion du DataFrame: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du traitement des données CSV: {str(e)}"
            )
        
        # Traiter le fichier de contenu s'il est fourni
        content_data = None
        if content_file and content_file.filename:
            # Si un fichier de contenu est fourni, activer l'analyse de contenu
            analyze_content = True
            
            content_contents = await content_file.read()
            temp_content_file = Path("temp_content_upload.csv")
            with open(temp_content_file, "wb") as f:
                f.write(content_contents)
            
            # Lire avec pandas
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
                        content_df = pd.read_csv(temp_content_file, encoding=encoding, sep=sep, on_bad_lines='skip')
                        print(f"Fichier de contenu CSV lu avec succès en utilisant l'encodage {encoding} et le séparateur '{sep}'")
                        success = True
                        break
                    except Exception as e:
                        print(f"Échec de lecture avec l'encodage {encoding} et le séparateur '{sep}': {str(e)}")
            
            if not success:
                # Dernière tentative avec des options plus permissives
                try:
                    content_df = pd.read_csv(temp_content_file, encoding='latin1', sep=None, engine='python', on_bad_lines='skip')
                    print("Fichier de contenu CSV lu avec l'encodage latin1 et détection automatique du séparateur")
                    success = True
                except Exception as final_e:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Impossible de lire le fichier de contenu CSV avec aucun encodage ou séparateur connu. Erreur: {str(final_e)}"
                    )
            
            # Supprimer le fichier temporaire
            os.remove(temp_content_file)
            
            # Vérifier que le fichier a au moins les colonnes url et content
            print(f"Colonnes trouvées dans le fichier de contenu: {list(content_df.columns)}")
            
            # Définir les mappings de colonnes possibles pour le fichier de contenu
            content_column_mappings = {
                # Format attendu par défaut
                'standard': {
                    'URL': 'url',
                    'Contenu': 'content'
                },
                # Format alternatif (en minuscules)
                'alt': {
                    'url': 'url',
                    'content': 'content'
                },
                # Format spécifique avec Adresse et Extracteurs
                'extracteur': {
                    'Adresse': 'url',
                    'Extracteur 1 1': 'content'
                }
            }
            
            # Détecter quel mapping utiliser
            selected_content_mapping = None
            for mapping_name, mapping in content_column_mappings.items():
                if all(col in content_df.columns for col in mapping.keys()):
                    selected_content_mapping = mapping
                    print(f"Utilisation du mapping de colonnes de contenu '{mapping_name}'")
                    break
            
            if not selected_content_mapping:
                # Aucun mapping ne correspond, afficher un message d'erreur détaillé
                all_possible_columns = set()
                for mapping in content_column_mappings.values():
                    all_possible_columns.update(mapping.keys())
                
                missing_columns = [col for col in all_possible_columns if col not in content_df.columns]
                print(f"Colonnes manquantes dans le fichier de contenu: {missing_columns}")
                
                # Construire un message d'erreur clair
                error_message = "Format de fichier de contenu CSV non reconnu. Le fichier doit contenir l'un des ensembles de colonnes suivants :\n"
                for mapping_name, mapping in content_column_mappings.items():
                    error_message += f"- Format {mapping_name}: {', '.join(mapping.keys())}\n"
                
                raise HTTPException(
                    status_code=400, 
                    detail=error_message
                )
            
            # Déterminer les noms de colonnes réels à utiliser
            url_column = next(old_col for old_col, new_col in selected_content_mapping.items() if new_col == 'url')
            content_column = next(old_col for old_col, new_col in selected_content_mapping.items() if new_col == 'content')
            
            # Préparer les données de contenu
            content_data = {}
            
            # Pour chaque ligne du fichier de contenu
            for _, row in content_df.iterrows():
                url = row[url_column]
                
                # Initialiser le contenu avec la colonne obligatoire
                if pd.isna(row[content_column]):
                    content = ""
                else:
                    content = str(row[content_column])
                
                # Ajouter le contenu des colonnes supplémentaires s'il y en a
                additional_content = []
                for col in content_df.columns:
                    if col not in [url_column, content_column] and pd.notna(row[col]):
                        additional_content.append(str(row[col]))
                
                # Fusionner tout le contenu
                if additional_content:
                    content = content + " " + " ".join(additional_content)
                
                # Stocker dans le dictionnaire
                content_data[url] = content
            
            print(f"Nombre d'URLs avec contenu: {len(content_data)}")
        
        # Récupérer les données de scraping si nécessaire et si aucun fichier de contenu n'est fourni
        scraped_data = None
        if analyze_content and not content_data:
            # Scraper les URLs si nécessaire
            print("Scraping des URLs...")
            scraped_data = {}
            for item in keywords_data:
                url = item["url"]
                if url not in scraped_data:
                    try:
                        scraped_content = web_scraper.scrape_url(url)
                        if scraped_content:
                            scraped_data[url] = scraped_content
                    except Exception as e:
                        print(f"Erreur lors du scraping de {url}: {str(e)}")
        
        # Utiliser les données de contenu fournies si disponibles
        if content_data:
            print("Utilisation des données de contenu fournies...")
            # Convertir les données de contenu au format attendu par le service d'analyse
            formatted_content_data = {}
            for url, content in content_data.items():
                formatted_content_data[url] = {
                    'title': "",  # Par défaut, titre vide
                    'meta_description': "",  # Par défaut, meta description vide
                    'h1': [],  # Par défaut, h1 vide
                    'h2': [],  # Par défaut, h2 vide
                    'content': content  # Le contenu fusionné
                }
            scraped_data = formatted_content_data
        
        # Analyser la cannibalisation
        try:
            results = await similarity_analyzer.analyze_keywords_async(
                keywords_data, 
                similarity_threshold,
                primary_keyword_only,
                scraped_data,
                min_clicks,
                min_impressions
            )
            
            # Ajouter les données de scraping aux résultats si elles ont été récupérées
            if scraped_data:
                results["scraped_data"] = scraped_data
            
            return results
        except Exception as e:
            print(f"Erreur lors de l'analyse des mots-clés: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")
    except Exception as e:
        print(f"Erreur générale: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/report")
async def generate_report(data: Dict[str, Any]):
    """Générer un rapport de cannibalisation"""
    try:
        report = await similarity_analyzer.generate_report_async(data)
        return report
    except Exception as e:
        print(f"Erreur lors de la génération du rapport: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=debug)
