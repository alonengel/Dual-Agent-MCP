# Archived deployment notes

Supplementary guides kept for reference. These paths were tested but are **not** the
recommended default for CopThief public play.

| Document | Why archived |
|----------|--------------|
| [`ngrok.md`](ngrok.md) | Full Windows walkthrough + free-tier gotchas. Free ngrok proved unreliable for a full `netplay` match; use Cloudflare quick tunnel instead (see [`../DEPLOYMENT.md`](../DEPLOYMENT.md)). |
| [`ngrok.yml.example`](ngrok.yml.example) | Sanitized config template — copy to project-root `ngrok.yml` (git-ignored) and add your authtoken. |
