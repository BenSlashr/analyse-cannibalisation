document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const csvForm = document.getElementById('csvForm');
    const gscForm = document.getElementById('gscForm');
    const gscAuthBtn = document.getElementById('gscAuthBtn');
    const gscAuth = document.getElementById('gscAuth');
    const siteUrlSelect = document.getElementById('siteUrl');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const analysisResults = document.getElementById('analysisResults');
    const keywordGroups = document.getElementById('keywordGroups');
    const totalKeywordsSpan = document.getElementById('totalKeywords');
    const thresholdUsedSpan = document.getElementById('thresholdUsed');
    const reportDateSpan = document.getElementById('reportDate');
    const resultsCountSpan = document.getElementById('resultsCount');
    const exportReportBtn = document.getElementById('exportReportBtn');
    const exportHtmlBtn = document.getElementById('exportHtmlBtn');
    
    // Sliders
    const csvSimilarityThreshold = document.getElementById('csvSimilarityThreshold');
    const csvThresholdValue = document.getElementById('csvThresholdValue');
    const gscSimilarityThreshold = document.getElementById('gscSimilarityThreshold');
    const gscThresholdValue = document.getElementById('gscThresholdValue');
    const similarityMinFilter = document.getElementById('similarityMinFilter');
    const similarityMinValue = document.getElementById('similarityMinValue');
    
    // Filtres
    const keywordFilter = document.getElementById('keywordFilter');
    const keywordExcludeFilter = document.getElementById('keywordExcludeFilter');
    const useRegex = document.getElementById('useRegex');
    const showExactSimilarity = document.getElementById('showExactSimilarity');
    const minUrlsFilter = document.getElementById('minUrlsFilter');
    const sortBySelect = document.getElementById('sortBy');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const minClicksFilter = document.getElementById('minClicksFilter');
    const minImpressionsFilter = document.getElementById('minImpressionsFilter');
    
    // Variables globales
    let analysisData = null;
    
    // Initialiser les dates
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    startDateInput.value = formatDate(thirtyDaysAgo);
    endDateInput.value = formatDate(today);
    
    // Mettre à jour les valeurs des sliders
    csvSimilarityThreshold.addEventListener('input', function() {
        csvThresholdValue.textContent = this.value;
    });
    
    gscSimilarityThreshold.addEventListener('input', function() {
        gscThresholdValue.textContent = this.value;
    });
    
    similarityMinFilter.addEventListener('input', function() {
        similarityMinValue.textContent = this.value;
    });
    
    // Activer automatiquement l'option "Analyser le contenu des pages" lorsqu'un fichier de contenu est sélectionné
    const contentFileInput = document.getElementById('contentFile');
    const csvScrapePages = document.getElementById('csvScrapePages');
    
    if (contentFileInput && csvScrapePages) {
        contentFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                csvScrapePages.checked = true;
                csvScrapePages.disabled = true; // Désactiver l'option pour éviter qu'elle ne soit décochée
            } else {
                csvScrapePages.disabled = false;
            }
        });
    }
    
    // Authentification Google Search Console
    gscAuthBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/api/auth/url');
            const data = await response.json();
            window.location.href = data.auth_url;
        } catch (error) {
            console.error('Erreur lors de la récupération de l\'URL d\'authentification:', error);
            alert('Erreur lors de la connexion à Google Search Console. Veuillez réessayer.');
        }
    });
    
    // Vérifier si l'utilisateur est authentifié et charger les sites
    async function checkAuthAndLoadSites() {
        try {
            const response = await fetch('/api/sites');
            const data = await response.json();
            
            if (data.sites && data.sites.length > 0) {
                // L'utilisateur est authentifié, afficher le formulaire
                gscAuth.classList.add('d-none');
                gscForm.classList.remove('d-none');
                
                // Stocker la liste complète des sites
                window.allSites = data.sites;
                
                // Remplir le select avec les sites
                populateSiteSelect(data.sites);
                
                // Ajouter l'événement de recherche
                const siteUrlSearch = document.getElementById('siteUrlSearch');
                if (siteUrlSearch) {
                    siteUrlSearch.addEventListener('input', function() {
                        const searchTerm = this.value.toLowerCase();
                        const filteredSites = window.allSites.filter(site => 
                            site.siteUrl.toLowerCase().includes(searchTerm)
                        );
                        populateSiteSelect(filteredSites);
                    });
                }
            }
        } catch (error) {
            console.error('Erreur lors de la vérification de l\'authentification:', error);
        }
    }
    
    // Fonction pour remplir le select avec les sites
    function populateSiteSelect(sites) {
        siteUrlSelect.innerHTML = '<option value="" selected disabled>Sélectionnez un site</option>';
        sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site.siteUrl;
            option.textContent = site.siteUrl; // Afficher l'URL complète
            siteUrlSelect.appendChild(option);
        });
    }
    
    // Vérifier l'authentification au chargement de la page
    checkAuthAndLoadSites();
    
    // Soumission du formulaire CSV
    csvForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        await analyzeData('csv');
    });
    
    // Soumission du formulaire GSC
    gscForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        await analyzeData('gsc');
    });
    
    // Fonction d'analyse des données
    async function analyzeData(source) {
        // Afficher l'indicateur de chargement
        loadingIndicator.classList.remove('d-none');
        analysisResults.classList.add('d-none');
        
        try {
            let response;
            
            if (source === 'csv') {
                const formData = new FormData(csvForm);
                response = await fetch('/api/analyze/csv', {
                    method: 'POST',
                    body: formData
                });
            } else if (source === 'gsc') {
                const formData = new FormData(gscForm);
                const data = {
                    site_url: formData.get('site_url'),
                    start_date: formData.get('start_date'),
                    end_date: formData.get('end_date'),
                    similarity_threshold: parseFloat(formData.get('similarity_threshold')),
                    scrape_pages: formData.get('scrape_pages') === 'on',
                    primary_keyword_only: formData.get('primary_keyword_only') === 'on',
                    max_rows: parseInt(formData.get('max_rows') || 100000),
                    min_clicks: parseInt(formData.get('min_clicks') || 0),
                    min_impressions: parseInt(formData.get('min_impressions') || 0),
                    use_date_chunks: formData.get('use_date_chunks') === 'on',
                    chunk_size: parseInt(formData.get('chunk_size') || 7)
                };
                
                response = await fetch('/api/analyze/search-console', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 403) {
                    // Erreur d'autorisation
                    showError(errorData.message || 'Erreur d\'autorisation. Veuillez vérifier vos permissions dans Google Search Console.');
                } else {
                    // Autres erreurs
                    showError(errorData.message || `Erreur ${response.status}: ${response.statusText}`);
                }
                hideLoading();
                return;
            }
            
            analysisData = await response.json();
            
            // Générer le rapport
            await generateReport(analysisData);
            
            // Cacher l'indicateur de chargement et afficher les résultats
            loadingIndicator.classList.add('d-none');
            analysisResults.classList.remove('d-none');
            
        } catch (error) {
            console.error('Erreur lors de l\'analyse:', error);
            alert('Erreur lors de l\'analyse. Veuillez réessayer.');
            loadingIndicator.classList.add('d-none');
        }
    }
    
    // Générer le rapport
    async function generateReport(data) {
        try {
            const response = await fetch('/api/report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const report = await response.json();
            
            // Stocker les données d'analyse pour les filtres
            analysisData = data;
            
            // Afficher les informations générales
            const threshold = data.similarity_threshold || 0.8;
            thresholdUsedSpan.textContent = threshold;
            reportDateSpan.textContent = new Date().toLocaleDateString();
            
            // Afficher les statistiques
            if (data.stats) {
                totalKeywordsSpan.textContent = `${data.stats.total_keywords} mots-clés analysés (${data.stats.cannibalization_count} avec cannibalisation)`;
            } else {
                totalKeywordsSpan.textContent = `${data.groups.length} groupes de mots-clés analysés`;
            }
            
            // Afficher le nombre de résultats
            const totalGroups = data.groups.length;
            resultsCountSpan.textContent = totalGroups;
            
            // Initialiser le filtre de similarité minimale
            similarityMinFilter.value = threshold;
            similarityMinValue.textContent = threshold;
            
            // Appliquer les filtres actuels et afficher les groupes
            applyFiltersAndSort(data.groups);
            
            // Activer les boutons d'export
            exportReportBtn.disabled = false;
            exportHtmlBtn.disabled = false;
            
        } catch (error) {
            console.error('Erreur lors de la génération du rapport:', error);
            alert('Erreur lors de la génération du rapport. Veuillez réessayer.');
        }
    }
    
    // Fonction pour appliquer les filtres et le tri
    function applyFiltersAndSort(groups) {
        const keywordFilterValue = document.getElementById('keywordFilter').value.trim();
        const keywordExcludeValue = document.getElementById('keywordExcludeFilter').value.trim();
        const useRegex = document.getElementById('useRegex').checked;
        const similarityThreshold = parseFloat(document.getElementById('similarityMinFilter').value);
        const minClicksFilterValue = parseInt(document.getElementById('minClicksFilter').value) || 0;
        const minImpressionsFilterValue = parseInt(document.getElementById('minImpressionsFilter').value) || 0;
        const minUrlsFilterValue = parseInt(document.getElementById('minUrlsFilter').value) || 2;
        const sortByValue = document.getElementById('sortBy').value;
        
        // Préparer les expressions régulières ou les termes de recherche
        let includeRegex = null;
        let excludeTerms = [];
        let excludeRegexes = [];
        
        if (useRegex && keywordFilterValue) {
            try {
                includeRegex = new RegExp(keywordFilterValue, 'i');
            } catch (e) {
                console.error('Expression régulière d\'inclusion invalide:', e);
                alert('Expression régulière d\'inclusion invalide: ' + e.message);
                return;
            }
        }
        
        if (keywordExcludeValue) {
            if (useRegex) {
                // Traiter chaque expression régulière séparément
                const regexStrings = keywordExcludeValue.split(',').map(s => s.trim()).filter(s => s);
                for (const regexStr of regexStrings) {
                    try {
                        excludeRegexes.push(new RegExp(regexStr, 'i'));
                    } catch (e) {
                        console.error('Expression régulière d\'exclusion invalide:', e);
                        alert('Expression régulière d\'exclusion invalide: ' + e.message);
                        return;
                    }
                }
            } else {
                // Utiliser des termes simples pour l'exclusion
                excludeTerms = keywordExcludeValue.split(',').map(s => s.trim().toLowerCase()).filter(s => s);
            }
        }
        
        // Mettre à jour le span qui affiche le seuil utilisé
        thresholdUsedSpan.textContent = similarityThreshold.toFixed(1);
        
        // Filtrer les groupes
        let filteredGroups = groups.filter(group => {
            const keyword = group.keyword;
            
            // Filtrer par mot-clé (inclusion)
            if (keywordFilterValue) {
                if (useRegex) {
                    if (!includeRegex.test(keyword)) {
                        return false;
                    }
                } else if (!keyword.toLowerCase().includes(keywordFilterValue.toLowerCase())) {
                    return false;
                }
            }
            
            // Filtrer par mot-clé (exclusion)
            if (useRegex) {
                for (const regex of excludeRegexes) {
                    if (regex.test(keyword)) {
                        return false;
                    }
                }
            } else {
                for (const term of excludeTerms) {
                    if (keyword.toLowerCase().includes(term)) {
                        return false;
                    }
                }
            }
            
            // Filtrer les URLs par clics et impressions
            const filteredUrls = group.urls.filter(url => {
                return (url.clicks || 0) >= minClicksFilterValue && 
                       (url.impressions || 0) >= minImpressionsFilterValue;
            });
            
            // Si aucune URL ne passe le filtre, exclure le groupe
            if (filteredUrls.length === 0) {
                return false;
            }
            
            // Vérifier le nombre minimum d'URLs
            if (filteredUrls.length < minUrlsFilterValue) {
                return false;
            }
            
            // Mettre à jour les URLs du groupe
            group.urls = filteredUrls;
            group.url_count = filteredUrls.length;
            
            // Filtrer les paires pour ne garder que celles dont les deux URLs passent le filtre
            const filteredUrlsSet = new Set(filteredUrls.map(u => u.url));
            const filteredPairs = group.pairs.filter(pair => {
                return filteredUrlsSet.has(pair.url1) && filteredUrlsSet.has(pair.url2) && 
                       pair.similarity >= similarityThreshold;
            });
            
            // Si aucune paire ne passe le filtre, exclure le groupe
            if (filteredPairs.length === 0) {
                return false;
            }
            
            // Mettre à jour les paires du groupe
            group.pairs = filteredPairs;
            
            return true;
        });
        
        // Trier les groupes
        filteredGroups = sortGroups(filteredGroups, sortByValue);
        
        // Mettre à jour le compteur de résultats
        resultsCountSpan.textContent = `${filteredGroups.length} mots-clés`;
        
        // Afficher les groupes filtrés
        displayKeywordGroups(filteredGroups);
    }
    
    // Fonction pour afficher les groupes de mots-clés
    function displayKeywordGroups(groups) {
        const container = document.getElementById('keywordGroups');
        const showExactSimilarityValue = document.getElementById('showExactSimilarity').checked;
        container.innerHTML = '';
        
        if (groups.length === 0) {
            container.innerHTML = '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>Aucun résultat ne correspond à vos critères de filtrage.</div>';
            return;
        }
        
        groups.forEach(group => {
            const keywordSection = document.createElement('div');
            keywordSection.className = 'keyword-group';
            
            const keywordHeader = document.createElement('div');
            keywordHeader.className = 'keyword-header';
            keywordHeader.innerHTML = `
                <h4 class="keyword-title">${group.keyword}</h4>
                <div class="keyword-stats">
                    <span class="badge bg-primary">${group.url_count} URLs</span>
                </div>
            `;
            
            keywordSection.appendChild(keywordHeader);
            
            // Trouver l'URL de référence (celle avec le plus de clics)
            if (group.urls.length > 0) {
                const referenceUrl = [...group.urls].sort((a, b) => (b.clicks || 0) - (a.clicks || 0))[0];
                
                // Créer la section pour l'URL de référence
                const referenceSection = document.createElement('div');
                referenceSection.className = 'reference-url-section mb-3';
                
                // Déterminer les URLs qui se cannibalisent avec l'URL de référence
                const cannibalizingUrls = group.urls.filter(url => url.url !== referenceUrl.url);
                
                if (cannibalizingUrls.length > 0) {
                    // Créer le tableau pour l'URL de référence et les URLs qui se cannibalisent
                    let tableHTML = `
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th style="width: 50%">URL</th>
                                        <th class="text-end">Position</th>
                                        <th class="text-end">Clics</th>
                                        <th class="text-end">Impressions</th>
                                        <th class="text-end">CTR</th>
                                        <th class="text-end">Similarité</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="reference-url">
                                        <td>
                                            <div class="d-flex align-items-center">
                                                <span class="badge bg-success me-2">Référence</span>
                                                <div class="url-cell">
                                                    <a href="${referenceUrl.url}" target="_blank" class="url-link">${referenceUrl.url}</a>
                                                    <button class="btn btn-sm btn-outline-secondary copy-url-btn" data-url="${referenceUrl.url}">
                                                        <i class="bi bi-clipboard"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="text-end">${parseFloat(referenceUrl.position) ? parseFloat(referenceUrl.position).toFixed(1) : '-'}</td>
                                        <td class="text-end">${referenceUrl.clicks || 0}</td>
                                        <td class="text-end">${referenceUrl.impressions || 0}</td>
                                        <td class="text-end">${referenceUrl.ctr ? (referenceUrl.ctr * 100).toFixed(2) + '%' : '-'}</td>
                                        <td class="text-end">-</td>
                                    </tr>
                    `;
                    
                    // Ajouter les URLs qui se cannibalisent
                    cannibalizingUrls.forEach(url => {
                        // Trouver la paire de similarité entre cette URL et l'URL de référence
                        const pair = group.pairs.find(p => 
                            (p.url1 === referenceUrl.url && p.url2 === url.url) || 
                            (p.url1 === url.url && p.url2 === referenceUrl.url)
                        );
                        
                        const similarity = pair ? pair.similarity : 0;
                        let similarityClass = '';
                        let riskText = '';
                        
                        if (similarity >= 0.9) {
                            similarityClass = 'high-similarity';
                            riskText = 'Risque élevé';
                        } else if (similarity >= 0.8) {
                            similarityClass = 'medium-similarity';
                            riskText = 'Risque moyen';
                        } else {
                            similarityClass = 'low-similarity';
                            riskText = 'Risque faible';
                        }
                        
                        // Formater l'affichage de la similarité selon l'option choisie
                        let similarityDisplay = '';
                        if (showExactSimilarityValue) {
                            // Afficher le score exact avec 4 décimales
                            similarityDisplay = similarity.toFixed(4);
                        } else {
                            // Afficher en pourcentage arrondi
                            similarityDisplay = (similarity * 100).toFixed(0) + '%';
                        }
                        
                        tableHTML += `
                            <tr>
                                <td>
                                    <div class="url-cell">
                                        <a href="${url.url}" target="_blank" class="url-link">${url.url}</a>
                                        <button class="btn btn-sm btn-outline-secondary copy-url-btn" data-url="${url.url}">
                                            <i class="bi bi-clipboard"></i>
                                        </button>
                                    </div>
                                </td>
                                <td class="text-end">${parseFloat(url.position) ? parseFloat(url.position).toFixed(1) : '-'}</td>
                                <td class="text-end">${url.clicks || 0}</td>
                                <td class="text-end">${url.impressions || 0}</td>
                                <td class="text-end">${url.ctr ? (url.ctr * 100).toFixed(2) + '%' : '-'}</td>
                                <td class="text-end similarity-cell">
                                    <span class="similarity-value ${similarityClass}">
                                        ${similarityDisplay}
                                    </span>
                                    <span class="risk-label ${similarityClass}">
                                        ${riskText}
                                    </span>
                                </td>
                            </tr>
                        `;
                    });
                    
                    tableHTML += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    referenceSection.innerHTML = tableHTML;
                    keywordSection.appendChild(referenceSection);
                } else {
                    const noResultsDiv = document.createElement('div');
                    noResultsDiv.className = 'alert alert-info';
                    noResultsDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>Aucune URL ne se cannibalise avec l\'URL de référence.';
                    keywordSection.appendChild(noResultsDiv);
                }
                
            } else {
                const noResultsDiv = document.createElement('div');
                noResultsDiv.className = 'alert alert-info';
                noResultsDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>Aucune paire de cannibalisation trouvée pour ce mot-clé.';
                keywordSection.appendChild(noResultsDiv);
            }
            
            container.appendChild(keywordSection);
        });
        
        // Ajouter les écouteurs d'événements pour les boutons de copie d'URL
        document.querySelectorAll('.copy-url-btn').forEach(button => {
            button.addEventListener('click', function() {
                const url = this.getAttribute('data-url');
                navigator.clipboard.writeText(url).then(() => {
                    // Changer temporairement l'icône pour indiquer que la copie a réussi
                    const icon = this.querySelector('i');
                    icon.classList.remove('bi-clipboard');
                    icon.classList.add('bi-clipboard-check');
                    
                    // Remettre l'icône d'origine après 1.5 secondes
                    setTimeout(() => {
                        icon.classList.remove('bi-clipboard-check');
                        icon.classList.add('bi-clipboard');
                    }, 1500);
                });
            });
        });
    }
    
    // Appliquer les filtres
    applyFiltersBtn.addEventListener('click', function() {
        if (!analysisData) return;
        
        applyFiltersAndSort(analysisData.groups);
    });
    
    // Réinitialiser les filtres
    resetFiltersBtn.addEventListener('click', function() {
        keywordFilter.value = '';
        keywordExcludeFilter.value = '';
        useRegex.checked = false;
        similarityMinFilter.value = thresholdUsedSpan.textContent;
        similarityMinValue.textContent = thresholdUsedSpan.textContent;
        minUrlsFilter.value = '2';
        sortBySelect.value = 'similarity_desc';
        minClicksFilter.value = '0';
        minImpressionsFilter.value = '0';
        
        // Réappliquer les filtres avec les valeurs réinitialisées
        if (analysisData) {
            applyFiltersAndSort(analysisData.groups);
        }
    });
    
    // Exporter le rapport
    exportReportBtn.addEventListener('click', function() {
        if (!analysisData) return;
        
        const reportData = {
            title: 'Rapport de Cannibalisation SEO',
            date: reportDateSpan.textContent,
            total_keywords: totalKeywordsSpan.textContent,
            similarity_threshold: thresholdUsedSpan.textContent,
            groups: []
        };
        
        // Récupérer les groupes actuellement affichés
        const groupElements = keywordGroups.querySelectorAll('.keyword-group');
        groupElements.forEach(groupElement => {
            const keyword = groupElement.querySelector('.keyword-title').textContent;
            const group = analysisData.groups.find(g => g.keyword === keyword);
            if (group) {
                reportData.groups.push(group);
            }
        });
        
        // Convertir en JSON et télécharger
        const dataStr = JSON.stringify(reportData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `rapport-cannibalisation-${formatDateForFilename(new Date())}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    });
    
    // Exporter le rapport en HTML
    exportHtmlBtn.addEventListener('click', async function() {
        if (!analysisData) return;
        
        try {
            // Récupérer le CSS
            const cssResponse = await fetch('/static/css/styles.css');
            const cssText = await cssResponse.text();
            
            // Récupérer Bootstrap CSS
            const bootstrapCssResponse = await fetch('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css');
            const bootstrapCssText = await bootstrapCssResponse.text();
            
            // Récupérer Bootstrap Icons CSS
            const bootstrapIconsCssResponse = await fetch('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css');
            const bootstrapIconsCssText = await bootstrapIconsCssResponse.text();
            
            // Créer une copie des données d'analyse pour l'export
            const exportData = JSON.parse(JSON.stringify(analysisData));
            
            // Créer le HTML complet avec CSS et JavaScript intégrés
            const htmlTemplate = `
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Cannibalisation SEO - ${new Date().toLocaleDateString()}</title>
    <style>
        /* Bootstrap CSS */
        ${bootstrapCssText}
        
        /* Bootstrap Icons CSS */
        ${bootstrapIconsCssText}
        
        /* Styles personnalisés */
        ${cssText}
        
        /* Styles supplémentaires pour l'export */
        body {
            padding: 20px;
        }
        .export-info {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .filters-section {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .keyword-group {
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h1 class="mb-4">Rapport de Cannibalisation SEO</h1>
                
                <div class="export-info">
                    <div class="row">
                        <div class="col-md-4">
                            <strong>Date du rapport:</strong> ${reportDateSpan.textContent}
                        </div>
                        <div class="col-md-4">
                            <strong>Seuil de similarité:</strong> ${thresholdUsedSpan.textContent}
                        </div>
                        <div class="col-md-4">
                            <strong>Mots-clés analysés:</strong> ${totalKeywordsSpan.textContent}
                        </div>
                    </div>
                </div>
                
                <div class="filters-section">
                    <h4>Filtres</h4>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="keywordFilter" class="form-label">Mot-clé contient:</label>
                            <input type="text" class="form-control" id="keywordFilter" placeholder="Rechercher un mot-clé...">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="keywordExcludeFilter" class="form-label">Exclure mot-clé:</label>
                            <input type="text" class="form-control" id="keywordExcludeFilter" placeholder="Mots-clés à exclure (séparés par des virgules)">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="useRegex" class="form-check-label">
                                <input type="checkbox" class="form-check-input me-2" id="useRegex">
                                Utiliser des expressions régulières
                            </label>
                            <div class="form-text">Active les regex pour les filtres d'inclusion et d'exclusion</div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="similarityMinFilter" class="form-label">Similarité minimum:</label>
                            <div class="d-flex align-items-center">
                                <input type="range" class="form-range flex-grow-1 me-2" id="similarityMinFilter" min="0.5" max="1.0" step="0.1" value="${thresholdUsedSpan.textContent}">
                                <span id="similarityMinValue">${thresholdUsedSpan.textContent}</span>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="minUrlsFilter" class="form-label">Nombre minimum de URLs:</label>
                            <input type="number" class="form-control" id="minUrlsFilter" min="2" value="2">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="minClicksFilter" class="form-label">Nombre minimum de clics:</label>
                            <input type="number" class="form-control" id="minClicksFilter" min="0" value="0">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="minImpressionsFilter" class="form-label">Nombre minimum d'impressions:</label>
                            <input type="number" class="form-control" id="minImpressionsFilter" min="0" value="0">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="sortBy" class="form-label">Trier par:</label>
                            <select class="form-select" id="sortBy">
                                <option value="similarity_desc">Similarité (décroissante)</option>
                                <option value="similarity_asc">Similarité (croissante)</option>
                                <option value="urls_desc">Nombre d'URLs (décroissant)</option>
                                <option value="urls_asc">Nombre d'URLs (croissant)</option>
                                <option value="clicks_desc">Clics (décroissants)</option>
                                <option value="clicks_asc">Clics (croissants)</option>
                            </select>
                        </div>
                        <div class="col-md-4 d-flex align-items-end">
                            <button id="applyFiltersBtn" class="btn btn-primary me-2">
                                <i class="bi bi-funnel-fill"></i> Appliquer les filtres
                            </button>
                            <button id="resetFiltersBtn" class="btn btn-outline-secondary">
                                <i class="bi bi-arrow-counterclockwise"></i> Réinitialiser
                            </button>
                        </div>
                    </div>
                </div>
                
                <div id="resultsInfo" class="d-flex justify-content-between align-items-center mb-3">
                    <h3>Résultats</h3>
                    <span id="resultsCount" class="badge bg-light text-dark me-2">${resultsCountSpan.textContent}</span>
                </div>
                
                <div id="keywordGroups">
                    ${document.getElementById('keywordGroups').innerHTML}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Données d'analyse
        const analysisData = ${JSON.stringify(exportData)};
        
        // Éléments du DOM
        const keywordGroups = document.getElementById('keywordGroups');
        const thresholdUsedSpan = document.querySelector('strong:contains("Seuil de similarité:")').nextElementSibling;
        const totalKeywordsSpan = document.querySelector('strong:contains("Mots-clés analysés:")').nextElementSibling;
        const reportDateSpan = document.querySelector('strong:contains("Date du rapport:")').nextElementSibling;
        const resultsCountSpan = document.getElementById('resultsCount');
        
        // Filtres
        const keywordFilter = document.getElementById('keywordFilter');
        const keywordExcludeFilter = document.getElementById('keywordExcludeFilter');
        const useRegex = document.getElementById('useRegex');
        const showExactSimilarity = document.getElementById('showExactSimilarity');
        const minUrlsFilter = document.getElementById('minUrlsFilter');
        const sortBySelect = document.getElementById('sortBy');
        const applyFiltersBtn = document.getElementById('applyFiltersBtn');
        const resetFiltersBtn = document.getElementById('resetFiltersBtn');
        const similarityMinFilter = document.getElementById('similarityMinFilter');
        const similarityMinValue = document.getElementById('similarityMinValue');
        const minClicksFilter = document.getElementById('minClicksFilter');
        const minImpressionsFilter = document.getElementById('minImpressionsFilter');
        
        // Initialiser les écouteurs d'événements
        document.addEventListener('DOMContentLoaded', function() {
            // Slider de similarité
            similarityMinFilter.addEventListener('input', function() {
                similarityMinValue.textContent = this.value;
            });
            
            // Appliquer les filtres
            applyFiltersBtn.addEventListener('click', function() {
                if (!analysisData) return;
                
                applyFiltersAndSort(analysisData.groups);
            });
            
            // Réinitialiser les filtres
            resetFiltersBtn.addEventListener('click', function() {
                keywordFilter.value = '';
                keywordExcludeFilter.value = '';
                useRegex.checked = false;
                similarityMinFilter.value = ${thresholdUsedSpan.textContent};
                similarityMinValue.textContent = ${thresholdUsedSpan.textContent};
                minUrlsFilter.value = '2';
                sortBySelect.value = 'similarity_desc';
                minClicksFilter.value = '0';
                minImpressionsFilter.value = '0';
                
                // Réappliquer les filtres avec les valeurs réinitialisées
                if (analysisData) {
                    applyFiltersAndSort(analysisData.groups);
                }
            });
            
            // Initialiser les boutons de copie d'URL
            document.querySelectorAll('.copy-url-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const url = this.getAttribute('data-url');
                    navigator.clipboard.writeText(url).then(() => {
                        // Changer temporairement l'icône pour indiquer que la copie a réussi
                        const icon = this.querySelector('i');
                        icon.classList.remove('bi-clipboard');
                        icon.classList.add('bi-clipboard-check');
                        
                        // Remettre l'icône d'origine après 1.5 secondes
                        setTimeout(() => {
                            icon.classList.remove('bi-clipboard-check');
                            icon.classList.add('bi-clipboard');
                        }, 1500);
                    });
                });
            });
        });
        
        // Fonction pour appliquer les filtres et le tri
        function applyFiltersAndSort(groups) {
            const keywordFilterValue = document.getElementById('keywordFilter').value.trim();
            const keywordExcludeValue = document.getElementById('keywordExcludeFilter').value.trim();
            const useRegex = document.getElementById('useRegex').checked;
            const similarityThreshold = parseFloat(document.getElementById('similarityMinFilter').value);
            const minClicksFilterValue = parseInt(document.getElementById('minClicksFilter').value) || 0;
            const minImpressionsFilterValue = parseInt(document.getElementById('minImpressionsFilter').value) || 0;
            const minUrlsFilterValue = parseInt(document.getElementById('minUrlsFilter').value) || 2;
            const sortByValue = document.getElementById('sortBy').value;
            
            // Préparer les expressions régulières ou les termes de recherche
            let includeRegex = null;
            let excludeTerms = [];
            let excludeRegexes = [];
            
            if (useRegex && keywordFilterValue) {
                try {
                    includeRegex = new RegExp(keywordFilterValue, 'i');
                } catch (e) {
                    console.error('Expression régulière d\\'inclusion invalide:', e);
                    alert('Expression régulière d\\'inclusion invalide: ' + e.message);
                    return;
                }
            }
            
            if (keywordExcludeValue) {
                if (useRegex) {
                    // Traiter chaque expression régulière séparément
                    const regexStrings = keywordExcludeValue.split(',').map(s => s.trim()).filter(s => s);
                    for (const regexStr of regexStrings) {
                        try {
                            excludeRegexes.push(new RegExp(regexStr, 'i'));
                        } catch (e) {
                            console.error('Expression régulière d\\'exclusion invalide:', e);
                            alert('Expression régulière d\\'exclusion invalide: ' + e.message);
                            return;
                        }
                    }
                } else {
                    // Utiliser des termes simples pour l'exclusion
                    excludeTerms = keywordExcludeValue.split(',').map(s => s.trim().toLowerCase()).filter(s => s);
                }
            }
            
            // Filtrer les groupes
            let filteredGroups = groups.filter(group => {
                const keyword = group.keyword;
                
                // Filtrer par mot-clé (inclusion)
                if (keywordFilterValue) {
                    if (useRegex) {
                        if (!includeRegex.test(keyword)) {
                            return false;
                        }
                    } else if (!keyword.toLowerCase().includes(keywordFilterValue.toLowerCase())) {
                        return false;
                    }
                }
                
                // Filtrer par mot-clé (exclusion)
                if (useRegex) {
                    for (const regex of excludeRegexes) {
                        if (regex.test(keyword)) {
                            return false;
                        }
                    }
                } else {
                    for (const term of excludeTerms) {
                        if (keyword.toLowerCase().includes(term)) {
                            return false;
                        }
                    }
                }
                
                // Filtrer les URLs par clics et impressions
                const filteredUrls = group.urls.filter(url => {
                    return (url.clicks || 0) >= minClicksFilterValue && 
                           (url.impressions || 0) >= minImpressionsFilterValue;
                });
                
                // Si aucune URL ne passe le filtre, exclure le groupe
                if (filteredUrls.length === 0) {
                    return false;
                }
                
                // Vérifier le nombre minimum d'URLs
                if (filteredUrls.length < minUrlsFilterValue) {
                    return false;
                }
                
                // Mettre à jour les URLs du groupe
                group.urls = filteredUrls;
                group.url_count = filteredUrls.length;
                
                // Filtrer les paires pour ne garder que celles dont les deux URLs passent le filtre
                const filteredUrlsSet = new Set(filteredUrls.map(u => u.url));
                const filteredPairs = group.pairs.filter(pair => {
                    return filteredUrlsSet.has(pair.url1) && filteredUrlsSet.has(pair.url2) && 
                           pair.similarity >= similarityThreshold;
                });
                
                // Si aucune paire ne passe le filtre, exclure le groupe
                if (filteredPairs.length === 0) {
                    return false;
                }
                
                // Mettre à jour les paires du groupe
                group.pairs = filteredPairs;
                
                return true;
            });
            
            // Trier les groupes
            filteredGroups = sortGroups(filteredGroups, sortByValue);
            
            // Mettre à jour le compteur de résultats
            resultsCountSpan.textContent = \`\${filteredGroups.length} mots-clés\`;
            
            // Afficher les groupes filtrés
            displayKeywordGroups(filteredGroups);
        }
        
        // Fonction pour trier les groupes
        function sortGroups(groups, sortBy) {
            switch(sortBy) {
                case 'similarity_desc':
                    return groups.sort((a, b) => {
                        const maxSimA = Math.max(...a.pairs.map(p => p.similarity));
                        const maxSimB = Math.max(...b.pairs.map(p => p.similarity));
                        return maxSimB - maxSimA;
                    });
                case 'similarity_asc':
                    return groups.sort((a, b) => {
                        const maxSimA = Math.max(...a.pairs.map(p => p.similarity));
                        const maxSimB = Math.max(...b.pairs.map(p => p.similarity));
                        return maxSimA - maxSimB;
                    });
                case 'urls_desc':
                    return groups.sort((a, b) => b.url_count - a.url_count);
                case 'urls_asc':
                    return groups.sort((a, b) => a.url_count - b.url_count);
                case 'clicks_desc':
                    return groups.sort((a, b) => {
                        const totalClicksA = a.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                        const totalClicksB = b.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                        return totalClicksB - totalClicksA;
                    });
                case 'clicks_asc':
                    return groups.sort((a, b) => {
                        const totalClicksA = a.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                        const totalClicksB = b.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                        return totalClicksA - totalClicksB;
                    });
                default:
                    return groups;
            }
        }
        
        // Fonction pour afficher les groupes de mots-clés
        function displayKeywordGroups(groups) {
            const container = document.getElementById('keywordGroups');
            const showExactSimilarityValue = document.getElementById('showExactSimilarity').checked;
            container.innerHTML = '';
            
            if (groups.length === 0) {
                container.innerHTML = '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>Aucun résultat ne correspond à vos critères de filtrage.</div>';
                return;
            }
            
            groups.forEach(group => {
                const keywordSection = document.createElement('div');
                keywordSection.className = 'keyword-group';
                
                const keywordHeader = document.createElement('div');
                keywordHeader.className = 'keyword-header';
                keywordHeader.innerHTML = \`
                    <h4 class="keyword-title">\${group.keyword}</h4>
                    <div class="keyword-stats">
                        <span class="badge bg-primary">\${group.url_count} URLs</span>
                    </div>
                \`;
                
                keywordSection.appendChild(keywordHeader);
                
                // Trouver l'URL avec le plus de clics pour la prendre comme référence
                if (group.urls.length > 0) {
                    const referenceUrl = [...group.urls].sort((a, b) => (b.clicks || 0) - (a.clicks || 0))[0];
                    
                    // Créer la section pour l'URL de référence
                    const referenceSection = document.createElement('div');
                    referenceSection.className = 'reference-url-section mb-3';
                    
                    // Déterminer les URLs qui se cannibalisent avec l'URL de référence
                    const cannibalizingUrls = group.urls.filter(url => url.url !== referenceUrl.url);
                    
                    if (cannibalizingUrls.length > 0) {
                        // Créer le tableau pour l'URL de référence et les URLs qui se cannibalisent
                        let tableHTML = \`
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th style="width: 50%">URL</th>
                                            <th class="text-end">Position</th>
                                            <th class="text-end">Clics</th>
                                            <th class="text-end">Impressions</th>
                                            <th class="text-end">CTR</th>
                                            <th class="text-end">Similarité</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr class="reference-url">
                                            <td>
                                                <div class="d-flex align-items-center">
                                                    <span class="badge bg-success me-2">Référence</span>
                                                    <div class="url-cell">
                                                        <a href="\${referenceUrl.url}" target="_blank" class="url-link">\${referenceUrl.url}</a>
                                                        <button class="btn btn-sm btn-outline-secondary copy-url-btn" data-url="\${referenceUrl.url}">
                                                            <i class="bi bi-clipboard"></i>
                                                        </button>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="text-end">\${parseFloat(referenceUrl.position) ? parseFloat(referenceUrl.position).toFixed(1) : '-'}</td>
                                            <td class="text-end">\${referenceUrl.clicks || 0}</td>
                                            <td class="text-end">\${referenceUrl.impressions || 0}</td>
                                            <td class="text-end">\${referenceUrl.ctr ? (referenceUrl.ctr * 100).toFixed(2) + '%' : '-'}</td>
                                            <td class="text-end">-</td>
                                        </tr>
                        \`;
                        
                        // Ajouter les URLs qui se cannibalisent
                        cannibalizingUrls.forEach(url => {
                            // Trouver la paire de similarité entre cette URL et l'URL de référence
                            const pair = group.pairs.find(p => 
                                (p.url1 === referenceUrl.url && p.url2 === url.url) || 
                                (p.url1 === url.url && p.url2 === referenceUrl.url)
                            );
                            
                            const similarity = pair ? pair.similarity : 0;
                            let similarityClass = '';
                            let riskText = '';
                            
                            if (similarity >= 0.9) {
                                similarityClass = 'high-similarity';
                                riskText = 'Risque élevé';
                            } else if (similarity >= 0.8) {
                                similarityClass = 'medium-similarity';
                                riskText = 'Risque moyen';
                            } else {
                                similarityClass = 'low-similarity';
                                riskText = 'Risque faible';
                            }
                            
                            // Formater l'affichage de la similarité selon l'option choisie
                            let similarityDisplay = '';
                            if (showExactSimilarityValue) {
                                // Afficher le score exact avec 4 décimales
                                similarityDisplay = similarity.toFixed(4);
                            } else {
                                // Afficher en pourcentage arrondi
                                similarityDisplay = (similarity * 100).toFixed(0) + '%';
                            }
                            
                            tableHTML += \`
                                <tr>
                                    <td>
                                        <div class="url-cell">
                                            <a href="\${url.url}" target="_blank" class="url-link">\${url.url}</a>
                                            <button class="btn btn-sm btn-outline-secondary copy-url-btn" data-url="\${url.url}">
                                                <i class="bi bi-clipboard"></i>
                                            </button>
                                        </div>
                                    </td>
                                    <td class="text-end">\${parseFloat(url.position) ? parseFloat(url.position).toFixed(1) : '-'}</td>
                                    <td class="text-end">\${url.clicks || 0}</td>
                                    <td class="text-end">\${url.impressions || 0}</td>
                                    <td class="text-end">\${url.ctr ? (url.ctr * 100).toFixed(2) + '%' : '-'}</td>
                                    <td class="text-end similarity-cell">
                                        <span class="similarity-value \${similarityClass}">
                                            \${similarityDisplay}
                                        </span>
                                        <span class="risk-label \${similarityClass}">
                                            \${riskText}
                                        </span>
                                    </td>
                                </tr>
                            \`;
                        });
                        
                        tableHTML += \`
                                    </tbody>
                                </table>
                            </div>
                        \`;
                        
                        referenceSection.innerHTML = tableHTML;
                        keywordSection.appendChild(referenceSection);
                    } else {
                        const noResultsDiv = document.createElement('div');
                        noResultsDiv.className = 'alert alert-info';
                        noResultsDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>Aucune URL ne se cannibalise avec l\\'URL de référence.';
                        keywordSection.appendChild(noResultsDiv);
                    }
                    
                } else {
                    const noResultsDiv = document.createElement('div');
                    noResultsDiv.className = 'alert alert-info';
                    noResultsDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>Aucune paire de cannibalisation trouvée pour ce mot-clé.';
                    keywordSection.appendChild(noResultsDiv);
                }
                
                container.appendChild(keywordSection);
            });
            
            // Ajouter les écouteurs d'événements pour les boutons de copie d'URL
            document.querySelectorAll('.copy-url-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const url = this.getAttribute('data-url');
                    navigator.clipboard.writeText(url).then(() => {
                        // Changer temporairement l'icône pour indiquer que la copie a réussi
                        const icon = this.querySelector('i');
                        icon.classList.remove('bi-clipboard');
                        icon.classList.add('bi-clipboard-check');
                        
                        // Remettre l'icône d'origine après 1.5 secondes
                        setTimeout(() => {
                            icon.classList.remove('bi-clipboard-check');
                            icon.classList.add('bi-clipboard');
                        }, 1500);
                    });
                });
            });
        }
        
        // Polyfill pour jQuery-like :contains selector
        if (!Element.prototype.matches) {
            Element.prototype.matches = Element.prototype.msMatchesSelector || Element.prototype.webkitMatchesSelector;
        }
        
        if (!document.querySelector('strong:contains("Seuil de similarité:")')) {
            document.querySelectorAll('strong').forEach(el => {
                if (el.textContent.includes('Seuil de similarité:')) {
                    el.setAttribute('data-contains', 'true');
                }
            });
        }
        
        // Initialiser l'affichage
        applyFiltersAndSort(analysisData.groups);
    </script>
</body>
</html>
            `;
            
            // Télécharger le rapport en HTML
            const exportFileDefaultName = `rapport-cannibalisation-${formatDateForFilename(new Date())}.html`;
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', `data:text/html;charset=utf-8,${encodeURIComponent(htmlTemplate)}`);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
            
        } catch (error) {
            console.error('Erreur lors de l\'export HTML:', error);
            alert('Erreur lors de l\'export HTML. Veuillez réessayer.');
        }
    });
    
    // Fonctions utilitaires
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    function formatDateForFilename(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}${month}${day}`;
    }
    
    function truncateUrl(url) {
        // Extraire le domaine et le chemin
        try {
            const urlObj = new URL(url);
            const domain = urlObj.hostname;
            const path = urlObj.pathname;
            
            // Si l'URL est courte, l'afficher en entier
            if (url.length < 60) {
                return url;
            }
            
            // Sinon, formater l'URL pour qu'elle soit plus lisible
            // Conserver le domaine complet et tronquer le chemin si nécessaire
            const pathParts = path.split('/').filter(part => part.length > 0);
            let displayPath = '';
            
            if (pathParts.length > 0) {
                // Afficher au moins le premier et le dernier segment du chemin
                if (pathParts.length <= 2) {
                    displayPath = path;
                } else {
                    // Pour les chemins plus longs, afficher le début et la fin
                    displayPath = '/' + pathParts[0] + '/.../' + pathParts[pathParts.length - 1];
                }
            }
            
            return domain + displayPath + (urlObj.search || '');
        } catch (e) {
            // En cas d'erreur, revenir à la méthode simple
            const maxLength = 60;
            return url.length > maxLength ? url.substring(0, maxLength) + '...' : url;
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Fonction utilitaire pour déterminer la classe CSS du badge de risque
    function getRiskClass(risk) {
        switch (risk.toLowerCase()) {
            case 'high':
                return 'high';
            case 'medium':
                return 'medium';
            case 'low':
                return 'low';
            default:
                return 'secondary';
        }
    }
    
    function getBadgeClass(risk) {
        switch(risk) {
            case 'ÉLEVÉ': return 'bg-danger';
            case 'MOYEN': return 'bg-warning text-dark';
            case 'FAIBLE': return 'bg-info text-dark';
            default: return 'bg-success';
        }
    }
    
    function sortGroups(groups, sortBy) {
        switch(sortBy) {
            case 'similarity_desc':
                return groups.sort((a, b) => {
                    const maxSimA = Math.max(...a.pairs.map(p => p.similarity));
                    const maxSimB = Math.max(...b.pairs.map(p => p.similarity));
                    return maxSimB - maxSimA;
                });
            case 'similarity_asc':
                return groups.sort((a, b) => {
                    const maxSimA = Math.max(...a.pairs.map(p => p.similarity));
                    const maxSimB = Math.max(...b.pairs.map(p => p.similarity));
                    return maxSimA - maxSimB;
                });
            case 'urls_desc':
                return groups.sort((a, b) => b.url_count - a.url_count);
            case 'urls_asc':
                return groups.sort((a, b) => a.url_count - b.url_count);
            case 'clicks_desc':
                return groups.sort((a, b) => {
                    const totalClicksA = a.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                    const totalClicksB = b.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                    return totalClicksB - totalClicksA;
                });
            case 'clicks_asc':
                return groups.sort((a, b) => {
                    const totalClicksA = a.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                    const totalClicksB = b.urls.reduce((sum, url) => sum + (url.clicks || 0), 0);
                    return totalClicksA - totalClicksB;
                });
            default:
                return groups;
        }
    }
    
    function showError(message) {
        const errorElement = document.getElementById('error');
        errorElement.textContent = message;
        errorElement.classList.remove('d-none');
    }
    
    function hideLoading() {
        const loadingElement = document.getElementById('loading');
        loadingElement.classList.add('d-none');
    }
    
    function showLoading(message) {
        const loadingElement = document.getElementById('loading');
        loadingElement.textContent = message;
        loadingElement.classList.remove('d-none');
    }
});
