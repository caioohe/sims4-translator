<p align="center"><strong>English</strong> · <a href="README.pt-BR.md">Português (Brasil)</a></p>

<p align="center">
  <img src="docs/assets/banner-en.svg" alt="The Sims 4 Translator — reliability fork" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-68dbc2" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11-3277bb" alt="Windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.12_%7C_3.14-3277bb" alt="Python 3.12 and 3.14">
  <a href="https://github.com/caioohe/sims4-translator/pull/1"><img src="https://img.shields.io/badge/development-under_review-e6b85c" alt="Development under review"></a>
</p>

<p align="center">
  <a href="#download-and-run">Download</a> ·
  <a href="#translation-providers">Providers</a> ·
  <a href="#translate-a-mod">Getting started</a> ·
  <a href="#documentation-and-validation">Documentation</a> ·
  <a href="https://github.com/caioohe/sims4-translator/issues">Report an issue</a>
</p>

A translation editor for **The Sims 4** `.package` mods, with reusable dictionaries, translation exports and automatic translation services.

This fork, maintained by **caioohe**, derives from [voky1/sims4-translator](https://github.com/voky1/sims4-translator). It focuses on handling failures, preserving game text structure and reducing lost progress when translating large mods.

> **Under review:** improvements are on [`fix/translation-reliability`](https://github.com/caioohe/sims4-translator/tree/fix/translation-reliability), in [PR #1](https://github.com/caioohe/sims4-translator/pull/1). The `main` branch still contains the original base. No automatic merge has been performed.

## Changes in this fork

- **Gemini and Microsoft Translator:** official APIs, batch translation and test buttons in Options.
- **Game text protection:** variables, tags and escapes are validated; Gemini/Microsoft translate visible text inside `{M0...}` and `{F0...}` gender branches while preserving their structure.
- **Network failures and limits:** timeouts, bounded retries and `Retry-After` handling in the implemented provider adapters. Persistent errors stop translation.
- **Progress recovery:** completed batches are checkpointed; compatible records can be restored when reopening a package.
- **`.package` and STBL handling:** documented fixes for writing, backups, caches and resource preservation.
- **Organized settings:** provider settings in General, masked keys, saving when Options closes and configurable batch size.

Original dictionaries, manual translation, separate package exports and finalization into the mod remain available. See the [audit (PT-BR)](docs/AUDIT.md) for demonstrated issues and the limits of each fix.

## Download and run

1. Open [GitHub Actions](https://github.com/caioohe/sims4-translator/actions/workflows/ci.yml) and select a **successful** run for `fix/translation-reliability`.
2. Under **Artifacts**, download **Sims4Translator-Windows**. You must be signed in to GitHub.
3. Extract the **entire ZIP** into a writable folder.
4. Run **`Sims4Translator.exe`**.

Keep `_internal`, `prefs` and `fonts` next to the executable. Artifacts are retained for **14 days**; this fork does not yet have a stable release.

**Validated build of the current integrations:** [run #5](https://github.com/caioohe/sims4-translator/actions/runs/38183900356), code `eecc409`.

## Translation providers

| Service | Integration | Required setup |
| --- | --- | --- |
| **Microsoft Translator** | Official Azure Translator v3 API | Resource key and region; choose **F0** for the free allowance |
| **Gemini** | Official Google `generateContent` API | AI Studio key and a model available to your project |
| **DeepL** | Official API with native batches | **DeepL API** Free or paid key |
| **Google Translate** | Unofficial web page | No key; adjustable interval, subject to blocks and site changes |
| **MyMemory** | MyMemory service | No key in the current integration; subject to service quotas |

Allowances and availability are determined by each service. A Gemini app subscription or DeepL web subscription does not determine API allowances. The program does not create accounts, activate billing or bypass limits with proxies or IP rotation.

### Quick setup

In **Options → General**, select the source and destination languages and configure your provider:

- **Microsoft:** enter the key and exact resource region. Use `brazilsouth` for **Brazil South**; leave the region blank for a **Global** resource. [Full guide (PT-BR)](docs/MICROSOFT.md).
- **Gemini:** enter your key and select a model. Use **Test translation** before starting a large mod. [Guide and Google investigation (PT-BR)](docs/GEMINI_GOOGLE.md).
- **DeepL:** enter your API key. The program selects the Free endpoint for keys ending in `:fx`.

Close Options to save. Gemini and Microsoft appear in the provider list when a key is configured locally or through an environment variable. Gemini accepts `GEMINI_API_KEY`; Microsoft accepts `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION`.

**Texts per batch:** 1–100, default 50, in multiline mode for Gemini/Microsoft. DeepL is capped at 50. Character limits still apply: long texts may produce smaller batches. Larger batches do not guarantee faster translation.

## Translate a mod

1. Open a copy of your `.package` file.
2. Check the languages and choose an automatic translation provider.
3. Translate a small selection first; review names, meaning and variables before processing everything.
4. Save the dictionary to reuse translations in future versions of the mod.
5. Export to a separate `.package` or finalize into the mod, depending on your workflow.
6. Check the package in Sims 4 Studio and test it in the game.

### If translation stops

- **429:** rate limit or quota. Wait and check usage in the provider dashboard.
- **503:** service unavailability or a connection failure reported by the adapter. Try again later.
- **DeepL 456:** translation quota exhausted; retrying does not replenish it.
- **Invalid response:** a batch is not applied if results are missing or protected tokens have changed.

Earlier completed batches remain applied. Recovery checks the package path, original text and languages; it does not replace your dictionary or final export. See [resuming a large mod (PT-BR)](docs/WINDOWS.md#retomar-um-mod-grande).

## Documentation and validation

The detailed technical documents below are currently in **Brazilian Portuguese**. This README provides installation, setup and development instructions in English.

| Document | Contents |
| --- | --- |
| [Technical audit](docs/AUDIT.md) | Confirmed issues, affected files and comparison with Wisdom |
| [Gemini and Google](docs/GEMINI_GOOGLE.md) | Token protection, Gemini integration and HTTP 429 investigation |
| [Microsoft and settings](docs/MICROSOFT.md) | Azure setup, batch size and key persistence |
| [Windows](docs/WINDOWS.md) | Run, build, test and recover progress |
| [Validation results](docs/VALIDATION.md) | Test evidence and limitations |

**146 tests passed on Windows with Python 3.12 and 3.14**, and the PyInstaller build succeeded in [run #5](https://github.com/caioohe/sims4-translator/actions/runs/38183900356). Tests use mocked HTTP and synthetic packages, without real credentials.

This does not certify each model's translation quality, access to your account, all mod variants or in-game results. Real translations require review; Google web blocks remain outside the program's control.

## Development

Windows 10/11 64-bit and **Python 3.12 or 3.14** 64-bit. In PowerShell:

```powershell
git clone --branch fix/translation-reliability https://github.com/caioohe/sims4-translator.git
cd sims4-translator
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

Run tests:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

Build the Windows executable:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name Sims4Translator main.py
Copy-Item prefs dist/Sims4Translator/prefs -Recurse
Copy-Item fonts dist/Sims4Translator/fonts -Recurse
Copy-Item LICENSE dist/Sims4Translator/LICENSE
```

Before distributing a local build, remove `prefs/config.xml`, `prefs/recovery/` and any local dictionaries from it. Prefer the Actions artifact for public distribution: it is built from a clean checkout and checks for private configuration and recovery files.

Actions uses standard `windows-latest` runners, dependency caching and one build after the tests.

**Local files:** `prefs/config.xml` stores keys as text despite UI masking. Do not publish this file, `prefs/recovery/`, dictionaries or personal mods. Bug reports should include the message, version and steps to reproduce; remove credentials from screenshots and logs.

## Interface languages

Interface translations are in `prefs/interface/`. Add a new language with an XML file in that folder. The fork includes the new controls in PT-BR.

## Credits and license

- **Original project:** [voky1 / The Sims 4 Translator](https://github.com/voky1/sims4-translator).
- **Fork maintainer:** [caioohe](https://github.com/caioohe).
- **Original inspiration:** [xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).
- **Roboto:** [Apache 2.0](fonts/LICENSE-Roboto.txt).
- **JetBrains Mono:** [SIL Open Font License 1.1](fonts/LICENSE-JetBrains.txt).

Code is under the [MIT license](LICENSE), preserving the original license and credits. A community project, unaffiliated with EA/Maxis or the translation providers.
