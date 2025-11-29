# agents/web_search.py

import logging
import re
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_search_agent")

def extract_search_terms(query):
    """
    Extrae los términos de búsqueda de la consulta del usuario
    """
    # Patrones comunes para eliminar palabras de relleno
    patterns_to_remove = [
        r'información de',
        r'datos de', 
        r'datos sobre',
        r'buscar',
        r'busca',
        r'quiero saber de',
        r'quiero saber sobre',
        r'hablame de',
        r'cuéntame de',
        r'info de'
    ]
    
    clean_query = query.lower().strip()
    
    for pattern in patterns_to_remove:
        clean_query = re.sub(pattern, '', clean_query)
    
    # Limpiar espacios extra y caracteres especiales
    clean_query = re.sub(r'[^\w\s]', '', clean_query)
    clean_query = clean_query.strip()
    
    logger.info(f"🔍 Términos de búsqueda extraídos: '{clean_query}'")
    return clean_query

def search_tmdb_online(search_terms):
    """
    Busca en TMDB y devuelve el primer resultado RELEVANTE
    """
    search_url = f"https://www.themoviedb.org/search?query={search_terms.replace(' ', '+')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)
        
        try:
            logger.info(f"🌐 Buscando en TMDB: {search_terms}")
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            
            # Aceptar cookies rápidamente
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                logger.info("✔ Cookies aceptadas")
                time.sleep(0.5)
            except:
                pass
            
            # Obtener el HTML completo y buscar con regex
            time.sleep(2)
            html_content = page.content()
            
            browser.close()
            
            # BUSCAR PATRONES MEJORADOS
            patterns = [
                # Patrón para películas principales
                r'href="/movie/(\d+)-[^"]*"[^>]*>\s*<h2[^>]*>([^<]+)</h2>',
                # Patrón para series principales  
                r'href="/tv/(\d+)-[^"]*"[^>]*>\s*<h2[^>]*>([^<]+)</h2>',
            ]
            
            results = []
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    tmdb_id, title = match
                    media_type = "movie" if "/movie/" in pattern else "tv"
                    
                    # Calcular relevancia
                    title_lower = title.lower()
                    search_lower = search_terms.lower()
                    
                    relevance = 0
                    
                    # Coincidencia exacta del título
                    if title_lower == search_lower:
                        relevance += 100
                    
                    # Coincidencia de todas las palabras principales
                    search_words = search_lower.split()
                    title_words = title_lower.split()
                    
                    exact_word_matches = sum(1 for word in search_words if word in title_words)
                    if exact_word_matches == len(search_words):
                        relevance += 50
                    
                    # Penalizar documentales, momentos, etc.
                    bad_keywords = ['documentary', 'moment', 'greatest', 'behind', 'making', 'special']
                    if any(bad in title_lower for bad in bad_keywords):
                        relevance -= 30
                    
                    if relevance >= 0:
                        results.append({
                            "tmdb_id": int(tmdb_id),
                            "type": media_type,
                            "title": title.strip(),
                            "relevance": relevance
                        })
            
            # Ordenar por relevancia y tomar el mejor
            if results:
                results.sort(key=lambda x: x["relevance"], reverse=True)
                best = results[0]
                logger.info(f"🎯 Mejor resultado: {best['title']} (ID: {best['tmdb_id']})")
                return best['tmdb_id'], best['type']
            
            logger.warning("❌ No se encontraron resultados en TMDB")
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda online: {e}")
            browser.close()
            return None, None

# ===========================================================
# Scraper TMDB (Series) - SELECTORES CORREGIDOS
# ===========================================================
def scrape_tmdb_tv(tv_id):
    """Scraper para series de TV con selectores corregidos"""
    url = f"https://www.themoviedb.org/tv/{tv_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        
        try:
            logger.info(f"📺 Scrapeando serie ID: {tv_id}")
            page.goto(url, timeout=20000, wait_until="domcontentloaded")

            # Aceptar cookies rápidamente
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(0.5)
            except:
                pass

            # Datos básicos
            result_data = {
                "source": "tmdb",
                "url": url,
                "tmdb_id": tv_id,
                "title": None,
                "overview": None,
                "year": None,
                "genres": [],
                "score": None,
                "creator": None,
                "cast": [],
                "media_type": "tv"
            }

            # INTENTAR MÚLTIPLES SELECTORES PARA EL TÍTULO
            title_selectors = [
                "section.header.poster h2 a",  # Selector principal
                "h2.title",                    # Selector alternativo
                "h2 a[href*='/tv/']",          # Otro selector común
                ".title h2",                   # Selector adicional
                "h1",                          # Último recurso
            ]

            for selector in title_selectors:
                try:
                    title_element = page.locator(selector).first
                    if title_element.count() > 0:
                        title_text = title_element.inner_text(timeout=3000).strip()
                        if title_text and len(title_text) > 1:
                            result_data["title"] = title_text
                            logger.info(f"✅ Título encontrado con '{selector}': {title_text}")
                            break
                except:
                    continue

            # OVERVIEW - Múltiples selectores
            overview_selectors = [
                "div.overview p",
                ".overview p",
                "[data-cy='overview'] p",
                ".header_info p"
            ]

            for selector in overview_selectors:
                try:
                    overview_element = page.locator(selector).first
                    if overview_element.count() > 0:
                        overview_text = overview_element.inner_text(timeout=3000).strip()
                        if overview_text:
                            result_data["overview"] = overview_text
                            break
                except:
                    continue

            # AÑO
            try:
                year_selectors = [
                    "span.release_date",
                    ".release_date",
                    ".facts span:has-text('20')",  # Busca spans que contengan años
                    "span:has-text('202'), span:has-text('201'), span:has-text('200')"
                ]
                
                for selector in year_selectors:
                    try:
                        year_element = page.locator(selector).first
                        if year_element.count() > 0:
                            year_text = year_element.inner_text(timeout=3000)
                            year_match = re.search(r'(19\d{2}|20\d{2})', year_text)
                            if year_match:
                                result_data["year"] = year_match.group(1)
                                break
                    except:
                        continue
            except:
                pass

            # GÉNEROS
            try:
                genre_selectors = [
                    "span.genres a",
                    ".genres a",
                    "[data-cy='genres'] a"
                ]
                
                for selector in genre_selectors:
                    try:
                        genre_elements = page.locator(selector).all()
                        if genre_elements:
                            genres = []
                            for genre in genre_elements:
                                try:
                                    genre_text = genre.inner_text(timeout=2000)
                                    if genre_text and genre_text.strip():
                                        genres.append(genre_text.strip())
                                except:
                                    continue
                            if genres:
                                result_data["genres"] = genres
                                break
                    except:
                        continue
            except:
                pass

            # SCORE
            try:
                score_selectors = [
                    ".user_score_chart",
                    "[data-percent]",
                    ".percent"
                ]
                
                for selector in score_selectors:
                    try:
                        score_element = page.locator(selector).first
                        if score_element.count() > 0:
                            score = score_element.get_attribute("data-percent", timeout=2000)
                            if score:
                                result_data["score"] = score
                                break
                    except:
                        continue
            except:
                pass

            # CREATOR
            try:
                # Buscar en la sección de personas
                people_sections = page.locator("ol.people li.profile, .people li.card").all()
                for person in people_sections[:10]:  # Revisar solo los primeros 10
                    try:
                        role_element = person.locator(".character, .department, .role")
                        if role_element.count() > 0:
                            role_text = role_element.inner_text(timeout=2000).lower()
                            if 'creator' in role_text or 'creador' in role_text:
                                name_element = person.locator("p a, .name a")
                                if name_element.count() > 0:
                                    creator_name = name_element.inner_text(timeout=2000).strip()
                                    if creator_name:
                                        result_data["creator"] = creator_name
                                        break
                    except:
                        continue
            except:
                pass

            browser.close()
            
            if result_data["title"]:
                logger.info(f"✅ Scraping completado: {result_data['title']}")
            else:
                logger.warning("⚠️ Scraping completado pero sin título")
                
            return result_data

        except Exception as e:
            logger.error(f"❌ Error en scraping serie: {e}")
            browser.close()
            return {"error": f"Error en scraping: {str(e)}"}

# ===========================================================
# Scraper TMDB (Películas) - SELECTORES CORREGIDOS
# ===========================================================
def scrape_tmdb_movie(movie_id):
    """Scraper para películas con selectores corregidos"""
    url = f"https://www.themoviedb.org/movie/{movie_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        
        try:
            logger.info(f"🎬 Scrapeando película ID: {movie_id}")
            page.goto(url, timeout=20000, wait_until="domcontentloaded")

            # Aceptar cookies rápidamente
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(0.5)
            except:
                pass

            # Datos básicos
            result_data = {
                "source": "tmdb", 
                "url": url,
                "tmdb_id": movie_id,
                "title": None,
                "overview": None,
                "year": None,
                "genres": [],
                "score": None,
                "director": None,
                "cast": [],
                "media_type": "movie"
            }

            # TÍTULO - Múltiples selectores
            title_selectors = [
                "section.header.poster h2 a",
                "h2.title", 
                "h2 a[href*='/movie/']",
                ".title h2",
                "h1"
            ]

            for selector in title_selectors:
                try:
                    title_element = page.locator(selector).first
                    if title_element.count() > 0:
                        title_text = title_element.inner_text(timeout=3000).strip()
                        if title_text and len(title_text) > 1:
                            result_data["title"] = title_text
                            logger.info(f"✅ Título encontrado con '{selector}': {title_text}")
                            break
                except:
                    continue

            # OVERVIEW
            overview_selectors = [
                "div.overview p",
                ".overview p", 
                "[data-cy='overview'] p"
            ]

            for selector in overview_selectors:
                try:
                    overview_element = page.locator(selector).first
                    if overview_element.count() > 0:
                        overview_text = overview_element.inner_text(timeout=3000).strip()
                        if overview_text:
                            result_data["overview"] = overview_text
                            break
                except:
                    continue

            # AÑO
            try:
                year_selectors = [
                    "span.release_date",
                    ".release_date",
                    ".facts span:has-text('20')"
                ]
                
                for selector in year_selectors:
                    try:
                        year_element = page.locator(selector).first
                        if year_element.count() > 0:
                            year_text = year_element.inner_text(timeout=3000)
                            year_match = re.search(r'(19\d{2}|20\d{2})', year_text)
                            if year_match:
                                result_data["year"] = year_match.group(1)
                                break
                    except:
                        continue
            except:
                pass

            # GÉNEROS
            try:
                genre_selectors = [
                    "span.genres a",
                    ".genres a",
                    "[data-cy='genres'] a"
                ]
                
                for selector in genre_selectors:
                    try:
                        genre_elements = page.locator(selector).all()
                        if genre_elements:
                            genres = []
                            for genre in genre_elements:
                                try:
                                    genre_text = genre.inner_text(timeout=2000)
                                    if genre_text and genre_text.strip():
                                        genres.append(genre_text.strip())
                                except:
                                    continue
                            if genres:
                                result_data["genres"] = genres
                                break
                    except:
                        continue
            except:
                pass

            # SCORE
            try:
                score_selectors = [
                    ".user_score_chart",
                    "[data-percent]",
                    ".percent"
                ]
                
                for selector in score_selectors:
                    try:
                        score_element = page.locator(selector).first
                        if score_element.count() > 0:
                            score = score_element.get_attribute("data-percent", timeout=2000)
                            if score:
                                result_data["score"] = score
                                break
                    except:
                        continue
            except:
                pass

            browser.close()
            
            if result_data["title"]:
                logger.info(f"✅ Scraping completado: {result_data['title']}")
            else:
                logger.warning("⚠️ Scraping completado pero sin título")
                
            return result_data

        except Exception as e:
            logger.error(f"❌ Error en scraping película: {e}")
            browser.close()
            return {"error": f"Error en scraping: {str(e)}"}

# ===========================================================
# Agente Web Search
# ===========================================================
def web_search_agent(query: str):
    """
    Agente que busca en TMDB
    """
    logger.info(f"🔍 Procesando consulta: {query}")

    # 1. Extraer términos de búsqueda
    search_terms = extract_search_terms(query)
    if not search_terms or len(search_terms) < 2:
        return {"error": "No se pudieron extraer términos de búsqueda válidos"}

    # 2. Buscar en TMDB online
    logger.info(f"🌐 Buscando: '{search_terms}'")
    media_id, media_type = search_tmdb_online(search_terms)
    
    if not media_id:
        return {"error": f"No se encontró '{search_terms}' en TMDB"}

    # 3. Hacer scraping
    try:
        if media_type == "tv":
            result = scrape_tmdb_tv(media_id)
        elif media_type == "movie":
            result = scrape_tmdb_movie(media_id)
        else:
            return {"error": "Tipo no soportado"}
        
        if "error" in result:
            return result
        
        result["original_query"] = query
        return result
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {"error": f"Error: {str(e)}"}

# ===========================================================
# TEST CON SELECTORES CORREGIDOS
# ===========================================================
if __name__ == "__main__":
    print("🎯 Probando Web Search Agent")
    print("=" * 50)
    
    test_queries = [
        "Busca Interstellar",
        "Minecraft",
        "Proyecto X",
    ]
    
    for query in test_queries:
        print(f"\n📋 Consulta: '{query}'")
        start_time = time.time()
        
        result = web_search_agent(query)
        
        end_time = time.time()
        time_taken = end_time - start_time
        print(f"⏱️  Tiempo: {time_taken:.1f}s")
        
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ Título: {result.get('title', 'N/A')}")
            print(f"📅 Año: {result.get('year', 'N/A')}")
            print(f"🎭 Géneros: {', '.join(result.get('genres', ['N/A']))}")
            print(f"⭐ Score: {result.get('score', 'N/A')}")
            
            if result.get('overview'):
                overview = result['overview']
                if len(overview) > 120:
                    overview = overview[:120] + "..."
                print(f"📝 Sinopsis: {overview}")