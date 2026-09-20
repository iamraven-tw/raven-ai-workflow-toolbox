# WordPress.com operations

Read only the section that matches the user's request. Always discover the live operation and schema before execution.

## Read-only work

Use read-only operations for inventories, content retrieval, statistics, theme context, activity, and diagnostics. Request only fields needed for the task and avoid account, billing, security, or collaborator data unless the user specifically requests it.

Report the site URL, query boundaries, verification time, returned count, and any permission gaps. Do not treat an empty result as proof that content does not exist until filters and site identity are checked.

## Draft creation

1. Read the active theme, presets, allowed blocks, and relevant patterns.
2. Prepare a local preview with title, block content, taxonomy, excerpt, featured media, and intended status.
3. State that the remote result will be a WordPress draft and request confirmation to create it.
4. Create with draft status explicitly set even when draft is the server default.
5. Re-read the created post and inspect `_content_warnings`.

Do not publish as part of a draft test.

## Existing content edits

Read the current post or page immediately before editing. For a small change, list its top-level sections and replace, insert, or remove only the confirmed section. Use locking tokens returned by the live section-list operation when required.

Show the exact before-and-after scope. If the remote item changed after the preview, stop and rebuild the proposal instead of overwriting it.

## Publication and scheduling

Treat publication as a separate operation even if the content draft was already approved. Present:

- Site and content ID.
- Public title and URL or expected slug.
- Final status.
- Scheduled date, time, and timezone when applicable.
- Whether subscribers or integrations may receive notifications.

Execute only after a new explicit confirmation, then re-read the item and verify the stored status and timestamp. A technical save does not replace human review of the public page.

## Media

Confirm the file, destination site, alt text, caption, licensing or provenance when relevant, and whether it will become a featured image. Uploading or generating media is a remote write.

Deleting media is permanent and can break content that references it. Fetch the media record and affected context before requesting deletion confirmation.

## Comments and invitations

Creating or approving a comment can become public immediately. Inviting or resending an invitation sends a real email. Never execute these operations to test connectivity.

## Site administration

Plugin, theme, navigation, global-style, site-setting, collaborator, domain, and billing changes can affect the whole site or account. Read the current state, present the blast radius and rollback path, and obtain operation-specific confirmation.

Never use billing, domain, user removal, permanent deletion, site launch, or email-sending operations as smoke tests.

## Verification after writes

After every confirmed write:

1. Fetch the changed resource by ID.
2. Compare only the confirmed fields and status.
3. Check content warnings and timestamps.
4. Report whether the change is local-only, a WordPress draft, scheduled, or public.
5. State what remains unverified, including public-page appearance or subscriber delivery.
