# Repository Guidelines

## Project Structure & Module Organization
Core HTTP routing stays in `server.js`; all reusable logic lives in `lib/`. Key modules include `lib/openaiClient.js` for cached client instances, `lib/promptBuilder.js` for request cleaning, `lib/responseService.js` for Responses API calls, and `lib/responseFormatter.js` for Markdown normalization. Client assets sit under `public/`, Node test specs under `tests/`, automation scripts in `scripts/`, and daily audit output in `logs/`. Add new shared helpers to `lib/` and keep them pure so tests remain isolated from network calls.

## Build, Test, and Development Commands
Install dependencies with `npm install`. Use `npm start` to run the Express server (defaults to port 3000) and `npm run dev` for hot reload via nodemon. Execute `npm test` to run Node’s native test runner with c8 coverage. Enforce style and catch unused imports with `npm run lint`. Database utilities are available through `npm run setup:db` and `npm run load:knowledge` when preparing local fixtures.

## Coding Style & Naming Conventions
The project ships ECMAScript modules with 2-space indentation, single quotes, and trailing commas enforced by ESLint (`.eslintrc.cjs`). Name pure helpers with verb-noun patterns such as `buildPromptVariables`, and keep OpenAI-facing services noun-based (`responseService`). Align front-end IDs with server payload keys (e.g., `current-inp` → `current_inp_abx`).

## Testing Guidelines
Place deterministic specs in `tests/` using descriptive filenames like `promptBuilder.test.js`. Run `npm test` locally before pushing; coverage must stay above 85% as reported by c8. Avoid hitting live APIs—stub inputs through helper exports instead. Investigate new utilities by exporting pure functions and asserting against small fixtures.

## Commit & Pull Request Guidelines
Write imperative commit titles under 60 characters (e.g., `Switch to Responses API`). Summaries should call out workflow or formatting changes that affect clinicians. Pull requests need a brief problem statement, testing commands executed, and rendered Markdown evidence whenever UI output shifts. Always request review to preserve response formatting norms.

## Security & Configuration Tips
Follow `.env.example` and set `OPENAI_API_KEY`, `OPENAI_PROMPT_ID`, and `OPENAI_PROMPT_VERSION` before running the server. Never log secrets—`recordAuditEntry` already redacts tokens. Rotate `logs/` regularly or point the logger at a secure directory via deployment configuration.
