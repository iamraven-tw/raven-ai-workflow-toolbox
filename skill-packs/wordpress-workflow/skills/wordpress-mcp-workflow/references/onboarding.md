# ChatGPT and MCP onboarding

Read this reference whenever a user asks how to connect ChatGPT to WordPress.com, when connecting a new client, repairing authentication, configuring permissions, or handing the workflow to another environment.

## Choose the client route

Use the **ChatGPT Desktop plugin route** when the user says ChatGPT and does not explicitly name Codex or another MCP client. Do not give them Codex CLI commands, `.codex/config.toml`, or OpenCLI setup for this route.

Use the **manual MCP route** only when the user explicitly asks about Codex, Cursor, VS Code, another custom MCP client, or the WordPress.com MCP endpoint.

## ChatGPT Desktop plugin route

Explain the following sequence in clear user-facing language:

1. Confirm that the site has WordPress.com MCP access. A paid WordPress.com plan is the normal long-term prerequisite. A newly created free site may have a temporary MCP grace period, so verify the current plan and MCP availability instead of assuming.
2. Open the ChatGPT desktop application.
3. Go to **Settings → Plugins → Browse directory**.
4. Search for **WordPress.com**, select it, and choose **Add**.
5. Choose **Sign in with WordPress.com**. The user signs in and approves the OAuth connection themselves; never ask for or enter their password, one-time code, token, cookie, or callback data.
6. Open `https://my.wordpress.com/` and select the intended website.
7. Go to **Settings → AI tools → External AI agent access**.
8. Open both **Read** and **Write**. When the user wants ChatGPT to manage the whole site, enable all Read and Write capabilities. If they want a limited workflow, enable only the capabilities required for that workflow.
9. Return to ChatGPT, start a new conversation, type `@WordPress.com`, and select the plugin.
10. List accessible sites and match the intended domain before making changes. Then run the requested real read or write operation and verify the saved result.

Tell the user explicitly that WordPress.com is remote: a new computer does not need WordPress installed locally. The ChatGPT plugin route also does not require `.codex/config.toml`, `codex mcp login wpcom`, or OpenCLI Browser Bridge.

Official references:

- [Edit your WordPress.com site with ChatGPT](https://wordpress.com/support/mcp/connect-chatgpt/)
- [Enable WordPress.com MCP tool access](https://wordpress.com/support/mcp/)

## Connection acceptance

Do not treat plugin installation or a successful OAuth screen as complete proof. After connection:

1. Start a new ChatGPT conversation.
2. Invoke `@WordPress.com`.
3. List accessible sites and match the intended site.
4. Confirm the enabled tools include the required Read and Write capabilities.
5. Run a real task in the requested mode.
6. Re-read the result and report its site, ID, URL, status, and saved state.

## Manual Codex or custom MCP route

Use the sections below only for Codex or another explicitly named MCP client.

### Intake

Collect only what changes the connection design:

- The intended site URL.
- Whether it is hosted on WordPress.com or self-hosted with Jetpack.
- The client's WordPress role and the work they expect the agent to perform.
- Whether the first acceptance test must be read-only.

Do not ask for a WordPress password, application password, token, cookie, or exported browser profile.

### Preferred architecture

For a supported WordPress.com site, use the built-in remote MCP server:

```text
https://public-api.wordpress.com/wpcom/v2/mcp/v1
```

The skill dependency declares this endpoint as `wpcom`. If the client's installer does not provision MCP dependencies, create a project-scoped `.codex/config.toml`:

```toml
[mcp_servers.wpcom]
url = "https://public-api.wordpress.com/wpcom/v2/mcp/v1"
auth = "oauth"
enabled = true
required = false
default_tools_approval_mode = "writes"
```

Validate the file with `codex mcp get wpcom`. If that Codex version rejects `writes`, change only that value to `prompt`, validate again, and record the compatibility fallback.

### WordPress.com permission setup

Ask the client to open WordPress.com Preferences, then AI and MCP. Prefer enabling one specific site instead of the whole account.

Start with the smallest useful tool set:

- Enable only the read groups needed for the acceptance test.
- Keep write tools disabled until a concrete write workflow is approved.
- Keep plugin management, user management, domains, account settings, billing, deletion, and invitations disabled unless explicitly required.

WordPress.com can enable both Read and Write groups when MCP is first turned on. Recheck both lists before OAuth acceptance.

### OAuth handoff

1. Confirm the client asked to connect or authenticate.
2. Run `codex mcp login wpcom`, or use the Authenticate control in Codex.
3. Make sure the authorization page opens in the client's intended browser profile.
4. The client reviews the signed-in account and authorizes the connection themselves.
5. Do not record the generated authorization URL or any callback query parameters.

### OAuth retrieval, verification, and revocation

- Generate a fresh authorization URL by running `codex mcp login wpcom`. The URL is an output of that one PKCE session, not a reusable installation value.
- If browser auto-opening would select the wrong profile, prevent the automatic launch and open the same fresh URL through the approved Chrome bridge profile. Do not persist the URL.
- After the callback, let Codex exchange and retain the access and refresh credentials in its credential store. Do not inspect, export, print, or package credential values.
- Verify the client-visible state with `codex mcp list --json`; `auth_status: o_auth` proves that the OAuth connection exists, but not that the intended site or operations are available.
- Reauthorize with `codex mcp logout wpcom` followed by a fresh login. For immediate server-side revocation, have the client remove the MCP client from WordPress.com Connected Apps.

### Read-only acceptance test

After authentication, start a new Codex task so the MCP catalog is refreshed. Then:

1. Confirm `wpcom` reports OAuth authentication.
2. Discover the live tools.
3. List accessible sites and match the intended URL.
4. Read the active theme and available presets for that site.
5. List a small number of recent posts using only ID, title, status, date, and URL.
6. Confirm that no remote writes were made.

Record each gate separately. A working OAuth token does not prove the intended site or tools are accessible.

### Client handoff

Deliver the skill folder without credentials or customer identifiers. Tell the client that installation can declare the MCP endpoint, but every customer still needs to enable WordPress.com MCP, choose tool permissions, complete their own OAuth authorization, and pass the read-only acceptance test.
