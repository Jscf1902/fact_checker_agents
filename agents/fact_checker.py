# agents/fact_checker.py

import logging
import httpx

logger = logging.getLogger("fact_checker_agent")


# ---------------------------------------------------------
# Llamada robusta a Qwen vía Ollama
# ---------------------------------------------------------
def ask_qwen(prompt: str, timeout: int = 45) -> str:
    """
    Llama a Qwen vía Ollama con manejo de errores y timeout ampliado.
    """
    try:
        client = httpx.Client(timeout=timeout)

        response = client.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "qwen2.5:7b",
                "stream": False,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )

        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    except Exception as e:
        logger.error(f"❌ Error llamando a Qwen: {e}")
        return None



# ---------------------------------------------------------
# Fact-checker principal
# ---------------------------------------------------------
def fact_checker_agent(interpretation, evidence):
    logger.info("🔍 Realizando fact-check basado en evidencia completa...")

    claim = interpretation["entities"].get("claim")
    if not claim:
        return {
            "claim": "Consulta no detectada",
            "is_true": None,
            "evidence": "No se detectó una afirmación para verificar."
        }

    # Armar contexto completo
    ctx = [
        f"Título: {evidence.get('title')}",
        f"Año: {evidence.get('year')}",
        f"Géneros: {', '.join(evidence.get('genres', []))}",
        f"Score: {evidence.get('score')}",
        f"Creador: {evidence.get('creator')}",
        f"Resumen: {evidence.get('overview')}",
    ]

    # Cast
    cast_list = evidence.get("cast", [])
    if cast_list:
        ctx.append("Reparto: " + ", ".join([c.get("actor", "") for c in cast_list[:10]]))

    context_text = "\n".join(ctx)

    # Prompt robusto
    prompt = f"""
Actúa como un verificador de hechos experto en series.

Afirmación del usuario:
"{claim}"

Información objetiva obtenida del scraping:
{context_text}

Con base únicamente en esta información, responde:
1. ¿La afirmación es VERDADERA, FALSA o IMPOSIBLE DE DETERMINAR?
2. Explica brevemente por qué.
"""

    qwen_answer = ask_qwen(prompt)

    # -----------------------------------------
    # Si Qwen falla → inferencia fallback
    # -----------------------------------------
    if not qwen_answer:
        return {
            "claim": claim,
            "is_true": False,
            "evidence": "Error consultando Qwen."
        }

    answer_low = qwen_answer.lower()

    if "verdadera" in answer_low or "true" in answer_low:
        result = True
    elif "falsa" in answer_low or "false" in answer_low:
        result = False
    else:
        result = None

    return {
        "claim": claim,
        "is_true": result,
        "evidence": qwen_answer
    }
