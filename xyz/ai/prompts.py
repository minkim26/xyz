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
