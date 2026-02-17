# Check path changes

GitHub Action that detects whether any file under a given path has changed between two Git refs. Sets an output `changed` to `true` or `false` so you can run later steps only when that path was modified (e.g. skip builds when only docs changed).

## Usage

1. Check out the repository with `fetch-depth: 0` so `github.event.before` is available on `push`.
2. Run this action with an `id` and pass the path to watch.
3. Use `if: steps.<id>.outputs.changed == 'true'` on steps that should run only when the path changed.

### Example workflow

```yaml
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # required so event.before is available
      - id: changes
        uses: OWNER/GitCondition@v1
        with:
          path: mon-dossier
      - name: Step qui s'exécute seulement si modifié
        if: steps.changes.outputs.changed == 'true'
        run: echo "Des fichiers ont changé"
```

Replace `OWNER/GitCondition@v1` with your repo and ref (e.g. `@main` or a tag).

## Inputs

| Input   | Required | Default                    | Description |
|--------|----------|----------------------------|-------------|
| `path` | Yes      | -                          | Path prefix to watch (e.g. `mon-dossier`). Files under this path set `changed=true`. |
| `before` | No     | `github.event.before`      | Git ref for the “before” commit. |
| `after`  | No     | `github.sha`               | Git ref for the “after” commit. |

Override `before` and `after` when you need to compare different refs (e.g. a branch vs `main`).

## Outputs

| Output   | Description |
|----------|-------------|
| `changed` | `"true"` if at least one file under `path` changed between `before` and `after`, otherwise `"false"`. |

## Requirements

- Run after `actions/checkout` with `fetch-depth: 0` when using defaults on `push` events.
- Python 3 and Git available on the runner (default GitHub-hosted runners satisfy this).
