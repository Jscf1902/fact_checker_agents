import logging
import json
import ollama

logger = logging.getLogger("nlp_agent")

MODEL = "qwen2.5:7b"  # cambia aquí el modelo si quieres otro


def ask_llm_for_intent(query):
    """
    Pregunta a Qwen local vía Ollama.
    El modelo devuelve SOLO JSON válido con la interpretación.
    """

    prompt = f"""
Eres el analizador de intenciones de un sistema multi-agente.
Tu trabajo es interpretar la consulta del usuario y devolver un JSON con:

- intent: "search", "fact_check", "analysis", "opinion", "comparison", "summary", "unknown".
- target_title: serie/película si aplica.
- target_person: persona si aplica.
- task: subtarea como "genre_inference", "cast_question", "violence_compare", "award_check", etc.
- needs_web: true o false según si debe consultarse el scraper.
- needs_fact_check: true/false.
- query_purpose: una frase explicativa.

DEVUELVE SOLO JSON PURO, SIN TEXTO EXTRA.

Consulta:
"{query}"
"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response["message"]["content"].strip()

    logger.info(f"Qwen NLP output: {content}")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.error("❌ El modelo no devolvió JSON válido")
        parsed = {"intent": "unknown", "raw": content}

    return parsed


def nlp_agent(query):
    """
    Punto de entrada principal del agente NLP.
    """

    try:
        parsed = ask_llm_for_intent(query)
        return parsed
    except Exception as e:
        logger.error(f"❌ Error en nlp_agent: {e}")
        return {"intent": "unknown", "error": str(e)}
