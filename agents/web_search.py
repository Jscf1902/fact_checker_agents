# agents/web_search.py

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_search_agent")


# ===========================================================
# Scraper TMDB (Series y Películas)
# ===========================================================
def scrape_tmdb_tv(tv_id):
    url = f"https://www.themoviedb.org/tv/{tv_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        # 1. Aceptar cookies
        try:
            page.wait_for_selector("#onetrust-accept-btn-handler", timeout=4000)
            page.locator("#onetrust-accept-btn-handler").click()
            logger.info("✔ Cookies aceptadas")
        except:
            logger.info("No apareció banner de cookies")

        page.wait_for_timeout(1500)

        # Título
        try:
            title = page.locator("section.header.poster h2 a").inner_text()
        except:
            title = None

        # Overview
        try:
            overview = page.locator("div.overview p").inner_text()
        except:
            overview = None

        # Año
        try:
            year = (
                page.locator("section.header.poster span.tag.release_date")
                .inner_text()
                .strip("()")
            )
        except:
            year = None

        # Géneros
        try:
            genre_nodes = page.query_selector_all("span.genres a")
            genres = [g.inner_text() for g in genre_nodes]
        except:
            genres = []

        # Score
        try:
            score = (
                page.locator(".user_score_chart")
                .get_attribute("data-percent")
                .strip()
            )
        except:
            score = None

        # Creator
        try:
            creator = None
            items = page.locator("ol.people li.profile")
            for i in range(items.count()):
                role = items.nth(i).locator(".character").inner_text()
                if "Creador" in role or "Creator" in role:
                    creator = items.nth(i).locator("a").inner_text()
                    break
        except:
            creator = None

        # Reparto
        try:
            cast_items = page.query_selector_all(
                "section.panel.top_billed li.card"
            )
            cast = []
            for c in cast_items:
                actor = c.query_selector("p a")
                char = c.query_selector("p.character")
                if actor:
                    cast.append({
                        "actor": actor.inner_text().strip(),
                        "character": char.inner_text().strip() if char else None,
                    })
        except:
            cast = []

        browser.close()

        return {
            "source": "tmdb",
            "url": url,
            "title": title,
            "overview": overview,
            "year": year,
            "genres": genres,
            "score": score,
            "creator": creator,
            "cast": cast,
        }


# ===========================================================
# Agente Web Search
# ===========================================================
def web_search_agent(query: str):
    """
    Recibe una consulta tipo:
    'Busca información de Breaking Bad'
    """

    logger.info(f"Buscando información para: {query}")

    # por ahora, vamos directo a Breaking Bad (tv_id=1396)
    # luego lo automatizamos
    if "breaking bad" in query.lower():
        return scrape_tmdb_tv(1396)

    # Si no sabemos qué es:
    return {"error": "No se encontró información"}


if __name__ == "__main__":
    print(web_search_agent("Información de Breaking Bad"))
