from pathlib import Path
from unittest.mock import Mock
import json

import pytest

from string_catalog.coordinator import TranslationCoordinator
from string_catalog.translator import OpenAITranslator
from string_catalog.language import Language


@pytest.fixture
def mock_translator():
    translator = Mock(spec=OpenAITranslator)
    # 模拟翻译结果
    translator.translate.side_effect = lambda text, lang, _: {
        ("I really like tests!", "zh-Hans"): "我真的很喜欢测试！",
        ("I have %lld cat", "zh-Hans"): "我有 %lld 只猫",
        ("I have %lld cats", "zh-Hans"): "我有 %lld 只猫",
        ("I have no cats :(", "zh-Hans"): "我没有猫 :(",
        ("Found %#@arg1@ with %#@arg2@", "zh-Hans"): "找到了 %#@arg1@ 和 %#@arg2@",
        ("%arg cat", "zh-Hans"): "%arg 猫",
        ("%arg cats", "zh-Hans"): "%arg 猫",
        ("%arg kitten", "zh-Hans"): "%arg 小猫",
        ("%arg kittens", "zh-Hans"): "%arg 小猫",
        ("Key is source language content", "zh-Hans"): "键是源语言内容",
        (
            "Key is source language content and contain other language",
            "zh-Hans",
        ): "键是源语言内容并包含其他语言",
    }.get((text, lang), f"TRANSLATED_{text}")
    return translator


def test_translation_coordinator(mock_translator):
    # 创建 TranslationCoordinator 实例
    coordinator = TranslationCoordinator(
        translator=mock_translator,
        target_languages={Language.CHINESE_SIMPLIFIED},
        overwrite=False,
    )

    # 获取测试文件路径
    test_file = Path(__file__).parent / "example" / "BasicCatalog.xcstrings"

    # 执行翻译
    coordinator.translate_files(test_file)

    # 验证翻译器被正确调用
    assert mock_translator.translate.called

    # 验证特定的翻译调用
    mock_translator.translate.assert_any_call("I really like tests!", "zh-Hans", None)

    # 读取生成的文件并验证内容
    output_file = (
        Path(__file__).parent / "example" / "BasicCatalog.translated.xcstrings"
    )
    expected_file = (
        Path(__file__).parent / "example" / "BasicCatalog.expected.xcstrings"
    )

    assert output_file.exists()

    # 读取并比较文件内容
    with open(output_file) as f:
        actual_content = json.load(f)
    with open(expected_file) as f:
        expected_content = json.load(f)

    # 比较 JSON 内容
    assert (
        actual_content == expected_content
    ), "Generated file content does not match expected output"
