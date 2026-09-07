# Working on Phantom

Read [CLAUDE.md](CLAUDE.md) before changing this repository. Its architecture,
privacy, testing, writing, and planning rules apply to Codex and other coding
agents too. Phantom does not use GSD; preserve its private planning history.

## Releases include communication

When the user asks you to publish a Phantom release, follow
[RELEASING.md](RELEASING.md) through its release-campaign step. A pushed tag and
published package do not finish the release task on their own. Prepare and
schedule the corresponding MailerLite campaigns through the private fadelab.net
workflow, unless the user explicitly excludes release communication.

The owner has requested this as the default release process. Do not ask for the
same authorization again when the current task includes a release. Respect any
narrower user instruction and all tool approval requirements. Never infer a
release request from an ordinary code change, version edit, or test run.

Keep campaign credentials, recipient settings, IDs, drafts, and execution state
out of this public repository. If the private workflow or its credentials are
unavailable, finish the authorized public release work and report the campaign
step as blocked; do not claim it ran or improvise an audience.
