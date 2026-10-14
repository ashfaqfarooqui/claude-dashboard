# Python guidelines

## Environment and dependencies

- Use `uv` exclusively. Never call `pip install` in a project with `pyproject.toml` / `uv.lock`.
- `uv add` / `uv remove` for dependencies, `uv sync` to install the lock, `uv init` for new
  projects.
- Run everything through `uv run` (`uv run pytest`, `uv run python -m …`) so the locked
  environment is used, not the system Python.
- Lint and format with what the project configures (`[tool.ruff]` in `pyproject.toml` →
  `uv run ruff check <files>`, `uv run ruff format <files>`), on changed files only.

## Checking docs before use

- Stdlib: `uv run python -c "help(module.func)"`, or read the source.
- Third-party: the docs for the version in `uv.lock`, or the installed source under
  `.venv/lib/python*/site-packages/`.

## Reuse

- Check `pyproject.toml` for dependencies that already cover the need before adding one.
- Prefer the standard library over a new dependency for something it already does.
