# supervisor/coordinator.py

import logging
import sys
import os

# Añadir el directorio raíz al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.fact_checker import fact_checker_agent
from agents.web_search import web_search_agent
from agents.reporter import reporter_agent
from agents.nlp_agent import nlp_agent

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("coordinator")

def run_query(query: str):
    logger.info(f"🚀 Iniciando procesamiento para: '{query}'")

    # ---------------------------------------------------------
    # 1. INTERPRETACIÓN CON OLLAMA
    # ---------------------------------------------------------
    logger.info("🔍 Analizando consulta con NLP...")
    interpretation = nlp_agent(query)
    logger.info(f"✅ NLP detectó - Intención: {interpretation.get('intent')}, Título: {interpretation.get('target_title')}")

    intent = interpretation.get("intent", "unknown")
    evidence = None
    fact_result = None

    # ---------------------------------------------------------
    # 2. BÚSQUEDA WEB SI ES NECESARIO
    # ---------------------------------------------------------
    if interpretation.get("needs_web") or intent in ["search", "analysis", "fact_check"]:
        # Usar solo target_title
        title = interpretation.get("target_title")
        
        if not title:
            logger.warning("❌ No se pudo determinar el título")
            return "No pude determinar el título sobre el cual consultar."
        
        logger.info(f"🌐 Buscando información para: '{title}'")
        evidence = web_search_agent(title)
        
        if evidence and "error" not in evidence:
            logger.info(f"✅ Información encontrada: {evidence.get('title', 'N/A')} ({evidence.get('year', 'N/A')})")
            if evidence.get("cast"):
                logger.info(f"🎭 Cast encontrado: {len(evidence['cast'])} actores")
        else:
            logger.warning("❌ No se encontró información en la búsqueda web")

    # ---------------------------------------------------------
    # 3. FACT-CHECK SI ES NECESARIO
    # ---------------------------------------------------------
    if interpretation.get("needs_fact_check") or intent == "fact_check":
        logger.info("🔍 Realizando verificación de hechos...")
        fact_result = fact_checker_agent(query, evidence)
        
        if fact_result:
            status = "VERDADERO" if fact_result.get("is_true") else "FALSO" if fact_result.get("is_true") is False else "INCONCLUSO"
            logger.info(f"✅ Fact-check completado: {status}")

    # ---------------------------------------------------------
    # 4. GENERAR REPORTE
    # ---------------------------------------------------------
    logger.info("📊 Generando reporte...")
    report = reporter_agent(
        interpretation=interpretation,
        evidence=evidence,
        fact_check=fact_result
    )
    
    logger.info(f"💾 Reporte guardado: {report.get('filename', 'N/A')}")

    # ---------------------------------------------------------
    # 5. RESPUESTA FINAL - MEJORADA PARA MOSTRAR CAST
    # ---------------------------------------------------------
    logger.info(f"🎯 Preparando respuesta para intención: {intent}")

    # DETECCIÓN ESPECÍFICA PARA CONSULTAS DE CAST
    query_lower = query.lower()
    is_cast_query = any(word in query_lower for word in ["cast", "reparto", "actores", "elenco", "protagonistas"])

    # ANALYSIS
    if intent == "analysis" or is_cast_query:
        genres = evidence.get("genres", []) if evidence else []
        summary = evidence.get("summary", "No disponible") if evidence else "No disponible"
        cast = evidence.get("cast", []) if evidence else []
        year = evidence.get("year", "No disponible") if evidence else "No disponible"
        
        # CONSULTA ESPECÍFICA DE CAST - RESPUESTA MEJORADA
        if is_cast_query and cast:
            cast_text = "\n".join([f"• {actor}" for actor in cast])
            response = f"""
🎬 **{evidence.get('title', title)} ({year})**

🎭 **Reparto Principal:**
{cast_text}

📖 **Sinopsis:**
{summary}
"""
        else:
            # ANÁLISIS GENERAL
            cast_preview = "\n".join([f"• {actor}" for actor in cast[:3]]) if cast else "No disponible"
            response = f"""
📌 **Análisis sobre: {title}**

🎬 *{evidence.get('title', title)} ({year})*

🔎 **Propósito:** {interpretation.get("query_purpose")}  
🎭 **Géneros:** {", ".join(genres) if genres else "No disponibles"}

📖 **Resumen:** {summary}

👥 **Reparto (primeros 3):**
{cast_preview}
"""
        logger.info("✅ Respuesta ANALYSIS/CAST generada")
        return response.strip()

    # SEARCH
    if intent == "search":
        summary = evidence.get("summary", "No hay información disponible") if evidence else "No hay información disponible"
        
        # MEJORAR RESPUESTA PARA INCLUIR MÁS INFORMACIÓN
        cast = evidence.get("cast", []) if evidence else []
        year = evidence.get("year", "No disponible") if evidence else "No disponible"
        genres = evidence.get("genres", []) if evidence else []
        
        if cast:
            # Si hay cast, mostrarlo en la respuesta
            cast_text = "\n".join([f"• {actor}" for actor in cast[:6]])  # Primeros 6 actores
            response = f"""
**Información sobre {title} ({year})**

**🎭 Géneros:** {", ".join(genres) if genres else "No disponibles"}

**📖 Sinopsis:**
{summary}

**🎬 Reparto Principal:**
{cast_text}
"""
        else:
            # Respuesta normal si no hay cast
            response = f"""
**Información sobre {title} ({year})**

**🎭 Géneros:** {", ".join(genres) if genres else "No disponibles"}

**📖 Sinopsis:**
{summary}
"""
        
        logger.info("✅ Respuesta SEARCH generada")
        return response.strip()

    # FACT-CHECK
    if intent == "fact_check" and fact_result:
        status = "VERDADERO" if fact_result["is_true"] else "FALSO" if fact_result["is_true"] is False else "INCONCLUSO"
        
        response = f"""
**Fact-Check:** {fact_result['claim']}

**Resultado:** {status}

**Evidencia:** {fact_result.get('evidence', 'Sin explicación')}
"""
        logger.info("✅ Respuesta FACT-CHECK generada")
        return response.strip()

    logger.warning("❌ Intención no reconocida")
    return "No entiendo la consulta. ¿Puedes reformularla?"

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:])
    if not query:
        print("❌ Por favor proporciona una consulta")
        sys.exit(1)
        
    print(run_query(query))