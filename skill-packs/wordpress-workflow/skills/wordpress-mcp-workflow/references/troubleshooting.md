# Troubleshooting

Use the matching symptom. Record only verified, reusable behavior; never copy OAuth URLs, callback parameters, tokens, cookies, account emails, or customer identifiers into logs.

## Codex rejects `default_tools_approval_mode = "writes"`

**Symptom:** `codex mcp get` fails to load the project configuration and reports that `writes` is not a supported variant.

**Applies when:** The installed Codex version predates support for the documented `writes` mode.

**Verified solution:** Change the value to `prompt`, then run `codex mcp get <server-name>` again. This is more conservative because every MCP tool call requires approval. Keep WordPress.com's separate `user_confirmed: true` rule for writes.

**Verification:** On Codex CLI `0.142.5`, `writes` failed parsing and `prompt` loaded the remote server successfully.

## Browser bridge is connected but WordPress.com asks for login

**Symptom:** Browser diagnostics report a connected extension, but the WordPress authorization page redirects to the login form.

**Cause:** Browser-bridge connectivity and the authenticated website session are separate. The bridge can be attached to a different Chrome profile from the one the user normally uses.

**Verified solution:** Confirm the intended Chrome profile has the browser bridge extension connected, or let the user sign in manually in the currently connected Chrome profile. Never automate password entry.

**Verification:** A live OpenCLI diagnostic succeeded while the WordPress.com authorization page in that same bridged session still required login.

## MCP endpoint returns HTTP 401 before OAuth

**Symptom:** A direct unauthenticated request to the WordPress.com MCP endpoint returns `401`.

**Interpretation:** This confirms the protected endpoint responded; it does not indicate a valid login or a usable MCP connection.

**Next step:** Complete OAuth and verify with the MCP client. Do not replace OAuth with a WordPress password.

## OAuth opens in the wrong browser

**Symptom:** `codex mcp login` launches a browser profile that is not approved for agent work or does not contain the intended WordPress session.

**Solution:** Cancel before approval, start a fresh login, and open the newly generated one-time authorization URL in the intended browser. Do not save or reuse an old URL; its state, challenge, callback, and listener are tied to that login attempt.

## OAuth callback times out on the WordPress.com login page

**Symptom:** The authorization listener reports a timeout while the browser remains on the WordPress.com login form.

**Verified solution:** Let the expired attempt end, have the user finish signing in to WordPress.com in the same bridged Chrome profile, then start a new OAuth attempt. Never reopen the expired authorization URL. Confirm that no credential was stored before reporting the attempt as safe to retry.

**Verification:** Two fresh attempts reached the correct WordPress.com login page but timed out without callbacks or stored OAuth access while the selected Chrome profile remained signed out.

## Tools are missing after changing WordPress.com settings

**Symptom:** OAuth works, but the expected tools or operations do not appear.

**Solution:** Check both account-level and site-level AI and MCP settings. Refresh only the needed toggles, then restart the MCP client and begin a new task before testing again. Use the live tool list as the source of truth.

## Existing task still requires authentication after successful OAuth

**Symptom:** OAuth login reports success and a fresh client can discover the WordPress MCP tools, but tool calls in the already-running task still return `Authentication required`.

**Verified solution:** Ask the user to restart Codex, then retry a read-only site-list call in the existing task before requesting another OAuth login. Keep all pending website writes paused until the live read succeeds. A configured OAuth status or successful tool discovery alone is not proof that site reads work.

**Verification:** With Codex CLI `0.142.5`, a fresh client discovered 19 WordPress tools while the existing task still failed authentication. After the user restarted Codex, that task successfully read the site list, active theme, saved draft, and page template without another login.

**Limit:** This verifies recovery of the existing connection, not the original reason authentication failed. Do not infer a short token lifetime or a refresh-token defect without relevant evidence.

## Custom template saves but page template assignment is rejected

**Symptom:** `templates.create` and `templates.get` confirm a saved custom block template, but `pages.update` rejects its slug with `Invalid parameter(s): template` and an empty list of accepted templates.

**Applies when:** The approved change is a dedicated template for one specific page, and no existing template for that page would be overwritten.

**Verified solution:** Check the live template inventory, then create the already-approved layout using the WordPress hierarchy slug `page-{page_id}`. Leave the page's explicit `template` value unchanged; the hierarchy selects its dedicated template automatically. Keep the page's draft/publication state unchanged. Do not substitute a shared `page` or `index` template, which would broaden the change to other content.

**Verification:** On a WordPress.com site using Launchit, direct assignment was rejected. A dedicated page-ID template was saved and re-read byte-for-byte, then a freshly loaded authenticated draft preview rendered the new header, full-width main content and footer. Desktop and mobile screenshots confirmed the layout. Refresh the preview before judging the result; an already-open tab may still display the old document.

**Reference:** [WordPress block-template hierarchy](https://developer.wordpress.org/themes/templates/template-hierarchy/#page-hierarchy). Do not remove an unused earlier template without the required deletion approval.
