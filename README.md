# string-catalog

[![PyPI](https://img.shields.io/pypi/v/string-catalog.svg)](https://pypi.org/project/string-catalog/)
[![Changelog](https://img.shields.io/github/v/release/Sanster/string-catalog?include_prereleases&label=changelog)](https://github.com/Sanster/string-catalog/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Sanster/string-catalog/blob/master/LICENSE)

A CLI tool for translating Xcode string catalogs.

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

You can also use:

```bash
python -m string_catalog --help
```

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

```bash
cd string-catalog
python -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:

```bash
pip install -e '.[test]'
```

To run the tests:

```bash
python -m pytest
```

# Acknowledgments

This project is inspired by [swift-translate](https://github.com/hidden-spectrum/swift-translate).
