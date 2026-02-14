# GitHub Translation Stats (github-l10n)

A GTK4/Adwaita application that scans popular open-source GitHub repositories and shows which ones have (or lack) translations for a given language.

"Top 100 GitHub projects without Swedish l10n" — and more.

![GTK4](https://img.shields.io/badge/GTK-4-green) ![License](https://img.shields.io/badge/license-GPL--3.0-blue)

## Features

- Lists top GitHub repos by stars with their l10n status
- Searches for `.po`, `.ts`, `.xliff` files per language
- Shows: repo name, stars, translation status (Yes/No/Partial)
- Filter: All / Without translation / With translation
- Drill-down: click a repo to see its translation files
- Links to repos and specific translation files on GitHub
- Optional GitHub personal access token (60/h → 5000/h)
- Local cache (`~/.cache/github-l10n/`, 1h TTL)
- Language selector (default: Swedish, supports 15+ languages)

## Install

### From PyPI / source

```bash
pip install .
github-l10n
```

### Debian/Ubuntu

```bash
curl -s https://yeager.github.io/debian-repo/KEY.gpg | sudo gpg --dearmor -o /usr/share/keyrings/yeager.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update && sudo apt install github-l10n
```

### Fedora/RPM

```bash
sudo dnf config-manager --add-repo https://yeager.github.io/rpm-repo/yeager.repo
sudo dnf install github-l10n
```

## Usage

Launch the app, click **Refresh** to fetch top repos and scan for translations. Use the language dropdown to check different languages.

For higher API rate limits, click the key icon and enter a GitHub personal access token.

## License

GPL-3.0-or-later — Daniel Nylander <daniel@danielnylander.se>
