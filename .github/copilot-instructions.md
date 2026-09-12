# Agentic AI Workspace Instructions

## Repository Structure

- Keep each agent in its own top-level folder, such as `react/` or `chatbot/`.
- Each agent folder must contain `main.py`, `README.md`, and `__init__.py`.
- Keep reusable Azure OpenAI behavior in `common/`.
- Keep agent-specific prompts, tools, orchestration, demo data, and metrics inside
  the owning agent folder.
- Use the root `requirements.txt` for dependencies shared by the workspace. Add an
  agent-specific requirements file only when its dependencies should not be
  installed for other agents.

## Running And Validation

- Run agents from the repository root with `python -m <agent>.main`.
- Prefer module execution over `python <path>/main.py` so imports from `common/`
  work consistently.
- Before finishing Python changes, run `python3 -m py_compile` on the touched
  modules and run the narrowest relevant test or command.
- Keep each agent README current with its purpose, setup, run command, validation
  command, and file structure.
- Update the root README when adding an agent or changing workspace-wide setup.

## Azure And Secrets

- Read Azure configuration from environment variables or a secret manager.
- Never hard-code API keys, endpoints containing credentials, tokens, or passwords.
- Never add real secrets to `.env.example`, README files, tests, fixtures, or
  commits.
- Preserve the repository's ignore rules for `.env` files, virtual environments,
  caches, and local OS files.

## Change Discipline

- Inspect nearby code before editing and follow existing project patterns.
- Keep changes focused on the requested agent or shared abstraction.
- Do not modify another agent's behavior unless the change is explicitly shared
  and the affected agent is validated.
- Use clear, descriptive names and avoid introducing provider-specific naming in
  shared abstractions unless the abstraction is intentionally provider-specific.
