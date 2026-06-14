import json
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.gemini_api_key)

PROMPT_VERSION = "v1.0"


def _build_system_prompt(theme_name: str, keywords: list[str], feedback_context: str = "") -> str:
    base = f"""Tu es un assistant de veille technologique spécialisé sur le thème : "{theme_name}".
Mots-clés associés : {'', ''.join(keywords) if keywords else ''non définis''}.

Ta mission :
1. Résumer l''article en 2-3 phrases claires et concises en français.
2. Attribuer un score de pertinence de 1 à 10 par rapport au thème donné.
   - 1-3 : hors sujet ou très faiblement lié
   - 4-6 : partiellement pertinent
   - 7-10 : très pertinent, article à lire absolument

Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication, avec ce format exact :
{{
  "summary": "résumé de l''article",
  "relevance_score": 7.5,
  "theme_match": "sous-thème identifié"
}}"""

    if feedback_context:
        base += f"\n\nContexte de préférences utilisateur (basé sur les feedbacks précédents) :\n{feedback_context}"

    return base


async def analyze_article(
    title: str,
    content: str,
    theme_name: str,
    keywords: list[str],
    feedback_context: str = ""
) -> dict:
    """Analyse un article avec Gemini et retourne summary + score."""
    model = genai.GenerativeModel(settings.gemini_model)

    system_prompt = _build_system_prompt(theme_name, keywords, feedback_context)
    user_message = f"Titre : {title}\n\nContenu :\n{content[:3000]}"  # limite tokens

    response = model.generate_content(
        f"{system_prompt}\n\n{user_message}",
        generation_config=genai.GenerationConfig(
            temperature=0.2,  # réponses cohérentes et factuelles
            max_output_tokens=512,
        )
    )

    raw = response.text.strip()

    # Nettoyage au cas où Gemini ajoute des backticks
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw)

    return {
        "summary": result.get("summary", ""),
        "relevance_score": float(result.get("relevance_score", 5.0)),
        "theme_match": result.get("theme_match", theme_name),
        "llm_prompt_version": PROMPT_VERSION,
    }


async def generate_digest(articles: list[dict], theme_name: str) -> str:
    """Génère un digest quotidien à partir des meilleurs articles."""
    model = genai.GenerativeModel(settings.gemini_model)

    articles_text = "\n\n".join([
        f"- [{a[''title'']}]({a[''url'']}) — Score: {a[''score'']}/10\n  {a[''summary'']}"
        for a in articles
    ])

    prompt = f"""Tu génères un digest quotidien de veille technologique sur le thème : "{theme_name}".

Voici les articles du jour triés par pertinence :
{articles_text}

Génère un résumé structuré en français avec :
1. Une introduction en 1 phrase sur les tendances du jour
2. Les 3 points clés à retenir
3. Une conclusion en 1 phrase

Format markdown, ton professionnel mais accessible."""

    response = model.generate_content(prompt)
    return response.text

