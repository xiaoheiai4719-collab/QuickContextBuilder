# Security and privacy

QuickContextBuilder reads local files and writes a local `.qcb` cache. It does not send network requests, download models, import repository modules, run project tests or execute inspected source. When Git is installed it invokes read-only Git commands, disabling fsmonitor and hooks for those calls. Use a trusted Git/Python installation and a normal local checkout.

Default defenses are deliberately limited:

- Reject symlinked source files/directories and symlinked cache destinations
- Reject paths outside the selected root, binary/non-UTF-8 input, files over 512 KB and recognized private-key content
- Exclude `.env*`, credential/secret-named paths, key formats and common dependency/build/config directories
- Honor Git ignore selection plus exclusion-only `.qcbignore`
- Redact some quoted credential assignments and common token formats while preserving line numbers
- Store newly created cache files with restrictive permissions and use atomic replacement
- Revalidate current selected bytes and displayed lines before returning a pack

**This is not a secret scanner, DLP system, prompt-injection defense, or sandbox.** Unknown token formats, personal data and confidential business logic can remain. Source comments, filenames, queries, history titles and case links are untrusted content. The trust label helps a downstream agent distinguish data from instructions; it does not guarantee the agent will obey that boundary. Prefer JSON for automated consumption. Review every pack before uploading it elsewhere.

Caches include source excerpts. Add `.qcb/` to your repository's `.gitignore`; never commit or share it. Existing directory permissions remain under your control. Do not reuse untrusted/pre-populated caches. Current source text is rechecked, but cache metadata is not authenticated. Concurrent hostile local filesystem changes and resource-exhaustion attacks are outside the security boundary. The tool is meant for repositories you are authorized to read, under your own local OS account.

Report security concerns through the repository's private security-reporting feature if it is enabled. If it is not, open a minimal issue requesting a private contact without including secrets, private source or exploitable details. No private reporting channel is promised until configured by maintainers.
