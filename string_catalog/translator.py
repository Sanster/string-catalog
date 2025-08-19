from typing import Optional
import openai
from openai import OpenAI
from diskcache import Cache
from tenacity import retry, stop_after_attempt, wait_exponential


class TranslationError(Exception):
    """Raised when translation fails"""

    pass


class OpenAITranslator:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "anthropic/claude-3.5-haiku-20241022",
        cache_dir: str = ".translation_cache",
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.cache = Cache(cache_dir)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=3, max=10),
        retry_error_cls=TranslationError,
    )
    def translate(
        self, text: str, target_language: str, comment: Optional[str] = None
    ) -> str:
        """Translate text to target language using OpenAI"""
        cache_key = f"{text}:{target_language}:{comment}:{self.model}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        system_prompt = (
            "You are a helpful assistant designed to translate the given text "
            f"from English to the language with ISO 639-1 code: {target_language}\n"
            "If the input text contains argument placeholders (%arg, @arg1, %lld, etc), "
            "it's important they are preserved in the translated text.\n"
            "You should not output anything other than the translated text.\n"
        )

        if comment:
            system_prompt += f"\n- IMPORTANT: Take into account the following context when translating: {comment}\n"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
            )
            result = response.choices[0].message.content.strip()

            self.cache[cache_key] = result
            return result

        except openai.OpenAIError as e:
            raise TranslationError(f"OpenAI translation failed: {str(e)}")
