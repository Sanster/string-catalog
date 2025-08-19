# string-catalog

[![PyPI](https://img.shields.io/pypi/v/string-catalog.svg)](https://pypi.org/project/string-catalog/)
[![Changelog](https://img.shields.io/github/v/release/Sanster/string-catalog?include_prereleases&label=changelog)](https://github.com/Sanster/string-catalog/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Sanster/string-catalog/blob/master/LICENSE)

A CLI tool for translating Xcode string catalogs.

Apps using this tool:

- [ByePhotos](https://apps.apple.com/us/app/byephotos-storage-cleanup/id6737446757): Find similar photos and compress large videos to free up space on your iPhone and iCloud.
- [ParkClock](https://apps.apple.com/us/app/parkclock/id6748295364): Parking Timer & Reminder.
- [OptiClean](https://apps.apple.com/ca/app/opticlean-ai-object-remover/id6452387177): Removes unwanted objects from photos using AI, run model fully on device.

## Installation

Install this tool using `pip`:

```bash
pip install string-catalog
```

## Usage

For help, run:

```bash
string-catalog --help
```

Translate a single xcstrings file or all xcstrings files in a directory

```bash
export OPENROUTER_API_KEY=sk-or-v1-xxxxx
string-catalog xcstrings translate /path_or_dir/to/xcstrings_file \
--model anthropic/claude-3.5-sonnet \
--lang ru \
--lang zh-Hant
```

Translate a single xcstrings file and all supported languages using deepseek-v3 API

```bash
string-catalog xcstrings translate /path_or_dir/to/xcstrings_file \
--base-url https://api.deepseek.com \
--api-key sk-xxxx --model deepseek-chat --lang all
```

- All API call results are cached in the `.translation_cache/` directory and will be used first for subsequent calls.

The translation results have a default state of `needs_review`. If you need to update them to `translated` (for example, after reviewing all translations in Xcode and wanting to avoid manually clicking "Mark as Reviewed" for each one), you can use the following command:

```bash
string-catalog xcstrings update-state /path_or_dir/to/xcstrings_file \
--old needs_review \
--new translated
```

## App Store Connect Automation

Generate What's New JSON file from xcstrings file:

```bash
string-catalog xcstrings generate-whats-new \
/Users/cwq/code/xcode/ByePhotos/ByePhotos/Resources/WhatsNewLocalizable.xcstrings \
--key v1.1_feature1 \
--key v1.1_feature2
```

Here is the generated JSON file:

```json
{
  "it": "Nuova funzione 1: Titolo\nNuova funzione 2: Titolo",
  "pt": "Nova funcionalidade 1: Título\nNova funcionalidade 2: Título",
  "ja": "新機能1: タイトル\n新機能2: タイトル",
  "zh-Hans": "新功能1: 标题\n新功能2: 标题"
}
```

Creating `ISSUER_ID`, `KEY_ID`, and `KEY_FILE` for [App Store Connect API](https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api), then update Whats New using the following command:

```bash
export ASC_ISSUER_ID=xxxx
export ASC_KEY_ID=xxxx
export ASC_KEY_FILE=xxxx.p8

string-catalog appstore update-whats-new \
--bundle-id com.xxx.xxx \
--version 1.0.0 \
--json-path whats_new.json \
--platform IOS
```

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

```bash
uv run string-catalog --help
```

Test:

```bash
uv run pytest
```

# Acknowledgments

This project is inspired by [swift-translate](https://github.com/hidden-spectrum/swift-translate).
