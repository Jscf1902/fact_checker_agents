# agents/web_search.py

import logging
import re
import time
import json
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_search_agent")

def web_search_agent(title: str):
    """
    Agente que busca en TMDB - Recibe SOLO el título ya extraído
    """
    logger.info(f"🎯 Buscando: '{title}'")
    
    # Buscar directamente en TMDB
    media_id, media_type = search_tmdb_online(title)
    
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
    
    # Hacer scraping
    try:
        result = scrape_tmdb_with_javascript(media_id, media_type)
        
        # CONVERTIR AL FORMATO ESPERADO POR EL REPORTER
        if "error" not in result:
            formatted_result = {
                "title": result.get("title", title),
                "year": result.get("year", "No disponible"),
                "genres": result.get("genres", []),
                "director": result.get("director") or result.get("creator", "No disponible"),
                "summary": result.get("overview", "No hay descripción disponible."),
                "rating": f"{result.get('score', 'N/A')}%" if result.get('score') else "No disponible",
                "cast": result.get("cast", [])
            }
            logger.info(f"✅ Información formateada: {formatted_result['title']} ({formatted_result['year']})")
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

def search_tmdb_online(search_terms):
    """Busca en TMDB y devuelve el primer resultado RELEVANTE"""
    search_url = f"https://www.themoviedb.org/search?query={search_terms.replace(' ', '+')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)
        
        try:
            logger.info(f"🌐 Buscando en TMDB: {search_terms}")
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            
            # Aceptar cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                logger.info("🍪 Cookies aceptadas")
                time.sleep(0.5)
            except:
                logger.info("ℹ️ No se encontró banner de cookies")
                pass
            
            # Buscar resultados
            time.sleep(2)
            html_content = page.content()
            browser.close()
            
            # Patrones de búsqueda
            patterns = [
                r'href="/movie/(\d+)-[^"]*"[^>]*>\s*<h2[^>]*>([^<]+)</h2>',
                r'href="/tv/(\d+)-[^"]*"[^>]*>\s*<h2[^>]*>([^<]+)</h2>',
            ]
            
            results = []
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    tmdb_id, found_title = match
                    media_type = "movie" if "/movie/" in pattern else "tv"
                    
                    # Calcular relevancia simple
                    relevance = 100 if found_title.lower() == search_terms.lower() else 50
                    
                    results.append({
                        "tmdb_id": int(tmdb_id),
                        "type": media_type,
                        "title": found_title.strip(),
                        "relevance": relevance
                    })
            
            # Tomar el mejor resultado
            if results:
                results.sort(key=lambda x: x["relevance"], reverse=True)
                best = results[0]
                logger.info(f"✅ Encontrado: {best['title']} (ID: {best['tmdb_id']}, Tipo: {best['type']})")
                return best['tmdb_id'], best['type']
            
            logger.warning("❌ No se encontraron resultados en TMDB")
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            browser.close()
            return None, None

def scrape_tmdb_with_javascript(media_id, media_type):
    """Scraping AGGRESIVO usando JavaScript para extraer datos"""
    url = f"https://www.themoviedb.org/{media_type}/{media_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(40000)
        
        try:
            logger.info(f"🎬 Scrapeando {media_type} ID: {media_id}")
            
            # Navegar a la página principal
            page.goto(url, timeout=40000, wait_until="networkidle")
            time.sleep(3)
            
            # Aceptar cookies si aparecen
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(1)
            except:
                pass
            
            # EJECUTAR JAVASCRIPT PARA EXTRAER DATOS COMPLETOS
            result = page.evaluate("""
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
                    const titleSelectors = [
                        'section.header.poster h2 a',
                        'h2.title',
                        'h2 a[href*="/movie/"], h2 a[href*="/tv/"]',
                        '.title h2',
                        'h1'
                    ];
                    
                    for (const selector of titleSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            result.title = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Sinopsis
                    const overviewSelectors = [
                        'div.overview p',
                        '.overview p',
                        '[data-cy="overview"] p'
                    ];
                    
                    for (const selector of overviewSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            result.overview = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Año
                    const yearElements = document.querySelectorAll('span.release_date, .release_date');
                    for (const element of yearElements) {
                        const text = element.textContent;
                        const yearMatch = text.match(/(19\\d{2}|20\\d{2})/);
                        if (yearMatch) {
                            result.year = yearMatch[1];
                            break;
                        }
                    }
                    
                    // Géneros
                    const genreElements = document.querySelectorAll('span.genres a, .genres a');
                    const genres = [];
                    for (const element of genreElements) {
                        if (element.textContent.trim()) {
                            genres.push(element.textContent.trim());
                        }
                    }
                    result.genres = genres;
                    
                    // Score
                    const scoreElement = document.querySelector('.user_score_chart, [data-percent]');
                    if (scoreElement) {
                        result.score = scoreElement.getAttribute('data-percent');
                    }
                    
                    return result;
                }
            """)
            
            # AHORA EXTRAER CAST DE FORMA AGRESIVA
            logger.info("🎭 Extrayendo cast con método agresivo...")
            
            # Ir a la página de cast
            cast_url = f"https://www.themoviedb.org/{media_type}/{media_id}/cast"
            page.goto(cast_url, timeout=30000, wait_until="networkidle")
            time.sleep(3)
            
            # EJECUTAR JAVASCRIPT PARA EXTRAER CAST COMPLETO
            cast_data = page.evaluate("""
                () => {
                    const cast = [];
                    
                    // Método 1: Buscar en elementos de cast
                    const castElements = document.querySelectorAll(
                        'ol.people.credits .card, .cast_list .profile, [data-cy="cast-person-name"], .person'
                    );
                    
                    for (const element of castElements) {
                        // Buscar nombre en diferentes lugares dentro del elemento
                        const nameSelectors = [
                            '.name a', '.name', 'a[href*="/person/"]', 'h2', 'p'
                        ];
                        
                        for (const selector of nameSelectors) {
                            const nameElement = element.querySelector(selector);
                            if (nameElement && nameElement.textContent) {
                                const name = nameElement.textContent.trim();
                                if (name && name.length > 2 && !name.includes('Character') && 
                                    !name.includes('Order') && name.includes(' ')) {
                                    if (!cast.includes(name)) {
                                        cast.push(name);
                                    }
                                    break;
                                }
                            }
                        }
                        
                        // Si no se encontró con selectores, buscar texto directo
                        if (element.textContent) {
                            const text = element.textContent.trim();
                            const lines = text.split('\\n');
                            for (const line of lines) {
                                const cleanLine = line.trim();
                                if (cleanLine && cleanLine.length > 2 && 
                                    !cleanLine.includes('Character') && 
                                    !cleanLine.includes('Order') &&
                                    cleanLine.includes(' ') &&
                                    !cast.includes(cleanLine)) {
                                    cast.push(cleanLine);
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Método 2: Buscar todos los enlaces a /person/
                    const personLinks = document.querySelectorAll('a[href*="/person/"]');
                    for (const link of personLinks) {
                        if (link.textContent && link.textContent.trim()) {
                            const name = link.textContent.trim();
                            if (name && name.length > 2 && name.includes(' ') && 
                                !name.includes('Character') && !cast.includes(name)) {
                                cast.push(name);
                            }
                        }
                    }
                    
                    // Método 3: Buscar en imágenes (alt text)
                    const images = document.querySelectorAll('img[alt]');
                    for (const img of images) {
                        const alt = img.getAttribute('alt');
                        if (alt && alt.length > 2 && alt.includes(' ') && 
                            !alt.includes('Character') && !cast.includes(alt)) {
                            cast.push(alt);
                        }
                    }
                    
                    return cast.slice(0, 15); // Máximo 15 actores
                }
            """)
            
            result["cast"] = cast_data
            logger.info(f"✅ Cast encontrado: {len(cast_data)} actores")
            
            # Si no se encontró cast, intentar método de emergencia
            if not cast_data:
                logger.info("🚨 Usando método de emergencia para cast...")
                emergency_cast = extract_cast_emergency_method(page)
                result["cast"] = emergency_cast
                logger.info(f"✅ Cast emergencia: {len(emergency_cast)} actores")
            
            browser.close()
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en scraping: {e}")
            browser.close()
            return {"error": f"Error: {str(e)}"}

def extract_cast_emergency_method(page):
    """Método de emergencia: extraer todo el texto y buscar patrones de nombres"""
    try:
        # Obtener todo el texto de la página
        full_text = page.content()
        
        # Buscar patrones de nombres en el HTML
        name_patterns = [
            r'<p class="name">[^<]*<a[^>]*>([^<]+)</a>',
            r'<h2 class="name">[^<]*<a[^>]*>([^<]+)</a>',
            r'<a[^>]*data-cy="cast-person-name"[^>]*>([^<]+)</a>',
            r'alt="([^"]*)"[^>]*class="profile"',
            r'<img[^>]*alt="([^"]+)"[^>]*loading="lazy"',
        ]
        
        cast_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if (name and len(name) > 2 and 
                    name not in cast_names and
                    not any(bad in name.lower() for bad in ["character", "order", "credit", "avatar", "loading", "image"]) and
                    ' ' in name and
                    len(name) < 50):
                    cast_names.append(name)
                    if len(cast_names) >= 12:
                        break
            if cast_names:
                break
        
        # Si aún no hay nombres, buscar en el texto visible
        if not cast_names:
            visible_text = page.locator("body").inner_text()
            # Buscar líneas que parezcan nombres (primera letra mayúscula, tienen espacio, etc.)
            lines = visible_text.split('\n')
            for line in lines:
                line = line.strip()
                if (len(line) > 3 and len(line) < 40 and
                    ' ' in line and
                    line[0].isupper() and
                    not any(bad in line.lower() for bad in ["character", "order", "as ", "play"]) and
                    line not in cast_names):
                    cast_names.append(line)
                    if len(cast_names) >= 8:
                        break
        
        return cast_names[:10]  # Máximo 10 nombres
        
    except Exception as e:
        logger.error(f"❌ Error en método emergencia: {e}")
        return []

def scrape_tmdb_tv(tv_id):
    """Scraper para series de TV - usa el mismo método que películas"""
    return scrape_tmdb_with_javascript(tv_id, "tv")