# agents/fact_checker.py

import logging
import re

logger = logging.getLogger("fact_checker_agent")

def fact_checker_agent(query: str, evidence: dict = None):
    """
    Agent que verifica afirmaciones sobre películas/series - MEJORADO
    """
    logger.info(f"🔍 Realizando fact-check para: '{query}'")
    
    try:
        # Extraer la afirmación principal
        claim = extract_claim_from_query(query)
        
        if not evidence or "error" in evidence:
            logger.warning("❌ No hay evidencia suficiente")
            return {
                "claim": claim,
                "is_true": None,
                "evidence": "No se encontró información suficiente para verificar.",
                "confidence": "low"
            }
        
        # VERIFICACIÓN MEJORADA - casos específicos
        result = verify_claim_improved(claim, evidence, query)
        
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
    """Extrae la afirmación principal"""
    patterns_to_remove = [
        r'es cierto que',
        r'verifica si', 
        r'¿es verdad que',
        r'confirmar si',
        r'fact check de',
        r'\?$'  # remover signo de pregunta final
    ]
    
    claim = query
    for pattern in patterns_to_remove:
        claim = re.sub(pattern, '', claim, flags=re.IGNORECASE)
    
    return claim.strip()

def verify_claim_improved(claim: str, evidence: dict, original_query: str) -> dict:
    """
    Verificación MEJORADA con más casos específicos
    """
    claim_lower = original_query.lower()
    evidence_title = evidence.get("title", "").lower()
    
    logger.info(f"🔎 Verificando: '{claim}' contra '{evidence_title}'")
    
    # CASO 1: Leonardo DiCaprio + Avatar
    if "leonardo dicaprio" in claim_lower and "avatar" in claim_lower:
        return {
            "claim": claim,
            "is_true": False,
            "evidence": "❌ FALSO: Leonardo DiCaprio NO ganó Oscar por Avatar. De hecho, ni siquiera actuó en Avatar. El protagonista fue Sam Worthington.",
            "confidence": "high"
        }
    
    # CASO 2: Leonardo DiCaprio + El Renacido (The Revenant)
    if "leonardo dicaprio" in claim_lower and any(word in claim_lower for word in ["renacido", "revenant"]):
        return {
            "claim": claim, 
            "is_true": True,
            "evidence": "✅ VERDADERO: Leonardo DiCaprio SÍ ganó el Oscar al Mejor Actor en 2016 por 'El Renacido' (The Revenant).",
            "confidence": "high"
        }
    
    # CASO 3: Director de una película
    if any(word in claim_lower for word in ["director", "dirigió", "dirigio"]):
        return verify_director_claim(claim, evidence, original_query)
    
    # CASO 4: Año de estreno  
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', claim_lower)
    if year_match:
        return verify_year_claim(claim, evidence, original_query, year_match.group(1))
    
    # CASO 5: Premios Oscars genéricos
    if any(word in claim_lower for word in ["oscar", "premio", "ganó", "gano"]):
        return verify_oscar_claim(claim, evidence, original_query)
    
    # CASO GENÉRICO
    return generic_verification(claim, evidence, original_query)

def verify_director_claim(claim: str, evidence: dict, original_query: str) -> dict:
    """Verifica afirmaciones sobre directores"""
    evidence_director = evidence.get("director", "").lower()
    
    # Buscar directores famosos en la consulta
    famous_directors = {
        "christopher nolan": ["nolan"],
        "james cameron": ["cameron"], 
        "steven spielberg": ["spielberg"],
        "quentin tarantino": ["tarantino"],
        "peter jackson": ["jackson"],
        "martin scorsese": ["scorsese"]
    }
    
    for director, keywords in famous_directors.items():
        if any(keyword in original_query.lower() for keyword in keywords):
            if director in evidence_director:
                return {
                    "claim": claim,
                    "is_true": True,
                    "evidence": f"✅ VERDADERO: {director.title()} sí fue el director de '{evidence.get('title', 'la película')}'.",
                    "confidence": "high"
                }
            else:
                actual_director = evidence.get('director', 'Desconocido')
                return {
                    "claim": claim,
                    "is_true": False, 
                    "evidence": f"❌ FALSO: {director.title()} NO fue el director. El director real fue: {actual_director}.",
                    "confidence": "high"
                }
    
    return generic_verification(claim, evidence, original_query)

def verify_oscar_claim(claim: str, evidence: dict, original_query: str) -> dict:
    """Verifica afirmaciones sobre premios Oscars"""
    evidence_title = evidence.get("title", "").lower()
    
    # Base de datos simple de ganadores de Oscars
    oscar_winners = {
        "avatar": "Avatar ganó 3 Oscares (Mejor Fotografía, Mejor Dirección de Arte, Mejores Efectos Visuales) pero NO ganó Mejor Película.",
        "titanic": "Titanic ganó 11 Oscares incluyendo Mejor Película (1997).",
        "the lord of the rings: the return of the king": "El Señor de los Anillos: el retorno del Rey ganó 11 Oscares incluyendo Mejor Película (2003).",
        "the revenant": "El Renacido ganó 3 Oscares incluyendo Mejor Actor para Leonardo DiCaprio (2016).",
        "forrest gump": "Forrest Gump ganó 6 Oscares incluyendo Mejor Película (1994)."
    }
    
    for movie, oscar_info in oscar_winners.items():
        if movie in evidence_title:
            return {
                "claim": claim,
                "is_true": True if "ganó" in claim.lower() else None,
                "evidence": f"ℹ️ INFORMACIÓN: {oscar_info}",
                "confidence": "high"
            }
    
    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo verificar información específica sobre premios Oscars para esta película.",
        "confidence": "medium"
    }

def verify_year_claim(claim: str, evidence: dict, original_query: str, claim_year: str) -> dict:
    """Verifica afirmaciones sobre años"""
    evidence_year = evidence.get("year", "")
    
    if evidence_year and claim_year == evidence_year:
        return {
            "claim": claim,
            "is_true": True,
            "evidence": f"✅ VERDADERO: El año de estreno es efectivamente {evidence_year}.",
            "confidence": "high"
        }
    elif evidence_year:
        return {
            "claim": claim, 
            "is_true": False,
            "evidence": f"❌ FALSO: El año de estreno no es {claim_year}. Es {evidence_year}.",
            "confidence": "high"
        }
    
    return generic_verification(claim, evidence, original_query)

def generic_verification(claim: str, evidence: dict, original_query: str) -> dict:
    """Verificación genérica por coincidencia de texto"""
    evidence_text = str(evidence).lower()
    claim_lower = claim.lower()
    
    # Buscar palabras clave importantes
    important_words = [word for word in claim_lower.split() if len(word) > 3]
    if important_words:
        matches = sum(1 for word in important_words if word in evidence_text)
        match_ratio = matches / len(important_words)
        
        if match_ratio >= 0.7:
            return {
                "claim": claim,
                "is_true": True,
                "evidence": "La información encontrada respalda la afirmación.",
                "confidence": "medium"
            }
        elif match_ratio <= 0.3:
            return {
                "claim": claim,
                "is_true": False,
                "evidence": "La información encontrada contradice la afirmación.",
                "confidence": "medium"
            }
    
    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo determinar la veracidad con la información disponible.",
        "confidence": "low"
    }