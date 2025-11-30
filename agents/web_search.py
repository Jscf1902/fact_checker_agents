# agents/web_search.py

import logging
import re
import time
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
        if media_type == "tv":
            result = scrape_tmdb_tv(media_id)
        else:
            result = scrape_tmdb_movie(media_id)
        
        # ✅ CONVERTIR AL FORMATO ESPERADO POR EL REPORTER
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

# ===========================================================
# FUNCIONES DE SCRAPING (MEJORADAS)
# ===========================================================

def scrape_tmdb_movie(movie_id):
    """Scraper para películas - MEJORADO"""
    url = f"https://www.themoviedb.org/movie/{movie_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        
        try:
            logger.info(f"🎬 Scrapeando película ID: {movie_id}")
            page.goto(url, timeout=20000, wait_until="domcontentloaded")

            # Aceptar cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(0.5)
            except:
                pass

            # Datos básicos
            result_data = {
                "title": None,
                "overview": None,
                "year": None,
                "genres": [],
                "score": None,
                "director": None,
                "cast": []
            }

            # TÍTULO
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
                        if title_text:
                            result_data["title"] = title_text
                            logger.info(f"📝 Título: {title_text}")
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
                            logger.info(f"📖 Sinopsis obtenida")
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
                                logger.info(f"📅 Año: {result_data['year']}")
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
                                    if genre_text:
                                        genres.append(genre_text.strip())
                                except:
                                    continue
                            if genres:
                                result_data["genres"] = genres
                                logger.info(f"🎭 Géneros: {', '.join(genres)}")
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
                                logger.info(f"⭐ Score: {score}%")
                                break
                    except:
                        continue
            except:
                pass

            browser.close()
            
            if result_data["title"]:
                logger.info(f"✅ Scraping completado exitosamente")
            else:
                logger.warning("⚠️ Scraping completado pero sin título")
                
            return result_data

        except Exception as e:
            logger.error(f"❌ Error en scraping: {e}")
            browser.close()
            return {"error": f"Error: {str(e)}"}

def scrape_tmdb_tv(tv_id):
    """Scraper para series de TV"""
    url = f"https://www.themoviedb.org/tv/{tv_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        
        try:
            logger.info(f"📺 Scrapeando serie ID: {tv_id}")
            page.goto(url, timeout=20000, wait_until="domcontentloaded")

            # Aceptar cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=2000)
                time.sleep(0.5)
            except:
                pass

            # Datos básicos
            result_data = {
                "title": None,
                "overview": None,
                "year": None,
                "genres": [],
                "score": None,
                "creator": None,
                "cast": []
            }

            # TÍTULO
            title_selectors = [
                "section.header.poster h2 a",
                "h2.title",
                "h2 a[href*='/tv/']",
                ".title h2",
                "h1",
            ]

            for selector in title_selectors:
                try:
                    title_element = page.locator(selector).first
                    if title_element.count() > 0:
                        title_text = title_element.inner_text(timeout=3000).strip()
                        if title_text:
                            result_data["title"] = title_text
                            logger.info(f"📝 Título: {title_text}")
                            break
                except:
                    continue

            # OVERVIEW
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
                            logger.info(f"📖 Sinopsis obtenida")
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
                                logger.info(f"📅 Año: {result_data['year']}")
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
                                    if genre_text:
                                        genres.append(genre_text.strip())
                                except:
                                    continue
                            if genres:
                                result_data["genres"] = genres
                                logger.info(f"🎭 Géneros: {', '.join(genres)}")
                                break
                    except:
                        continue
            except:
                pass

            browser.close()
            
            if result_data["title"]:
                logger.info(f"✅ Scraping completado exitosamente")
            else:
                logger.warning("⚠️ Scraping completado pero sin título")
                
            return result_data

        except Exception as e:
            logger.error(f"❌ Error en scraping: {e}")
            browser.close()
            return {"error": f"Error: {str(e)}"}