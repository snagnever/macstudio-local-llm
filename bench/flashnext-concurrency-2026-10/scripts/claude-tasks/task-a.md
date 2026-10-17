This repository is a small Python package, `inventory`, with a command line in `inventory/cli.py`.

Add a `--format` option to the command line. It takes `text` or `json`. `text` is the default and keeps the current output exactly. `json` prints one JSON object with the keys `items` (the item count) and `total` (the total value as a number rounded to cents), for example `{"items": 2, "total": 2.0}`.

Add a unit test for the `json` format in `tests/test_cli.py`. Run the whole suite with `python3 -m unittest discover -s tests -t .` from the repository root and make sure every test passes. Do not change any other behaviour. When you are done, reply with one line that says which files you changed.
