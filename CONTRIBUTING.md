# Contributing

Thank you for contributing to `etail-marketplaces-sdk`.

---

## Table of contents

1. [Project setup](#1-project-setup)
2. [Code standards](#2-code-standards)
3. [Adding a new platform](#3-adding-a-new-platform)
4. [Development workflow](#4-development-workflow)
5. [Publishing a release](#5-publishing-a-release)

---

## 1. Project setup

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repo
git clone https://github.com/etail-agency/etail_marketplaces_sdk.git
cd etail_marketplaces_sdk

# Install all dependencies (SDK + all extras + dev tools)
uv sync --all-extras
```

Verify everything is working:

```bash
uv run ruff check .      # linter
uv run mkdocs serve      # docs preview at http://127.0.0.1:8000
```

---

## 2. Code standards

| Tool | Purpose | Command |
|---|---|---|
| `ruff` | Lint + format | `uv run ruff check .` |
| `pytest` | Tests | `uv run pytest` |
| `mkdocstrings` | API reference (auto-generated from docstrings) | `uv run mkdocs serve` |

**Rules:**

- All public functions and classes must have docstrings.  The API reference is generated entirely from them — no separate docs file is needed.
- Type-annotate every parameter and return value.  Missing annotations will fail `mkdocs build --strict`.
- Each platform's mapper (`mappers.py`) is the **only** file that should change when a platform's API spec changes.  Keep HTTP logic in `client.py` and field mapping in `mappers.py`.
- The `raw` field on every canonical model must always hold the unmodified platform payload.

---

## 3. Adding a new platform

### Aggregator

```
etail_marketplaces_sdk/aggregators/<name>/
    __init__.py
    client.py    # extends BaseAggregator
    mappers.py   # raw dict → canonical models, no HTTP here
```

1. **`client.py`** — extend `BaseAggregator`, implement `fetch_orders`, `fetch_invoices`, `fetch_shipments`.
2. **`mappers.py`** — one `map_*` function per stream.  Use `_parse_dt()` for datetime parsing and always populate `raw=`.
3. Drop the platform's OpenAPI spec in `specs/aggregators/<name>/openapi.json`.
4. Export the new client in `etail_marketplaces_sdk/__init__.py`.
5. Add the platform to the supported-platforms table in `README.md` and `docs/index.md`.
6. Add a usage example in `docs/getting-started.md` and a reference section in `docs/api/aggregators.md`.

### Marketplace

Same structure under `etail_marketplaces_sdk/marketplaces/<name>/`, extending `BaseMarketplace`.  Add docs under `docs/api/marketplaces.md`.

---

## 4. Development workflow

Work is done on a feature branch and merged to `main` via pull request.

```
main  ←  feature/my-feature  (PR)
```

### Step-by-step

```bash
# 1. Create a branch from main
git checkout main && git pull
git checkout -b feature/my-feature

# 2. Make your changes

# 3. Lint before committing
uv run ruff check .

# 4. Commit with a conventional commit message
#    feat:     new feature
#    fix:      bug fix
#    docs:     documentation only
#    refactor: no behaviour change
#    chore:    tooling / build / deps
git add .
git commit -m "feat: add ShoppingFeed stock stream"

# 5. Push and open a PR against main
git push -u origin feature/my-feature
```

CI runs automatically on every PR:

- `ruff check .` — lint
- (tests, when added) `pytest`

Docs are deployed to GitHub Pages automatically on every merge to `main`.

---

## 5. Publishing a release

> Only maintainers with write access to the repository can publish releases.

Publishing follows a strict sequence.  **Do not skip steps** — the PyPI upload will fail if the tag does not include the version bump and all pending changes.

### 5.1 Decide the version bump

We follow [Semantic Versioning](https://semver.org):

| Change | Command | Example |
|---|---|---|
| Bug fix, doc update, chore | `patch` | `0.2.1` → `0.2.2` |
| New feature, backward-compatible | `minor` | `0.2.1` → `0.3.0` |
| Breaking API change | `major` | `0.2.1` → `1.0.0` |

### 5.2 Update the changelog

Open `CHANGELOG.md` and fill in the `[Unreleased]` section with everything that changed since the last release.  Move it under a new `[x.y.z] - YYYY-MM-DD` heading.

### 5.3 Commit pending changes

Make sure `CHANGELOG.md` and any other outstanding edits are committed to `main` **before** bumping the version:

```bash
git add CHANGELOG.md  # (and any other changed files)
git commit -m "docs: update changelog for x.y.z"
git push
```

### 5.4 Bump the version and create the tag

`bump-my-version` updates `pyproject.toml` and `etail_marketplaces_sdk/__init__.py`, commits the change, and creates a signed annotated git tag — all in one command:

```bash
# Choose one:
uv run bump-my-version bump patch
uv run bump-my-version bump minor
uv run bump-my-version bump major
```

### 5.5 Push the tag

```bash
git push          # push the version-bump commit
git push --tags   # push the new vX.Y.Z tag
```

> **Important:** if you made any more commits after the bump (e.g. a last-minute doc fix), move the tag to the latest commit before pushing:
>
> ```bash
> git tag -fa vX.Y.Z -m "Bump version: A.B.C → X.Y.Z" HEAD
> git push origin vX.Y.Z --force
> ```
>
> The release workflow checks out the exact commit the tag points to.  If the tag is behind `HEAD`, the published package will be missing your latest changes.

### 5.6 Create the GitHub Release

1. Go to **GitHub → Releases → Draft a new release**.
2. Select the tag `vX.Y.Z` you just pushed.
3. Set the title to `vX.Y.Z`.
4. Paste the changelog entries for this version into the description.
5. Click **Publish release**.

Publishing the release triggers the `release.yml` workflow, which:

1. Checks out the exact commit the tag points to.
2. Runs `uv build` to produce the `.whl` and `.tar.gz` artifacts.
3. Generates sigstore attestations.
4. Uploads to PyPI via Trusted Publishing (OIDC — no API token needed).

The package will be live on [PyPI](https://pypi.org/project/etail-marketplaces-sdk/) within a few minutes.

### 5.7 Verify

```bash
pip install "etail-marketplaces-sdk==X.Y.Z"
python -c "import etail_marketplaces_sdk; print(etail_marketplaces_sdk.__version__)"
```
