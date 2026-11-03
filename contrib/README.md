# Contrib

`ci.yml` is the GitHub Actions workflow, kept here because the current token
lacks the `workflow` scope. To activate it:

1. Create `.github/workflows/` and copy `contrib/ci.yml` to `ci.yml`.
2. Push with a token that has the `workflow` scope.

The workflow builds the database and runs conformance, database, interface,
retrieval and MCP checks.
