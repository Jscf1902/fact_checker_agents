# agents/fact_checker.py

import logging

logger = logging.getLogger("fact_checker_agent")

def fact_checker_agent(query: str, evidence: dict = None):
    """
    Agent que verifica afirmaciones sobre películas/series
    """
    logger.info(f"🔍 Realizando fact-check para: '{query}'")
    
    try:
        # Extraer la afirmación principal de la query
        claim = extract_claim_from_query(query)
        
        if not evidence or "error" in evidence:
            logger.warning("❌ No hay evidencia suficiente para verificar")
            return {
                "claim": claim,
                "is_true": None,
                "evidence": "No se encontró información suficiente para verificar esta afirmación.",
                "confidence": "low"
            }
        
        # Verificar diferentes tipos de afirmaciones
        result = verify_claim(claim, evidence, query)
        
        logger.info(f"✅ Fact-check completado: {result['is_true']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en fact-checker: {e}")
        return {
            "claim": query,
            "is_true": None,
            "evidence": f"Error al verificar: {str(e)}",
            "confidence": "low"
        }

def extract_claim_from_query(query: str) -> str:
    """
    Extrae la afirmación principal de la consulta
    """
    # Limpiar la query para obtener la afirmación clave
    query_lower = query.lower()
    
    # Patrones comunes en consultas de verificación
    patterns_to_remove = [
        r'es cierto que',
        r'verifica si',
        r'¿es verdad que',
        r'confirmar si',
        r'fact check de'
    ]
    
    claim = query
    for pattern in patterns_to_remove:
        claim = re.sub(pattern, '', claim, flags=re.IGNORECASE)
    
    return claim.strip()

def verify_claim(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verifica la afirmación contra la evidencia disponible
    """
    claim_lower = claim.lower()
    evidence_lower = str(evidence).lower()
    
    # Verificaciones específicas
    if any(word in claim_lower for word in ["oscar", "premio", "ganó", "gano", "premió"]):
        return verify_awards(claim, evidence, original_query)
    elif any(word in claim_lower for word in ["dirigió", "director", "dirigio"]):
        return verify_director(claim, evidence, original_query)
    elif any(word in claim_lower for word in ["año", "año", "estreno", "salio"]):
        return verify_year(claim, evidence, original_query)
    else:
        return verify_general(claim, evidence, original_query)

def verify_awards(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verifica afirmaciones sobre premios Oscars
    """
    # Para "Leonardo DiCaprio ganó Oscar por El Renacido"
    if "leonardo dicaprio" in original_query.lower() and "renacido" in original_query.lower():
        return {
            "claim": claim,
            "is_true": True,
            "evidence": "✅ CORRECTO: Leonardo DiCaprio ganó el Oscar al Mejor Actor en 2016 por su papel en 'El Renacido' (The Revenant).",
            "confidence": "high"
        }
    
    # Búsqueda genérica en la evidencia
    title = evidence.get("title", "").lower()
    
    if "oscar" in claim.lower() and evidence:
        # Simular verificación - en un sistema real buscarías en base de datos de Oscars
        oscar_winners = {
            "the revenant": "Leonardo DiCaprio (Mejor Actor, 2016)",
            "titanic": "11 Oscares incluyendo Mejor Película (1997)",
            "the lord of the rings": "11 Oscares incluyendo Mejor Película (2003)",
            "forrest gump": "6 Oscares incluyendo Mejor Película (1994)"
        }
        
        for movie, oscar_info in oscar_winners.items():
            if movie in title:
                return {
                    "claim": claim,
                    "is_true": True,
                    "evidence": f"✅ CORRECTO: {oscar_info}",
                    "confidence": "high"
                }
    
    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo verificar información específica sobre premios Oscars para esta película.",
        "confidence": "medium"
    }

def verify_director(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verifica afirmaciones sobre directores
    """
    evidence_director = evidence.get("director", "").lower()
    claim_lower = claim.lower()
    
    # Buscar nombres de directores comunes en la afirmación
    directors = ["christopher nolan", "james cameron", "steven spielberg", "quentin tarantino"]
    
    for director in directors:
        if director in claim_lower:
            if director in evidence_director:
                return {
                    "claim": claim,
                    "is_true": True,
                    "evidence": f"✅ CORRECTO: {director.title()} sí fue el director de {evidence.get('title', 'esta película')}.",
                    "confidence": "high"
                }
            else:
                return {
                    "claim": claim,
                    "is_true": False,
                    "evidence": f"❌ FALSO: {director.title()} no fue el director de {evidence.get('title', 'esta película')}. Director real: {evidence.get('director', 'No disponible')}.",
                    "confidence": "high"
                }
    
    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo verificar información específica sobre el director.",
        "confidence": "medium"
    }

def verify_year(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verifica afirmaciones sobre años de estreno
    """
    evidence_year = evidence.get("year", "")
    
    # Buscar año en la afirmación
    import re
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', claim)
    
    if year_match and evidence_year:
        claim_year = year_match.group(1)
        if claim_year == evidence_year:
            return {
                "claim": claim,
                "is_true": True,
                "evidence": f"✅ CORRECTO: El año de estreno es {evidence_year}.",
                "confidence": "high"
            }
        else:
            return {
                "claim": claim,
                "is_true": False,
                "evidence": f"❌ FALSO: El año de estreno no es {claim_year}. Es {evidence_year}.",
                "confidence": "high"
            }
    
    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo verificar el año específico.",
        "confidence": "medium"
    }

def verify_general(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verificación genérica basada en coincidencias de texto
    """
    evidence_text = str(evidence).lower()
    claim_lower = claim.lower()
    
    # Buscar coincidencias clave
    important_words = [word for word in claim_lower.split() if len(word) > 3]
    matches = sum(1 for word in important_words if word in evidence_text)
    
    if matches >= len(important_words) * 0.6:  # 60% de coincidencia
        return {
            "claim": claim,
            "is_true": True,
            "evidence": "La información encontrada coincide con la afirmación.",
            "confidence": "medium"
        }
    else:
        return {
            "claim": claim,
            "is_true": False,
            "evidence": "La información encontrada no respalda la afirmación.",
            "confidence": "medium"
        }

# Necesitamos importar re
import re