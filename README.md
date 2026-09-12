# agent-plugins

A command/plugin repository for AI agent harnesses — skills, MCP servers, rules, prompts, and other reusable plugins that can be shared across different agent frameworks.

## Purpose

Central home for agent plugins used across multiple harnesses (e.g. Claude Code, opencode, and other agent tooling). Everything here is designed to be installed or referenced by an agent runtime.

## Structure

```
agent-plugins/
├── skills/       # Agent skills (procedural knowledge + resources)
├── commands/     # Slash-commands / command definitions
├── rules/        # Rules and guidelines injected into agent context
├── mcp/          # MCP server configs and related assets
├── prompts/      # Reusable prompt templates
└── hooks/        # Hook scripts and configurations
```

> Note: directories are created as content lands here. Empty dirs are not tracked by git.

## Usage

Clone the repo and symlink or install the relevant plugin paths into your harness's expected location:

```bash
git clone git@github.com:aaron-c-zhao/agent-plugins.git
```

## Guidelines

- Keep each plugin self-contained and documented with its own README.
- Never commit secrets (API keys, tokens); use environment variables or `.env` files (gitignored).
- Keep harness-agnostic plugins portable; document harness-specific install steps per plugin.

## License

TBD
