# vendor/

Third-party tooling parked here for local convenience. **Not part of the
benchmarking pipeline** — these are unrelated infrastructure that happened
to live in this folder when it was organised.

## What's here

- **`web-search-mcp/`** — Local clone of [web-search-mcp](https://www.npmjs.com/package/web-search-mcp),
  a Node.js Model Context Protocol server providing web search + content
  extraction. Run with `npm install && npm run build` from inside the
  subdirectory. The pre-built `dist/` is committed; `node_modules/` is
  ignored (regenerate with `npm install`).

If something in `vendor/` becomes load-bearing for benchmarking, promote
it out to a top-level location with proper documentation.
