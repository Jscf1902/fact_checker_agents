from playwright.sync_api import sync_playwright

def scrape_rt_playwright(slug):
    url = f"https://www.rottentomatoes.com/tv/{slug}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=120000)

        # ================================
        # 1. ACEPTAR COOKIES (tu selector)
        # ================================
        try:
            page.wait_for_selector('#onetrust-accept-btn-handler', timeout=8000)
            page.locator('#onetrust-accept-btn-handler').click()
            print("✔ Cookie banner cerrado")
        except:
            print("No apareció el banner de cookies")

        # ================================
        # 2. Esperar a que cargue el contenido real
        # ================================
        try:
            page.wait_for_selector('h1[data-qa="series-title"]', timeout=30000)
            print("✔ Contenido cargado")
        except:
            browser.close()
            return {"error": "No se pudo cargar el contenido después de cerrar cookies"}

        # ================================
        # 3. Extraer título
        # ================================
        try:
            title = page.locator('h1[data-qa="series-title"]').inner_text()
        except:
            title = None

        # ================================
        # 4. Extraer sinopsis
        # ================================
        try:
            synopsis = page.locator('[data-qa="series-info-description"]').inner_text()
        except:
            synopsis = None

        # ================================
        # 5. Extraer géneros
        # ================================
        try:
            genres = page.locator('[data-qa="item"]:has-text("Genre") rt-link').all_inner_texts()
        except:
            genres = []

        browser.close()

        return {
            "title": title,
            "synopsis": synopsis,
            "genres": genres
        }


if __name__ == "__main__":
    print(scrape_rt_playwright("breaking_bad"))
