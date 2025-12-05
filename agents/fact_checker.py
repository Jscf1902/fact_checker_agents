# agents/fact_checker.py

import logging
import re
import requests
import json

logger = logging.getLogger("fact_checker_agent")

def fact_checker_agent(query: str, evidence: dict = None):
    """
    Fact-checker con conocimiento común + IA
    """
    logger.info(f"🔍 Fact-check: '{query}'")
    
    try:
        claim = extract_claim_from_query(query)
        
        if not evidence or "error" in evidence:
            logger.warning("❌ No hay evidencia suficiente")
            return {
                "claim": claim,
                "is_true": None,
                "evidence": "No se encontró información suficiente para verificar.",
                "confidence": "low"
            }
        
        # PRIMERO: Verificar casos comunes de conocimiento general
        common_knowledge_result = check_common_knowledge(query, evidence)
        if common_knowledge_result:
            return common_knowledge_result
        
        # SEGUNDO: Usar IA para análisis más profundo
        ai_result = ai_fact_check_enhanced(query, evidence)
        return ai_result
        
    except Exception as e:
        logger.error(f"❌ Error en fact-checker: {e}")
        return {
            "claim": query,
            "is_true": None,
            "evidence": f"Error al verificar: {str(e)}",
            "confidence": "low"
        }

def check_common_knowledge(query: str, evidence: dict):
    """
    Verificar hechos de conocimiento común sobre cine
    """
    query_lower = query.lower()
    
    # CASO 1: Leonardo DiCaprio y Oscars
    if "dicaprio" in query_lower or "leonardo" in query_lower:
        if "oscar" in query_lower:
            if "titanic" in query_lower:
                return {
                    "claim": query,
                    "is_true": False,
                    "evidence": "❌ FALSO: Aunque Titanic ganó 11 Oscars en 1997, Leonardo DiCaprio NO ganó Oscar por Titanic. Ni siquiera fue nominado a Mejor Actor por esa película.",
                    "confidence": "high"
                }
            elif "avatar" in query_lower:
                return {
                    "claim": query,
                    "is_true": False,
                    "evidence": "❌ FALSO: Leonardo DiCaprio NO actuó en Avatar, mucho menos ganó Oscar por esa película.",
                    "confidence": "high"
                }
            elif any(word in query_lower for word in ["renacido", "revenant"]):
                return {
                    "claim": query,
                    "is_true": True,
                    "evidence": "✅ VERDADERO: Leonardo DiCaprio SÍ ganó el Oscar al Mejor Actor por 'El Renacido' (The Revenant) en 2016.",
                    "confidence": "high"
                }
    
    # CASO 2: Años de estreno
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query_lower)
    if year_match and evidence.get("year"):
        claim_year = year_match.group(1)
        real_year = str(evidence.get("year"))
        
        if claim_year != real_year:
            return {
                "claim": query,
                "is_true": False,
                "evidence": f"❌ FALSO: El año de estreno no es {claim_year}. Es {real_year}.",
                "confidence": "high"
            }
    
    return None

def ai_fact_check_enhanced(query: str, evidence: dict) -> dict:
    """
    Fact-checking con IA
    """
    if not evidence or "error" in evidence:
        return {
            "claim": query,
            "is_true": None,
            "evidence": "No hay información para verificar.",
            "confidence": "low"
        }
    
    evidence_summary = f"""
    INFORMACIÓN:
    TÍTULO: {evidence.get('title', 'Desconocido')}
    AÑO: {evidence.get('year', 'Desconocido')}
    DIRECTOR: {evidence.get('director', 'Desconocido')}
    GÉNEROS: {', '.join(evidence.get('genres', []))}
    SINOPSIS: {evidence.get('summary', 'Desconocida')[:150]}...
    """
    
    prompt = f"""
    Verifica esta afirmación: "{query}"
    
    Información disponible:
    {evidence_summary}
    
    Basándote SOLO en esta información, responde:
    VERDADERO, FALSO o INCONCLUSO
    
    Explicación breve:
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
            result = response.json().get("response", "").upper()
            
            if "VERDADERO" in result:
                return {
                    "claim": query,
                    "is_true": True,
                    "evidence": "La información confirma la afirmación.",
                    "confidence": "medium"
                }
            elif "FALSO" in result:
                return {
                    "claim": query,
                    "is_true": False,
                    "evidence": "La información contradice la afirmación.",
                    "confidence": "medium"
                }
                
    except:
        pass
    
    return {
        "claim": query,
        "is_true": None,
        "evidence": "No se pudo verificar con la información disponible.",
        "confidence": "low"
    }

def extract_claim_from_query(query: str) -> str:
    patterns_to_remove = [
        r'es cierto que', r'verifica si', r'¿es verdad que',
        r'confirmar si', r'fact check de', r'\?$'
    ]
    
    claim = query
    for p in patterns_to_remove:
        claim = re.sub(p, "", claim, flags=re.IGNORECASE)
    
    return claim.strip()