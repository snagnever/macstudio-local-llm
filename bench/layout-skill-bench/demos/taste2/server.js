const { createServer } = require("http");
const { readFile } = require("fs/promises");
const { join, normalize, extname } = require("path");

const PAGES_DIR = join(__dirname, "pages");
const TOTAL = 5;
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff2": "font/woff2",
};

const server = createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
  try {
    if (path === "/") {
      res.writeHead(302, { Location: "/1" });
      return res.end();
    }
    if (path === "/favicon.ico") {
      res.writeHead(204);
      return res.end();
    }
    const n = Number(path.slice(1));
    if (Number.isInteger(n) && n >= 1 && n <= TOTAL) {
      const buf = await readFile(join(PAGES_DIR, `${n}.html`));
      res.writeHead(200, { "Content-Type": MIME[".html"], "Cache-Control": "no-store" });
      return res.end(buf);
    }
    const rel = normalize(path).replace(/^([/\\])+/, "");
    if (rel.includes("..")) {
      res.writeHead(403, { "Content-Type": "text/plain" });
      return res.end("Forbidden");
    }
    const file = await readFile(join(PAGES_DIR, rel)).catch(() => null);
    if (!file) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      return res.end("Not found");
    }
    res.writeHead(200, { "Content-Type": MIME[extname(rel)] || "application/octet-stream" });
    res.end(file);
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain" });
    res.end("Server error");
  }
});

let port = Number(process.env.PORT) || 3000;
const listen = (p) => {
  server.listen(p, () => {
    console.log(`Iterations live:`);
    for (let i = 1; i <= TOTAL; i++) console.log(`  http://localhost:${p}/${i}`);
  });
};
server.on("error", (err) => {
  if (err.code === "EADDRINUSE" && port < 3010) {
    port += 1;
    listen(port);
  } else {
    throw err;
  }
});
listen(port);
