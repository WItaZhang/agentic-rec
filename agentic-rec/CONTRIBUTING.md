# Contributing

- Add a component: subclass the base class in the relevant package, decorate with
  `@registry.register("<kind>", "<name>")`, add a test in `tests/`, and mention it in
  the README table.
- Add a paper: one row in `docs/component-matrix.md`, a paragraph in `docs/survey.md`
  under the right year, a BibTeX entry in `docs/references.bib`, and, when the
  architecture is expressible, a `configs/<name>.toml`.
- Keep the package free of runtime dependencies. Optional integrations go behind
  lazy imports.
- Run `ruff check .` and `pytest` before opening a pull request.
