# GitHub Translation Stats

A GTK4/Adwaita application that scans popular open-source GitHub repositories and shows which ones have (or lack) translations for a given language.

![Screenshot](data/screenshots/screenshot-01.png)

## Features

- Lists top GitHub repos by stars with their l10n status
- Searches for `.po`, `.ts`, `.xliff` files per language
- Filter: All / Without translation / With translation
- Drill-down: click a repo to see its translation files
- Links to repos and specific translation files on GitHub
- Optional GitHub personal access token for higher rate limits
- Local cache with 1h TTL
- Language selector supporting 15+ languages

## Installation

### Debian/Ubuntu

```bash
# Add repository
curl -fsSL https://yeager.github.io/debian-repo/KEY.gpg | sudo gpg --dearmor -o /usr/share/keyrings/yeager-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager-archive-keyring.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install github-l10n
```

### Fedora/RHEL

```bash
sudo dnf config-manager --add-repo https://yeager.github.io/rpm-repo/yeager.repo
sudo dnf install github-l10n
```

### From source

```bash
pip install .
github-l10n
```

## 🌍 Contributing Translations

Help translate this app into your language! All translations are managed via Transifex.

**→ [Translate on Transifex](https://app.transifex.com/danielnylander/github-l10n/)**

### How to contribute:
1. Visit the [Transifex project page](https://app.transifex.com/danielnylander/github-l10n/)
2. Create a free account (or log in)
3. Select your language and start translating

### Currently supported languages:
Arabic, Czech, Danish, German, Spanish, Finnish, French, Italian, Japanese, Korean, Norwegian Bokmål, Dutch, Polish, Brazilian Portuguese, Russian, Swedish, Ukrainian, Chinese (Simplified)

### Notes:
- Please do **not** submit pull requests with .po file changes — they are synced automatically from Transifex
- Source strings are pushed to Transifex daily via GitHub Actions
- Translations are pulled back and included in releases

New language? Open an [issue](https://github.com/yeager/github-l10n/issues) and we'll add it!

## License

GPL-3.0-or-later — Daniel Nylander <daniel@danielnylander.se>
