# supervisor/coordinator.py

import logging
from agents.interpreter import interpreter_agent
from agents.fact_checker import fact_checker_agent
from agents.web_search import web_search_agent
from agents.reporter import reporter_agent
from agents.nlp_agent import nlp_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coordinator")


# ---------------------------------------------------------
# FUSIÓN DE INTERPRETACIONES (reglas + LLM)
# ---------------------------------------------------------
def merge_interpretations(rule_res, llm_res):
    """
    Mezcla intelligente la interpretación basada en reglas y la del modelo Qwen.
    """

    merged = {}

    # INTENT
    if llm_res and llm_res.get("intent") not in [None, "unknown"]:
        merged["intent"] = llm_res["intent"]
    else:
        merged["intent"] = rule_res.get("intent", "unknown")

    # ENTIDADES
    ents = rule_res.get("entities", {}).copy()
    merged["entities"] = ents

    # Insertar title del LLM si lo detecta
    if llm_res and llm_res.get("target_title"):
        merged["entities"]["title"] = llm_res["target_title"]

    # Insertar tv_id si viene del rule-based
    if "tv_id" in rule_res.get("entities", {}):
        merged["entities"]["tv_id"] = rule_res["entities"]["tv_id"]

    # Otros campos generados por Qwen
    if llm_res:
        merged.update({
            "task": llm_res.get("task"),
            "needs_web": llm_res.get("needs_web", False),
            "needs_fact_check": llm_res.get("needs_fact_check", False),
            "query_purpose": llm_res.get("query_purpose")
        })

    return merged


# ---------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------------------------------------
def run_query(query: str):
    logger.info(f"Coordinador: iniciando orquestación para query: {query}")

    # 1) Interpretación basada en reglas
    rule_interp = interpreter_agent(query)
    logger.info(f"Interpretación rule_based: {rule_interp}")

    # 2) Interpretación con LLM (Qwen)
    llm_interp = nlp_agent(query)
    logger.info(f"Interpretación LLM: {llm_interp}")

    # 3) Fusión
    interpretation = merge_interpretations(rule_interp, llm_interp)
    logger.info(f"Interpretación combinada final: {interpretation}")

    intent = interpretation.get("intent", "unknown")

    evidence = None
    fact_result = None

    # ---------------------------------------------------------
    # 4) Obtener evidencia si se requiere
    # ---------------------------------------------------------
    if interpretation.get("needs_web") or intent in ["search", "analysis", "fact_check"]:
        title = interpretation["entities"].get("title")
        if not title:
            return "No pude determinar el título sobre el cual consultar."
        evidence = web_search_agent(query)

    # ---------------------------------------------------------
    # 5) Realizar fact-check
    # ---------------------------------------------------------
    if interpretation.get("needs_fact_check") or intent == "fact_check":
        fact_result = fact_checker_agent(interpretation, evidence)

    # ---------------------------------------------------------
    # 6) Generar un reporte estructurado
    # ---------------------------------------------------------
    report = reporter_agent(
        interpretation=interpretation,
        evidence=evidence,
        fact_check=fact_result
    )

    # ---------------------------------------------------------
    # 7) RESPUESTA FINAL AL USUARIO
    # ---------------------------------------------------------

    # ---------------------- ANALYSIS ----------------------
    if intent == "analysis":
        genres = evidence.get("genres", []) if evidence else []
        summary = report.get("summary", "")

        return f"""
📌 **Análisis sobre tu pregunta**

🎬 *{interpretation['entities']['title']}*

🔎 **Propósito de tu pregunta:**  
{interpretation.get("query_purpose")}  

🎭 **Géneros detectados:**  
{", ".join(genres) if genres else "No disponibles"}
 **Resumen clave:**  
{summary}

(Generé un reporte completo, pero aquí solo te muestro lo importante.)
""".strip()

    # ---------------------- SEARCH ------------------------
    if intent == "search":
        summary = report.get("summary", "")
        return f"""
**Información encontrada sobre {interpretation['entities']['title']}:**

{summary}

(El reporte completo se guardó automáticamente.)
""".strip()

    # ---------------------- FACT-CHECK --------------------
    if intent == "fact_check":
        if fact_result:
            status = (
                "VERDADERO" if fact_result["is_true"] is True
                else "FALSO" if fact_result["is_true"] is False
                else "INSUFICIENTE"
            )

            explanation = fact_result.get("evidence", "Sin explicación")

            return f"""
**Resultado del fact-check**

Afirmación:
➡️ *"{fact_result['claim']}"*

Estado: **{status}**

**Evidencia o explicación:**  
{explanation}
""".strip()

    # ------------------- DEFAULT FALLBACK -------------------
    return "No entiendo la consulta. ¿Puedes reformularla?"


# ---------------------------------------------------------
# EJECUCIÓN CLI
# ---------------------------------------------------------
if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:])
    print(run_query(query))
