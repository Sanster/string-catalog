# string-catalog

[![PyPI](https://img.shields.io/pypi/v/string-catalog.svg)](https://pypi.org/project/string-catalog/)
[![Changelog](https://img.shields.io/github/v/release/Sanster/string-catalog?include_prereleases&label=changelog)](https://github.com/Sanster/string-catalog/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Sanster/string-catalog/blob/master/LICENSE)

A CLI tool for translating Xcode string catalogs.

My apps using this tool:

- [ByePhotos](https://apps.apple.com/us/app/byephotos-storage-cleanup/id6737446757): Find similar photos and compress large videos to free up space on your iPhone and iCloud.
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
string-catalog translate /path_or_dir/to/xcstrings_file --model anthropic/claude-3.5-sonnet \
--lang ru \
--lang zh-Hant
```

Translate a single xcstrings file and all supported languages using deepseek-v3 API

```bash
string-catalog translate /path_or_dir/to/xcstrings_file --base-url https://api.deepseek.com --api-key sk-xxxx --model deepseek-chat --lang all
```

- All API call results are cached in the `.translation_cache/` directory and will be used first for subsequent calls.

The translation results have a default state of `needs_review`. If you need to update them to `translated` (for example, after reviewing all translations in Xcode and wanting to avoid manually clicking "Mark as Reviewed" for each one), you can use the following command:

```bash
string-catalog update-state /path_or_dir/to/xcstrings_file \
--old needs_review \
--new translated
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
