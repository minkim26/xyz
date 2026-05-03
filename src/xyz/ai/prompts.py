"""Prompt templates for Gemini API calls.

All prompts are separated from logic so they can be iterated on
without touching the calling code.
"""

EXPLAIN_PROMPT = """\
You are a developer tools expert helping a developer understand their \
installed packages. The developer has the package "{name}" (version {version}) \
installed via {manager}.

Answer exactly three questions. Use 2-3 sentences for each. Be concise and \
use plain English a junior developer would understand.

1. **What it does** -- What is this package and what is it used for?
2. **Why it's installed** -- What common tools, frameworks, or workflows \
typically depend on this package?
3. **Safe to remove?** -- Is it generally safe to uninstall this package? \
What might break if it is removed?

Format your response with the bold headers shown above, each followed by \
the answer on the same line.\
"""

ORPHAN_RISK_PROMPT = """\
You are a developer tools expert. The package "{name}" (installed via \
{manager}) has been flagged as an orphan -- it was installed as a dependency \
but its parent package has since been removed.

Assess the risk of removing this package. Respond in exactly this format:

**Risk Level:** [Low / Medium / High]
**Explanation:** (2-3 sentences on what might break and whether anything \
commonly depends on this package.)\
"""

CLEANUP_PROMPT = """\
You are a package management expert auditing a developer's machine. \
This person is an active developer — tools like pytest, flake8, black, eslint, \
docker, terraform, ansible, and other dev/ops tools are intentional installs. \
Never flag those for removal.

Installed packages:
{package_list}
{dupes_section}
Use verdict "remove" ONLY for packages that are:
- Officially deprecated or end-of-life with a named successor (e.g. "pkg-resources" \
superseded by "packaging", "nose" superseded by "pytest")
- Clearly a leftover artifact with no modern relevance (e.g. very old Python 2 compat \
shims like "future", "six" when the rest of the stack is Python 3-only)
- An exact functional duplicate of another package already in this list \
(e.g. both "colour" and "colorama" installed, serving identical purpose)

Use verdict "review" ONLY for:
- Packages with the same name installed via two different managers (cross-manager \
duplicates — these are almost always unintentional)
- Two packages in the list that do the exact same job and one is clearly redundant

When flagging similar packages (e.g. many tree-sitter-* variants), group them into \
a single entry for the parent package rather than listing each one separately.

If unsure, skip it. Return a short, focused list — quality over quantity.

Return ONLY a raw JSON array — no markdown fences, no explanation. Each element:
{{"name": "<exact name>", "manager": "<exact manager>", "verdict": "remove"|"review", \
"reason": "<one sentence>"}}

Return [] if nothing clearly meets the above criteria.\
"""

NL_SEARCH_PROMPT = """\
You are a package search assistant. Given the following list of installed \
package names:

{package_names}

The user wants to find packages matching this description: "{query}"

Return ONLY a valid JSON array of matching package names from the list above. \
Include only names that are clearly relevant to the user's description. \
Return an empty array [] if nothing matches. Do not include any explanation, \
markdown formatting, or text outside the JSON array.\
"""
