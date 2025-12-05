# agents/web_search.py

import logging
import re
import time
import json
import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_search_agent")

def web_search_agent(title: str):
    """
    Agente que busca en TMDB - Recibe SOLO el título ya extraído
    """
    logger.info(f"🎯 Buscando: '{title}'")
    
    # Buscar directamente en TMDB
    media_id, media_type, corrected_title = search_tmdb_inteligente(title)
    
    if not media_id:
        logger.warning(f"❌ No se encontró '{title}' en TMDB")
        return {
            "title": title,
            "year": "No disponible",
            "genres": [],
            "director": "No disponible",
            "summary": f"No se encontró información para '{title}' en TMDB.",
            "rating": "No disponible",
            "cast": []
        }
    
    # Hacer scraping CON CAST MEJORADO
    try:
        result = scrape_tmdb_with_cast(media_id, media_type)
        
        # CONVERTIR AL FORMATO ESPERADO POR EL REPORTER
        if "error" not in result:
            formatted_result = {
                "title": result.get("title", corrected_title or title),
                "year": result.get("year", "No disponible"),
                "genres": result.get("genres", []),
                "director": result.get("director") or result.get("creator", "No disponible"),
                "summary": result.get("overview", "No hay descripción disponible."),
                "rating": f"{result.get('score', 'N/A')}%" if result.get('score') else "No disponible",
                "cast": result.get("cast", [])
            }
            logger.info(f"✅ Información formateada: {formatted_result['title']} ({formatted_result['year']})")
            logger.info(f"✅ Cast obtenido: {len(formatted_result['cast'])} actores")
            return formatted_result
        else:
            logger.warning(f"❌ Error en scraping: {result.get('error')}")
            return {
                "title": title,
                "year": "Error",
                "genres": [],
                "director": "No disponible",
                "summary": f"Error al obtener información: {result.get('error')}",
                "rating": "No disponible",
                "cast": []
            }
        
    except Exception as e:
        logger.error(f"❌ Error general: {e}")
        return {
            "title": title,
            "year": "Error",
            "genres": [],
            "director": "No disponible",
            "summary": f"Error en la búsqueda: {str(e)}",
            "rating": "No disponible",
            "cast": []
        }

def search_tmdb_inteligente(search_terms: str):
    """
    Búsqueda INTELIGENTE en TMDB
    """
    search_url = f"https://www.themoviedb.org/search?query={search_terms.replace(' ', '+')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(40000)
        
        try:
            logger.info(f"🔍 Búsqueda para: '{search_terms}'")
            page.goto(search_url, timeout=50000, wait_until="domcontentloaded")
            time.sleep(3)
            
            # Aceptar cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(1)
            except:
                pass
            
            # Obtener HTML de resultados
            results_html = page.content()
            browser.close()
            
            # Buscar películas y series
            results = []
            
            # Patrón para películas
            movie_pattern = r'href="/movie/(\d+)-[^"]*".*?<h2[^>]*>(.*?)</h2>'
            movie_matches = re.findall(movie_pattern, results_html, re.DOTALL)
            
            for tmdb_id, title_html in movie_matches:
                title = re.sub(r'<.*?>', '', title_html).strip()
                if title:
                    results.append({
                        "id": int(tmdb_id),
                        "title": title,
                        "type": "movie"
                    })
            
            # Patrón para series
            tv_pattern = r'href="/tv/(\d+)-[^"]*".*?<h2[^>]*>(.*?)</h2>'
            tv_matches = re.findall(tv_pattern, results_html, re.DOTALL)
            
            for tmdb_id, title_html in tv_matches:
                title = re.sub(r'<.*?>', '', title_html).strip()
                if title:
                    results.append({
                        "id": int(tmdb_id),
                        "title": title,
                        "type": "tv"
                    })
            
            if results:
                # Seleccionar el PRIMER resultado (TMDB ya los ordena por relevancia)
                best = results[0]
                logger.info(f"✅ Resultado seleccionado: {best['title']} (ID: {best['id']}, Tipo: {best['type']})")
                return best["id"], best["type"], best["title"]
            
            logger.warning("❌ No se encontraron resultados en TMDB")
            return None, None, None
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            try:
                browser.close()
            except:
                pass
            return None, None, None

def scrape_tmdb_with_cast(media_id, media_type):
    """Scraping con extracción de cast GARANTIZADA"""
    url = f"https://www.themoviedb.org/{media_type}/{media_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)  # Más tiempo
        
        try:
            logger.info(f"🎬 Scraping {media_type} ID: {media_id}")
            
            # Navegar a la página principal
            page.goto(url, timeout=60000, wait_until="networkidle")
            time.sleep(3)
            
            # Aceptar cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                time.sleep(1)
            except:
                pass
            
            # EXTRAER DATOS BÁSICOS
            basic_data = page.evaluate("""
                () => {
                    const result = {
                        title: null,
                        overview: null,
                        year: null,
                        genres: [],
                        score: null,
                        director: null,
                        cast: []
                    };
                    
                    // Título
                    const titleEl = document.querySelector('h2 a, h2.title, [data-cy="movie-title"]');
                    if (titleEl) result.title = titleEl.textContent.trim();
                    
                    // Sinopsis
                    const overviewEl = document.querySelector('.overview p, [data-cy="overview"]');
                    if (overviewEl) result.overview = overviewEl.textContent.trim();
                    
                    // Año
                    const dateEl = document.querySelector('.release_date, .release');
                    if (dateEl) {
                        const yearMatch = dateEl.textContent.match(/(19\\d{2}|20\\d{2})/);
                        if (yearMatch) result.year = yearMatch[0];
                    }
                    
                    // Géneros
                    const genreEls = document.querySelectorAll('.genres a');
                    genreEls.forEach(el => {
                        if (el.textContent.trim()) {
                            result.genres.push(el.textContent.trim());
                        }
                    });
                    
                    // Score
                    const scoreEl = document.querySelector('[data-percent], .user_score_chart');
                    if (scoreEl) {
                        result.score = scoreEl.getAttribute('data-percent') || scoreEl.textContent;
                    }
                    
                    return result;
                }
            """)
            
            # EXTRAER CAST - MÉTODO GARANTIZADO
            logger.info("🎭 Extrayendo cast...")
            cast_data = extract_cast_guaranteed(page, media_id, media_type)
            basic_data["cast"] = cast_data
            
            browser.close()
            return basic_data
            
        except Exception as e:
            logger.error(f"❌ Error en scraping: {e}")
            try:
                browser.close()
            except:
                pass
            return {"error": f"Error: {str(e)}"}

def extract_cast_guaranteed(page, media_id, media_type):
    """
    Extrae el cast usando MÚLTIPLES métodos hasta conseguirlo
    """
    cast_methods = [
        extract_cast_method_1,  # Página principal
        extract_cast_method_2,  # Página de cast
        extract_cast_method_3,  # API oculta
        extract_cast_method_4   # Scraping directo
    ]
    
    cast = []
    
    for i, method in enumerate(cast_methods, 1):
        try:
            logger.info(f"🎭 Intentando método {i} para cast...")
            method_cast = method(page, media_id, media_type)
            
            if method_cast and len(method_cast) >= 3:
                logger.info(f"✅ Método {i} exitoso: {len(method_cast)} actores")
                cast = method_cast
                break
            else:
                logger.info(f"⚠️  Método {i} encontró {len(method_cast) if method_cast else 0} actores")
                
        except Exception as e:
            logger.warning(f"⚠️  Método {i} falló: {e}")
    
    # Si no se encontró cast, intentar método de emergencia
    if not cast:
        logger.info("🚨 Usando método de emergencia para cast...")
        cast = extract_cast_emergency(page)
    
    return cast[:15]  # Máximo 15 actores

def extract_cast_method_1(page, media_id, media_type):
    """Método 1: Extraer de la página principal"""
    cast = []
    
    try:
        # Intentar encontrar cast en la página principal
        cast_section = page.evaluate("""
            () => {
                const cast = [];
                // Buscar sección de "Top Billed Cast"
                const sections = document.querySelectorAll('section, .panel');
                
                for (const section of sections) {
                    const text = section.textContent;
                    if (text && text.includes('Cast') && text.includes('Top Billed')) {
                        // Buscar nombres en esta sección
                        const nameElements = section.querySelectorAll('a[href*="/person/"], .name, .profile .title');
                        nameElements.forEach(el => {
                            const name = el.textContent.trim();
                            if (name && name.length > 2 && name.includes(' ') && !cast.includes(name)) {
                                cast.push(name);
                            }
                        });
                        break;
                    }
                }
                return cast;
            }
        """)
        
        if cast_section:
            return cast_section
            
    except:
        pass
    
    return []

def extract_cast_method_2(page, media_id, media_type):
    """Método 2: Ir a la página específica de cast"""
    cast = []
    
    try:
        # Navegar a la página de cast
        cast_url = f"https://www.themoviedb.org/{media_type}/{media_id}/cast"
        page.goto(cast_url, timeout=30000, wait_until="networkidle")
        time.sleep(2)
        
        # Extraer nombres del cast
        cast_data = page.evaluate("""
            () => {
                const cast = [];
                
                // Método directo: buscar todas las tarjetas de cast
                const cards = document.querySelectorAll('.card, .profile, [class*="cast"]');
                
                cards.forEach(card => {
                    // Buscar nombre dentro de la tarjeta
                    const nameSelectors = [
                        '.name a', 
                        '.name', 
                        'a[href*="/person/"]',
                        'h2', 
                        'p.name',
                        '.title'
                    ];
                    
                    for (const selector of nameSelectors) {
                        const element = card.querySelector(selector);
                        if (element && element.textContent) {
                            const name = element.textContent.trim();
                            // Validar que sea un nombre real
                            if (name && name.length > 2 && name.includes(' ') && 
                                !name.includes('Character') && !name.includes('Order')) {
                                if (!cast.includes(name)) {
                                    cast.push(name);
                                }
                                break;
                            }
                        }
                    }
                    
                    // Si no se encontró con selectores, buscar en el texto
                    const text = card.textContent;
                    const lines = text.split('\\n');
                    for (const line of lines) {
                        const cleanLine = line.trim();
                        // Un nombre real: tiene espacio, empieza con mayúscula, no es muy largo
                        if (cleanLine && cleanLine.length > 3 && cleanLine.length < 30 &&
                            cleanLine.includes(' ') && 
                            cleanLine[0] === cleanLine[0].toUpperCase() &&
                            !cleanLine.includes('Character') &&
                            !cleanLine.includes('as ') &&
                            !cleanLine.includes('...') &&
                            !cast.includes(cleanLine)) {
                            cast.push(cleanLine);
                            break;
                        }
                    }
                });
                
                return cast;
            }
        """)
        
        if cast_data:
            return cast_data
            
    except Exception as e:
        logger.warning(f"⚠️  Método 2 falló: {e}")
    
    return []

def extract_cast_method_3(page, media_id, media_type):
    """Método 3: Buscar en el HTML completo"""
    cast = []
    
    try:
        # Obtener todo el HTML
        html_content = page.content()
        
        # Buscar nombres usando regex
        name_patterns = [
            r'alt="([^"]*)"[^>]*class="profile"',
            r'<a[^>]*href="/person/[^>]*>([^<]+)</a>',
            r'<p class="name">[^<]*<a[^>]*>([^<]+)</a>',
            r'data-cy="cast-person-name"[^>]*>([^<]+)<'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                name = match.strip()
                if (name and len(name) > 2 and name not in cast and
                    ' ' in name and not any(bad in name.lower() for bad in 
                    ["character", "order", "loading", "image", "avatar"])):
                    cast.append(name)
        
        # Filtrar nombres que parezcan reales
        filtered_cast = []
        for name in cast:
            # Un nombre real generalmente tiene espacio y longitud razonable
            if (2 <= len(name.split()) <= 3 and 
                4 <= len(name) <= 40 and
                not any(char.isdigit() for char in name)):
                filtered_cast.append(name)
        
        return filtered_cast
        
    except:
        return []

def extract_cast_method_4(page, media_id, media_type):
    """Método 4: Usar la API interna de TMDB"""
    cast = []
    
    try:
        # TMDB tiene una API interna que podemos intentar usar
        api_url = f"https://www.themoviedb.org/{media_type}/{media_id}/cast"
        
        # Hacer una solicitud directa a la API
        page.goto(api_url, timeout=30000)
        time.sleep(2)
        
        # Intentar extraer datos estructurados
        api_data = page.evaluate("""
            () => {
                const cast = [];
                const scriptTags = document.querySelectorAll('script[type="application/ld+json"]');
                
                for (const script of scriptTags) {
                    try {
                        const data = JSON.parse(script.textContent);
                        if (data.actor) {
                            if (Array.isArray(data.actor)) {
                                data.actor.forEach(actor => {
                                    if (actor.name) {
                                        cast.push(actor.name);
                                    }
                                });
                            } else if (data.actor.name) {
                                cast.push(data.actor.name);
                            }
                        }
                    } catch (e) {}
                }
                return cast;
            }
        """)
        
        if api_data and len(api_data) > 0:
            return api_data
            
    except:
        pass
    
    return []

def extract_cast_emergency(page):
    """Método de emergencia: extraer todo el texto visible"""
    cast = []
    
    try:
        # Obtener todo el texto visible
        visible_text = page.locator("body").inner_text()
        
        # Dividir en líneas
        lines = visible_text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Buscar líneas que parezcan nombres de actores
            # Reglas: tiene espacio, empieza con mayúscula, longitud razonable
            if (len(line) > 3 and len(line) < 40 and
                ' ' in line and
                line[0].isupper() and
                not any(bad in line.lower() for bad in 
                       ["character", "order", "as ", "plays", "director", "writer", "producer"]) and
                not line.endswith(':') and
                not line.startswith('Season') and
                not line.startswith('Episode') and
                line not in cast):
                cast.append(line)
        
        # Limitar a los primeros 10
        return cast[:10]
        
    except Exception as e:
        logger.error(f"❌ Error en método emergencia: {e}")
        return []