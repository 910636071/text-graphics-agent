# Operation Guide

This guide is for the local web client at `http://127.0.0.1:8012/`.

## First run

1. Start the client:

   ```powershell
   python -m text_graphics_agent.gui
   ```

2. Open `http://127.0.0.1:8012/`.
3. Use the `EN` / `中` language toggle in the top-right toolbar if needed.
4. The app opens on a **chat stream** — type naturally, just like ChatGPT.

## Interface overview

- **Sidebar**: "New chat" button, conversation search, history list (persisted to localStorage), and navigation (Workbench, Approval, Automation, Settings, Guide, diagnostic tools).
- **Chat stream**: The main area. Casual chat gets direct responses. Task requests ("check settings panel layout") are dispatched through the safety pipeline with results returned as cards.
- **Composer**: Bottom input area. Enter sends (Shift+Enter for newline). It stays focused on the request text, sample insertion, model configuration, the Live LLM toggle, and a compact task-scope summary.
- **Task Scope panel**: Collapsed right-side card beside the chat. Set per-task file scope, optional acceptance anchors, browse workspace files, paste paths, or drop files without leaving the conversation.
- **Inspector** (toggle with 👁 button): Right panel showing task scope, task context, permission boundary, and curated memory (labeled untrusted).
- **Topbar**: Title, language toggle, Inspector toggle, quick actions (guide, self-check, automation, settings).

## Core workflow

1. Type a message in the composer. Press Enter to send.
2. If it's casual chat ("hello", "what do you think"), TGA responds directly without dispatching a child agent.
3. If it's a task ("check settings panel layout and give me a fix"), TGA:
   - Decomposes intent and detects contamination (Intent Firewall)
   - Sanitizes the request into a `TaskSpec` (no raw user text reaches the child agent)
   - Routes to the best-matching specialist via `AgentRegistry`
   - The specialist generates an `AgentProposal`
   - 17 constraint checks review the proposal
   - Result appears as a card in the chat stream with accept/reject status and violation details
4. If the proposal is rejected, the chat card shows specific fix suggestions for each violation type.
5. Click "View details" on a task result card to see the full workflow timeline and audit trail.

## Conversation history

- All conversations are saved to `localStorage` automatically.
- The sidebar shows a history list with auto-generated titles (from your first message).
- Use the search box to filter conversations by title or content.
- Click a conversation to load it; hover to reveal the delete button.
- Conversations survive page refresh.

## Settings

Open **Settings** from the sidebar or topbar. Three sections:

1. **Connection**: Select provider (DeepSeek, OpenAI, Gemini, Mock), enter API key, optional model name. Click "Test connection" to verify.
2. **File Scope defaults**: Set fallback allowed file paths for tasks that do not specify a per-task scope. The daily workflow should usually use the right-side **Task Scope** panel beside the chat.
3. **Safety Rules**: Toggle any of the 17 constraint checks on/off (requires approval for high-risk changes).

## Task scope beside chat

The right-side **Task Scope** card is the normal place to narrow a task before sending it. It stays collapsed until you click the composer's **Files** summary or drag a file over the composer.

1. Add files in **Task files**. Use presets (`play.html`, `docs/`, `*.py`) or **Browse files**.
2. You can paste workspace-relative paths directly. If you paste a local absolute path that contains `text-graphics-agent`, the client trims it to a workspace-relative path.
3. You can drop files onto the composer or Task Scope card. The browser cannot expose trustworthy absolute local paths, so the client resolves dropped filenames against the workspace file list when possible.
4. Add short **Acceptance anchors** such as `settings panel` or `NPC dialogue` when the result must prove a specific evidence chain.
5. The composer summary shows whether the task uses defaults or a per-task scope.
6. Per-task scope and anchors are auto-saved with the active conversation and override Settings defaults for that submission only.

## Curated memory

The mother agent accumulates memory across sessions — common scopes, task patterns, violation feedback.

- Memory is **untrusted context**: it helps the mother agent reason but never enters `TaskSpec.objective` and never affects constraint decisions.
- View memories in the **Inspector** panel (open with 👁 button), under "Agent Memory".
- Each memory shows category, confidence percentage, and content.
- Click × to delete individual memories.
- Memories decay over time (5%/day) and are auto-pruned below 15% confidence.

## Live LLM

1. Configure provider and API key in **Settings → Connection**.
2. Test the connection.
3. Check the **Live LLM** checkbox in the composer.
4. Submit a task. The first live call triggers an approval checkpoint.
5. The specialist calls the real LLM, parses the response, and runs auto-repair if the first proposal fails precheck.

## Diagnostic tools

The sidebar's diagnostic section is for platform validation, not daily use:

- **Run Sample**: Demonstrates the dispatch + constraint pipeline.
- **Health Check**: Verifies platform configuration.
- **Baseline Comparison**: Runs the 11-scenario deterministic benchmark.
- **Safety Lab**: Interactive adversarial scenario testing.
- **Diagnostic Search**: Search the adversarial scenario library.

## Safety model

The UI is an operator surface, not the authority layer. Child agents can only propose records. The constraint checker and human approval gates decide whether unsafe actions continue. Curated memory is untrusted and cannot affect constraint decisions.
