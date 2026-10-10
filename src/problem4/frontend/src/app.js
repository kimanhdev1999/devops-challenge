// config.json is written per environment at deploy time, so one build serves every environment.
async function main() {
  const status = document.getElementById("status");
  try {
    const config = await (await fetch("/config.json", { cache: "no-store" })).json();
    const health = await (await fetch(`${config.apiBaseUrl}/healthz`)).json();
    status.textContent = `${config.environment}: API ${health.status} (version ${health.version})`;
  } catch (err) {
    status.textContent = `API unreachable: ${err.message}`;
  }
}

main();
