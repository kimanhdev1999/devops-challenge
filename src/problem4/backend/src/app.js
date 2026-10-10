const express = require("express");

function createApp({ version = process.env.APP_VERSION || "dev" } = {}) {
  const app = express();
  app.disable("x-powered-by");

  // Load balancer and pipeline smoke tests use this; it reports the deployed git SHA.
  app.get("/healthz", (req, res) => {
    res.json({ status: "ok", version });
  });

  app.get("/api/hello", (req, res) => {
    const name = String(req.query.name || "world").slice(0, 64);
    res.json({ message: `hello ${name}` });
  });

  return app;
}

module.exports = { createApp };
