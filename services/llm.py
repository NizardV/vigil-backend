import json
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.gemini_api_key)

PROMPT_VERSION = "v1.0"


def _build_system_prompt(theme_name: str, keywords: list[str], feedback_context: str = "") -> str:
    keywords_str = ", ".join(keywords) if keywords else "not defined"
    base = (
        f'You are a tech watch assistant specialized on the theme: "{theme_name}".\n'
        f"Associated keywords: {keywords_str}.\n\n"
        "Your mission:\n"
        "1. Summarize the article in 2-3 clear and concise sentences in English.\n"
        "2. Assign a relevance score from 1 to 10 based on the given theme.\n"
        "   - 1-3: off-topic or weakly related\n"
        "   - 4-6: partially relevant\n"
        "   - 7-10: highly relevant, must-read article\n\n"
        "Respond ONLY with valid JSON, no markdown, no explanation:\n"
        '{\n'
        '  "summary": "article summary",\n'
        '  "relevance_score": 7.5,\n'
        '  "theme_match": "identified sub-theme"\n'
        '}'
    )
    if feedback_context:
        base += f"\n\nUser preference context (based on previous feedback):\n{feedback_context}"
    return base


async def analyze_article(
    title: str,
    content: str,
    theme_name: str,
    keywords: list[str],
    feedback_context: str = ""
) -> dict:
    """Analyze an article with Gemini and return summary + score."""
    model = genai.GenerativeModel(settings.gemini_model)

    system_prompt = _build_system_prompt(theme_name, keywords, feedback_context)
    user_message = f"Title: {title}\n\nContent:\n{content[:3000]}"

    response = model.generate_content(
        f"{system_prompt}\n\n{user_message}",
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )
    )

    raw = response.text.strip()
    result = json.loads(raw)

    return {
        "summary": result.get("summary", ""),
        "relevance_score": float(result.get("relevance_score", 5.0)),
        "theme_match": result.get("theme_match", theme_name),
        "llm_prompt_version": PROMPT_VERSION,
    }


async def generate_digest(articles: list[dict], theme_name: str) -> str:
    """Generate a daily digest from the top articles."""
    model = genai.GenerativeModel(settings.gemini_model)

    articles_text = "\n\n".join([
        f"- [{a['title']}]({a['url']}) - Score: {a['score']}/10\n  {a['summary']}"
        for a in articles
    ])

    prompt = (
        f'Generate a daily tech watch digest on the theme: "{theme_name}".\n\n'
        f"Today's articles sorted by relevance:\n{articles_text}\n\n"
        "Generate a structured summary in English with:\n"
        "1. A one-sentence introduction on today's trends\n"
        "2. The 3 key takeaways\n"
        "3. A one-sentence conclusion\n\n"
        "Markdown format, professional but accessible tone."
    )

    response = model.generate_content(prompt)
    return response.text