# Contributing

Thanks for helping improve Open Ore Mapper.

## Ground Rules

- Do not include proprietary exploration data, private HSI cubes, model weights, or training outputs in pull requests.
- Do not include real spectral library data unless the source URL and redistribution license are documented.
- Keep contributions focused on open algorithms, clean interfaces, tests, documentation, and optional download recipes.

## Development

```bash
python -m pip install -e '.[dev,api]'
pytest -v
ruff check .
mypy src/open_ore_mapper
```

## Spectral Data Contributions

Real spectral data PRs must include:

- Source name
- Source URL
- License or terms URL
- Whether redistribution is allowed
- Exact files or rows included

If redistribution rights are unclear, document the source as a user-provided input recipe instead of bundling the data.
