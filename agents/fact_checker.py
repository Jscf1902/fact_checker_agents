# agents/fact_checker.py

import logging
import re

logger = logging.getLogger("fact_checker_agent")

def fact_checker_agent(query: str, evidence: dict = None):
    """
    Fact-checker general sin casos específicos.
    Verifica usando lógica basada en evidencia estructurada y consistencia textual.
    """
    logger.info(f"🔍 Fact-check: '{query}'")
    
    try:
        claim = extract_claim_from_query(query)

        if not evidence or "error" in evidence:
            return {
                "claim": claim,
                "is_true": None,
                "evidence": "No se encontró suficiente información.",
                "confidence": "low"
            }

        result = verify_claim_general(claim, evidence, query)
        logger.info(f"✔️ Resultado fact-check: {result['is_true']}")
        return result

    except Exception as e:
        logger.error(f"❌ Error en fact-checker: {e}")
        return {
            "claim": query,
            "is_true": None,
            "evidence": f"Error interno: {str(e)}",
            "confidence": "low"
        }


# -------------------------------------------------------------
# 1) Limpieza de la afirmación
# -------------------------------------------------------------
def extract_claim_from_query(query: str) -> str:
    patterns_to_remove = [
        r'es cierto que', r'verifica si', r'¿es verdad que',
        r'confirmar si', r'fact check de', r'podrías verificar',
        r'comprueba si', r'\?$'
    ]

    claim = query
    for p in patterns_to_remove:
        claim = re.sub(p, "", claim, flags=re.IGNORECASE)

    return claim.strip()


# -------------------------------------------------------------
# 2) Verificación general sin casuísticas duras
# -------------------------------------------------------------
def verify_claim_general(claim: str, evidence: dict, original_query: str) -> dict:
    claim_lower = claim.lower()
    ev_title = evidence.get("title", "").lower()

    # ---------------------------------------------------------
    # A) Verificación de coherencia obra–consulta
    # ---------------------------------------------------------
    if ev_title and ev_title not in claim_lower:
        # Si la obra no coincide con lo consultado, se devuelve "incierto"
        # NO se asume falso porque puede ser un falso positivo del scraper.
        return {
            "claim": claim,
            "is_true": None,
            "evidence": (
                "La consulta parece referirse a una obra distinta "
                f"de la encontrada ('{evidence.get('title')}')."
            ),
            "confidence": "low"
        }

    # ---------------------------------------------------------
    # B) Verificación de DIRECTOR basado en evidencia estructurada
    # ---------------------------------------------------------
    if any(k in claim_lower for k in ["director", "dirigió", "dirigido"]):
        return compare_simple_entity(
            claim,
            entity_from_claim=extract_name_from_text(claim_lower),
            entity_from_evidence=evidence.get("director", ""),
            entity_label="director"
        )

    # ---------------------------------------------------------
    # C) Verificación de actor / cast
    # ---------------------------------------------------------
    if any(k in claim_lower for k in ["actúa", "actuo", "actor", "protagon", "reparto"]):
        return verify_actor_relation(claim, evidence)

    # ---------------------------------------------------------
    # D) Verificación de AÑO
    # ---------------------------------------------------------
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', claim_lower)
    if year_match and evidence.get("year"):
        return compare_years(claim, year_match.group(1), evidence.get("year"))

    # ---------------------------------------------------------
    # E) Verificación de premios (muy general)
    # ---------------------------------------------------------
    if any(k in claim_lower for k in ["oscar", "premio", "award", "ganó", "gano"]):
        return verify_awards_generic(claim, evidence)

    # ---------------------------------------------------------
    # F) Verificación por coincidencia textual general
    # ---------------------------------------------------------
    return generic_similarity_verification(claim, evidence)


# -------------------------------------------------------------
# 3) Utilidades generales
# -------------------------------------------------------------
def extract_name_from_text(text: str) -> str:
    """
    Extrae potencial nombre propio de la afirmación.
    Esto es útil para director/actor sin casos predefinidos.
    """
    tokens = text.split()
    candidates = [w for w in tokens if w.istitle()]
    return " ".join(candidates) if candidates else ""


def compare_simple_entity(claim, entity_from_claim, entity_from_evidence, entity_label):
    """
    Comparación genérica para director, creador, escritor, etc.
    """
    if not entity_from_evidence:
        return {
            "claim": claim,
            "is_true": None,
            "evidence": f"No hay información del {entity_label}.",
            "confidence": "low"
        }

    if entity_from_claim.lower() in entity_from_evidence.lower():
        return {
            "claim": claim,
            "is_true": True,
            "evidence": f"El {entity_label} coincide: {entity_from_evidence}.",
            "confidence": "high"
        }

    return {
        "claim": claim,
        "is_true": False,
        "evidence": (
            f"El {entity_label} mencionado no coincide. "
            f"El {entity_label} real es: {entity_from_evidence}."
        ),
        "confidence": "high"
    }


def verify_actor_relation(claim, evidence):
    """
    Verificación general para saber si un actor pertenece al cast.
    """
    cast_list = evidence.get("cast", [])
    cast_text = " ".join(cast_list).lower()
    claim_lower = claim.lower()

    extracted = extract_name_from_text(claim)
    if not extracted:
        return generic_similarity_verification(claim, evidence)

    if extracted.lower() in cast_text:
        return {
            "claim": claim,
            "is_true": True,
            "evidence": f"El actor '{extracted}' sí aparece en el reparto.",
            "confidence": "high"
        }

    return {
        "claim": claim,
        "is_true": False,
        "evidence": f"El actor '{extracted}' NO aparece en el reparto proporcionado.",
        "confidence": "high"
    }


def compare_years(claim, claim_year, real_year):
    if claim_year == str(real_year):
        return {
            "claim": claim,
            "is_true": True,
            "evidence": f"Año correcto: {real_year}.",
            "confidence": "high"
        }
    return {
        "claim": claim,
        "is_true": False,
        "evidence": f"Año incorrecto. El año real es {real_year}.",
        "confidence": "high"
    }


def verify_awards_generic(claim, evidence):
    """
    Lógica muy general basada en coincidencia entre:
    - claim
    - lista de premios detectados en evidence
    """
    ev_awards = evidence.get("awards", "").lower()

    if not ev_awards:
        return {
            "claim": claim,
            "is_true": None,
            "evidence": "No se encontró información de premios.",
            "confidence": "low"
        }

    # Si menciona un premio que aparece en evidencia → posible verdadero
    important_words = [w for w in claim.lower().split() if len(w) > 4]

    matches = sum(1 for w in important_words if w in ev_awards)
    ratio = matches / len(important_words) if important_words else 0

    if ratio >= 0.5:
        return {
            "claim": claim,
            "is_true": True,
            "evidence": "La descripción coincide con la información de premios.",
            "confidence": "medium"
        }

    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No se pudo verificar la información de premios.",
        "confidence": "low"
    }


def generic_similarity_verification(claim, evidence):
    """
    Lógica general sin asumir casos específicos.
    """
    evidence_text = str(evidence).lower()
    claim_lower = claim.lower()

    words = [w for w in claim_lower.split() if len(w) > 4]
    matches = sum(1 for w in words if w in evidence_text)
    ratio = matches / len(words) if words else 0

    if ratio >= 0.7:
        return {
            "claim": claim,
            "is_true": True,
            "evidence": "La afirmación coincide con la información encontrada.",
            "confidence": "medium"
        }
    elif ratio <= 0.25:
        return {
            "claim": claim,
            "is_true": False,
            "evidence": "La afirmación no coincide con la información disponible.",
            "confidence": "medium"
        }

    return {
        "claim": claim,
        "is_true": None,
        "evidence": "No es posible determinar la veracidad con la información disponible.",
        "confidence": "low"
    }
