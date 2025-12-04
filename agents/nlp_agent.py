# agents/nlp_agent.py

import logging
import requests
import json
import re

logger = logging.getLogger("nlp_agent")

def nlp_agent(query: str):
    """
    Agent that uses Ollama with Qwen model to interpret user queries
    """
    try:
        logger.info(f"🔍 NLP Agent processing: {query}")
        
        prompt = f"""
        Eres un asistente especializado en analizar consultas sobre películas, series y contenido multimedia.
        
        ANALIZA esta consulta: "{query}"
        
        Tu tarea es IDENTIFICAR EL TÍTULO PRINCIPAL mencionado en la consulta, incluso si la descripción es vaga.
        
        Responde SOLO con un JSON válido con esta estructura:
        {{
            "intent": "search|analysis|fact_check|unknown",
            "target_title": "título detectado o null",
            "task": "descripción breve de la tarea",
            "needs_web": true/false,
            "needs_fact_check": true/false,
            "query_purpose": "propósito de la consulta en una frase"
        }}
        
        Reglas importantes:
        - "search": cuando piden buscar información general (incluye consultas sobre cast/reparto)
        - "analysis": cuando piden analizar profundamente  
        - "fact_check": cuando piden verificar una afirmación
        - "needs_web": true si requiere búsqueda web (casi siempre true)
        - "needs_fact_check": true solo para verificaciones
        - "target_title": SIEMPRE intenta extraer un título, incluso si es aproximado
        
        Palabras clave para cast/reparto: "cast", "reparto", "actores", "elenco", "protagonistas"
        
        Ejemplos:
        - "cual es el cast de Avengers" → "intent": "search", "target_title": "Avengers"
        - "reparto de The Matrix" → "intent": "search", "target_title": "The Matrix"
        - "quienes actúan en Titanic" → "intent": "search", "target_title": "Titanic"
        - "busca información sobre The Matrix" → "target_title": "The Matrix"
        """
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Extraer JSON de la respuesta
            try:
                # ----------------------------------------------
                # 1) EXTRAER JSON DE LA RESPUESTA DE OLLAMA
                # ----------------------------------------------
                json_candidates = re.findall(r'\{.*?\}', response_text, re.DOTALL)

                if not json_candidates:
                    logger.error(f"❌ No JSON found in response: {response_text}")
                    return {
                        "intent": "unknown",
                        "target_title": None,
                        "task": "fallback",
                        "needs_web": False,
                        "needs_fact_check": False,
                        "query_purpose": "No se detectó JSON en la respuesta"
                    }

                # Elegir el JSON más grande (= más probable de estar completo)
                json_str = max(json_candidates, key=len)
                parsed = json.loads(json_str)

                logger.info(f"✅ NLP Agent result: {parsed}")

                # ----------------------------------------------
                # 2) POST-PROCESAMIENTO Y NORMALIZACIÓN DEL TÍTULO
                # ----------------------------------------------
                title = parsed.get("target_title")

                # Limpieza básica
                if isinstance(title, str):
                    title = title.strip().replace('"', '').replace("'", "")
                    parsed["target_title"] = title

                # ----------------------------------------------
                # 3) Preguntas sobre DIRECTORES → intención "search"
                # ----------------------------------------------
                if any(k in query.lower() for k in ["director", "dirigió", "dirigida", "directed"]):
                    parsed["intent"] = "search"
                    parsed["task"] = "get_director"
                    parsed["needs_web"] = True

                return parsed

            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parsing JSON from Ollama: {e}")
                logger.error(f"Raw response: {response_text}")
                return {
                    "intent": "unknown",
                    "target_title": None,
                    "task": None,
                    "needs_web": False,
                    "needs_fact_check": False,
                    "query_purpose": None
                }


        q = query.lower()
        if parsed.get("intent") == "unknown":
            if any(w in q for w in ["quién actúa", "actores", "reparto", "cast", "protagonistas"]):
                parsed["intent"] = "search"
                parsed["task"] = "get_cast"
                parsed["needs_web"] = True

            elif any(w in q for w in ["es verdad", "cierto que", "fact", "verdadero o falso", "ganó", "murió"]):
                parsed["intent"] = "fact_check"
                parsed["needs_fact_check"] = True

            elif any(w in q for w in ["qué es", "de qué trata", "sinopsis", "trama"]):
                parsed["intent"] = "search"
                parsed["task"] = "get_summary"
                parsed["needs_web"] = True

            elif any(w in q for w in ["información", "datos", "detalles", "info"]):
                parsed["intent"] = "search"
                parsed["needs_web"] = True

        
        # Fallback en caso de error
        return {
            "intent": "unknown",
            "target_title": None,
            "task": "fallback",
            "needs_web": False,
            "needs_fact_check": False,
            "query_purpose": "Consulta no reconocida"
        }
        
    except Exception as e:
        logger.error(f"❌ Error en nlp_agent: {e}")
        return {
            "intent": "unknown", 
            "target_title": None,
            "task": None,
            "needs_web": False,
            "needs_fact_check": False,
            "query_purpose": None
        }