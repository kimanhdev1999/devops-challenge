import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["dist/"] },
  js.configs.recommended,
  { files: ["src/**/*.js"], languageOptions: { globals: globals.browser } },
  { files: ["scripts/**/*.mjs", "test/**/*.mjs"], languageOptions: { globals: globals.node } },
];
