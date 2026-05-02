/**
 * Verify every call<>("cmd") in client.ts has a matching route in the route table.
 * Run: node scripts/check-route-coverage.mjs
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, "../src/api/client.ts"), "utf-8");

// Extract command names from call<>("cmd", ...) calls
const callPattern = /call<[^>]*>\(\s*"([^"]+)"/g;
const usedCommands = new Set();
let m;
while ((m = callPattern.exec(src)) !== null) {
  usedCommands.add(m[1]);
}

// Extract route keys from the routes object (only within the routes block)
const routesStart = src.indexOf("const routes:");
const routesEnd = src.indexOf("};", routesStart);
const routesBlock = src.slice(routesStart, routesEnd);
const routePattern = /^\s+(\w+):\s*\{/gm;
const routeKeys = new Set();
while ((m = routePattern.exec(routesBlock)) !== null) {
  if (["method", "url", "body", "voidOn204"].includes(m[1])) continue;
  routeKeys.add(m[1]);
}

// Check coverage
let exit = 0;

for (const cmd of usedCommands) {
  if (!routeKeys.has(cmd)) {
    console.error(`MISSING ROUTE: "${cmd}" is used in call() but not in routes`);
    exit = 1;
  }
}

for (const key of routeKeys) {
  if (!usedCommands.has(key)) {
    console.warn(`UNUSED ROUTE: "${key}" is in routes but never used in call()`);
  }
}

if (exit === 0) {
  console.log(`OK: ${usedCommands.size} commands, ${routeKeys.size} routes — full coverage`);
}

process.exit(exit);
