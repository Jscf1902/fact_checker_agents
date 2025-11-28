# agents/interpreter.py

import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interpreter_agent")


# ===========================================================
# INTENT DETECTION
# ===========================================================
def detect_intent(query: str) -> str:
    q = query.lower()

    if any(word in q for word in ["buscar", "información", "info", "datos", "detalles", "sobre"]):
        return "search"

    if any(word in q for word in ["verifica", "es cierto", "confirma", "chequea", "fact", "verdad"]):
        return "fact_check"

    if any(word in q for word in ["reporte", "resumen", "report"]):
        return "report"

    return "unknown"


# ===========================================================
# ENTITY EXTRACTION (muy simple, luego podemos mejorarlo)
# ===========================================================
def extract_entities(query: str) -> Dict:
    q = query.lower()
    entities = {
        "title": None,
        "person": None,
        "claim": None,
    }

    # SERIES / TITLES conocidos (luego lo hacemos dinámico con búsqueda)
    tv_shows = {
        "breaking bad": 1396,
        "better call saul": 60059,
        "the office": 2316,
        "game of thrones": 1399,
    }

    for title in tv_shows:
        if title in q:
            entities["title"] = title
            entities["tv_id"] = tv_shows[title]

    # PERSONAS básicas (podemos expandir luego)
    people = [
        "bryan cranston",
        "aaron paul",
        "vince gilligan",
        "bob odenkirk",
    ]

    for p in people:
        if p.lower() in q:
            entities["person"] = p

    # CLAIM (texto original útil para fact checking)
    entities["claim"] = query

    return entities


# ===========================================================
# MAIN INTERPRETER AGENT
# ===========================================================
def interpreter_agent(query: str) -> Dict:
    logger.info(f"Interpretando consulta: {query}")

    intent = detect_intent(query)
    entities = extract_entities(query)

    return {
        "intent": intent,
        "entities": entities
    }


# ===========================================================
# TEST
# ===========================================================
if __name__ == "__main__":
    print(interpreter_agent("Dame información de Breaking Bad"))
    print(interpreter_agent("Verifica si Bryan Cranston ganó un Emmy"))
