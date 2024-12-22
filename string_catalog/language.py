from enum import Enum
from typing import List


class Language(str, Enum):
    """A class representing language codes."""

    ARABIC = "ar"
    CATALAN = "ca"
    CHINESE_SIMPLIFIED = "zh-Hans"
    CHINESE_TRADITIONAL = "zh-Hant"
    CHINESE_HONG_KONG = "zh-HK"
    CROATIAN = "hr"
    CZECH = "cs"
    DANISH = "da"
    DUTCH = "nl"
    ENGLISH = "en"
    FINNISH = "fi"
    FRENCH = "fr"
    GERMAN = "de"
    GREEK = "el"
    HEBREW = "he"
    HINDI = "hi"
    HUNGARIAN = "hu"
    INDONESIAN = "id"
    ITALIAN = "it"
    JAPANESE = "ja"
    KOREAN = "ko"
    MALAY = "ms"
    NORWEGIAN_BOKMAL = "nb"
    POLISH = "pl"
    PORTUGUESE_BRAZIL = "pt-BR"
    PORTUGUESE_PORTUGAL = "pt-PT"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SLOVAK = "sk"
    SPANISH = "es"
    SWEDISH = "sv"
    THAI = "th"
    TURKISH = "tr"
    UKRAINIAN = "uk"
    VIETNAMESE = "vi"

    @classmethod
    def all_common(cls) -> List["Language"]:
        return [
            cls.ARABIC,
            cls.CATALAN,
            cls.CHINESE_HONG_KONG,
            cls.CROATIAN,
            cls.CZECH,
            cls.DANISH,
            cls.DUTCH,
            cls.ENGLISH,
            cls.FINNISH,
            cls.FRENCH,
            cls.GERMAN,
            cls.GREEK,
            cls.HEBREW,
            cls.HINDI,
            cls.HUNGARIAN,
            cls.INDONESIAN,
            cls.ITALIAN,
            cls.JAPANESE,
            cls.KOREAN,
            cls.MALAY,
            cls.NORWEGIAN_BOKMAL,
            cls.POLISH,
            cls.PORTUGUESE_BRAZIL,
            cls.PORTUGUESE_PORTUGAL,
            cls.ROMANIAN,
            cls.RUSSIAN,
            cls.SLOVAK,
            cls.SPANISH,
            cls.SWEDISH,
            cls.THAI,
            cls.TURKISH,
        ]
