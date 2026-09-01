<!-- kodela:protocol:start -->
## Kodela context protocol

This repo uses **Kodela** to capture the *why* behind code changes. As an AI agent working here:

- **Before editing** a non-trivial file → call `kodela_get_context` to see prior reasoning.
- **After every file edit** → call `kodela_annotate_file` (why_changed, problem_solved, risk).
- **At the end of the session** → call `kodela_session_end`.
- Record significant choices with `kodela_record_decision`.

Kodela uses a two-path capture architecture. The MCP fast path above is preferred when your agent can drive it (highest-quality capture — you author the *why* in your own words). The background watcher is **ground-truth capture for tools that can't drive MCP**: it observes every file change via git + filesystem and a 6-layer UBA attribution stack, so the *what* is recorded even when no MCP call ever fires. The async synthesis worker fills in the *why* from diff + chat transcript when the agent didn't.
<!-- kodela:protocol:end -->
