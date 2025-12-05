# supervisor/coordinator.py

import logging
import sys
import os
import requests
import json

# Añadir el directorio raíz al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.fact_checker import fact_checker_agent
from agents.web_search import web_search_agent
from agents.reporter import reporter_agent
from agents.nlp_agent import nlp_agent
from agents.web_search_async import web_search_agent_async

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("coordinator")

async def run_query(query: str):
    logger.info(f"🚀 Iniciando procesamiento para: '{query}'")

    # ---------------------------------------------------------
    # 1. INTERPRETACIÓN CON OLLAMA
    # ---------------------------------------------------------
    logger.info("🔍 Analizando consulta con NLP...")
    interpretation = nlp_agent(query)
    
    if interpretation.get("intent") == "unknown" or not interpretation.get("target_title"):
        # Si el NLP no pudo entender, intentar con IA directamente
        logger.info("🤖 Consultando IA para entender mejor la consulta...")
        better_interpretation = ai_understand_query(query)
        if better_interpretation:
            interpretation.update(better_interpretation)
    
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
            return "No pude determinar de qué película o serie me hablas."
        
        logger.info(f"🌐 Buscando información para: '{title}'")
        evidence = await web_search_agent_async(title)
        
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
        logger.info("🔍 Realizando verificación de hechos con IA...")
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
    # 5. RESPUESTA FINAL - MEJORADA
    # ---------------------------------------------------------
    logger.info(f"🎯 Preparando respuesta para intención: {intent}")
    
    # DETECCIÓN ESPECÍFICA PARA CONSULTAS DE CAST
    query_lower = query.lower()
    is_cast_query = any(word in query_lower for word in ["cast", "reparto", "actores", "elenco", "protagonistas", "quién actúa", "quien actua"])

    # ANALYSIS o CAST QUERY
    if intent == "analysis" or is_cast_query:
        genres = evidence.get("genres", []) if evidence else []
        summary = evidence.get("summary", "No disponible") if evidence else "No disponible"
        cast = evidence.get("cast", []) if evidence else []
        year = evidence.get("year", "No disponible") if evidence else "No disponible"
        title_display = evidence.get("title", title) if evidence else title
        
        # CONSULTA ESPECÍFICA DE CAST - RESPUESTA MEJORADA
        if is_cast_query:
            if cast:
                cast_text = "\n".join([f"• {actor}" for actor in cast[:8]])
                response = f"""
🎬 **{title_display} ({year})**

🎭 **Reparto Principal:**
{cast_text}

📖 **Sinopsis:**
{summary}
"""
            else:
                response = f"""
🎬 **{title_display} ({year})**

ℹ️ No se pudo obtener información del reparto.

📖 **Sinopsis:**
{summary}
"""
        else:
            # ANÁLISIS GENERAL
            cast_preview = "\n".join([f"• {actor}" for actor in cast[:3]]) if cast else "No disponible"
            response = f"""
📌 **Análisis sobre: {title}**

🎬 *{title_display} ({year})*

🔎 **Propósito:** {interpretation.get("query_purpose", "Consulta general")}  
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
        title_display = evidence.get("title", title) if evidence else title
        
        if cast:
            # Si hay cast, mostrarlo en la respuesta
            cast_text = "\n".join([f"• {actor}" for actor in cast[:6]])  # Primeros 6 actores
            response = f"""
**Información sobre {title_display} ({year})**

**🎭 Géneros:** {", ".join(genres) if genres else "No disponibles"}

**📖 Sinopsis:**
{summary}

**🎬 Reparto Principal:**
{cast_text}
"""
        else:
            # Respuesta normal si no hay cast
            response = f"""
**Información sobre {title_display} ({year})**

**🎭 Géneros:** {", ".join(genres) if genres else "No disponibles"}

**📖 Sinopsis:**
{summary}
"""
        
        logger.info("✅ Respuesta SEARCH generada")
        return response.strip()

    # FACT-CHECK
    if intent == "fact_check" and fact_result:
        status = "VERDADERO" if fact_result["is_true"] else "FALSO" if fact_result["is_true"] is False else "INCONCLUSO"
        status_icon = "✅" if fact_result["is_true"] else "❌" if fact_result["is_true"] is False else "⚠️"
        
        response = f"""
{status_icon} **Fact-Check Resultado: {status}**

**Afirmación:** {fact_result['claim']}

**Evidencia:** {fact_result.get('evidence', 'Sin explicación disponible')}

**Confianza:** {fact_result.get('confidence', 'media').upper()}
"""
        logger.info("✅ Respuesta FACT-CHECK generada")
        return response.strip()

    logger.warning("❌ Intención no reconocida")
    return "No entiendo la consulta. ¿Puedes reformularla?"

def ai_understand_query(query: str):
    """
    Usar IA para entender mejor consultas complejas
    """
    prompt = f"""
    Analiza esta consulta sobre cine: "{query}"
    
    Identifica:
    1. ¿De qué película/serie habla? (título)
    2. ¿Qué quiere saber el usuario?
    
    Si la consulta es descriptiva ("payaso persigue niños"), sugiere el título más probable.
    
    Responde en JSON:
    {{
        "target_title": "título sugerido o null",
        "query_type": "search|fact_check|analysis",
        "description": "qué busca el usuario"
    }}
    """
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result_text = response.json().get("response", "")
            # Extraer JSON
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1:
                return json.loads(result_text[start:end])
    except:
        pass
    
    return None

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:])
    if not query:
        print("❌ Por favor proporciona una consulta")
        sys.exit(1)
        
    print(run_query(query))