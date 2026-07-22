# Security

## Sensitive Data

Do not upload private exploration data, coordinates, survey cubes, credentials, proprietary spectra, API keys, or Earthdata login credentials to public issues, discussions, or pull requests.

## Credential Handling

- Open Ore Mapper does **not** ship with any baked-in credentials.
- NASA Earthdata credentials (for EMIT/RELAB downloads) must be provided at runtime via environment variables, configuration files outside the repository, or interactive prompts.
- Never commit `.env` files, `netrc` files, or any file containing secrets.

## Reporting Vulnerabilities

Report vulnerabilities through **GitHub private vulnerability reporting**:

1. Navigate to the repository's **Security** tab.
2. Click **Report a vulnerability** (or **Advisories → New advisory**).
3. Provide a clear description, steps to reproduce, and affected versions.

Do **not** report vulnerabilities via public issues, discussions, or pull requests.

If the repository does not yet have private reporting enabled, check the repository Settings > Security > Private vulnerability reporting to confirm availability. Do not file a public issue with vulnerability details.

## Supported Versions

The project is pre-1.0. Security fixes are applied to the latest commit on the default branch. No backports are made to earlier versions.

## Dependency Scanning

Dependencies are managed via `uv` / `pyproject.toml`. Keep them updated and review Dependabot or similar alerts when available.
