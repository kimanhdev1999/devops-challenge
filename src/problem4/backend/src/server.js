const { createApp } = require("./app");

const port = Number(process.env.PORT || 3000);
const server = createApp().listen(port, () => console.log(`backend listening on ${port}`));

// Finish in-flight requests on SIGTERM (docker stop) instead of dropping them.
process.on("SIGTERM", () => {
  console.log("SIGTERM received, draining");
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 25_000).unref();
});
