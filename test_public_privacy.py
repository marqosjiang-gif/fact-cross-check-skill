#!/usr/bin/env python3
"""Publication guard for this repository.

Locks the public file tree and scans all publishable text files for
private data patterns. Runs offline with the standard library only.

    python3 -m unittest test_public_privacy -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".html", ".svg", ".txt", ".cfg", ".example"}
ALLOWED_TEXT_SUFFIXES = TEXT_SUFFIXES - {".pyc"}

# Patterns that must never appear in public text files.
PATTERNS = {
    "local_absolute_path": re.compile(r"/Users/|/home/|/root/"),
    "credential": re.compile(
        r"gho_[A-Za-z0-9]{10,}"
        r"|sk-[A-Za-z0-9]{16,}"
        r"|ak_[A-Za-z0-9]{12,}"
        r"|xox[baprs]-[A-Za-z0-9-]{10,}"
        r"|Bearer\s+[A-Za-z0-9_\-]{20,}"
    ),
    "internal_tool": re.compile(
        r"westock|ashare|antifragile|"
        r"automation-[0-9]|@skill|hitl_confirmation|Weekly_strategy|"
        r"current_portfolio|boll_items"
    ),
    "personal_name": re.compile(r"Linda|Marc\b|Marqos\b|marqosjiang@gmail"),
    "host_machine": re.compile(r"\.local\b.*MacBook|Marqos-MacBook"),
}

# Domain-scope guard: this repository is a generic fact-checking utility.
# Its docs must not drift into a specific market/investment context.
# NOTE: terms are assembled from fragments so this word list does not
# itself contain the literal strings it bans (the scanner runs on this file too).
_SCOPE_TERM_POOL = (
    "炒" + "股", "股" + "票", "基" + "金", "理" + "财", "证" + "券账户",
    "仓" + "位", "持" + "仓", "个" + "股", "A" + "股", "港" + "股", "美" + "股",
    "资" + "金流", "换" + "手", "K" + "线", "阳" + "线", "阴" + "线",
    "牛" + "市", "熊" + "市", "期" + "货", "期" + "权", "融资" + "余额",
)
SCOPE_PATTERNS = {
    "market_context": re.compile("|".join(re.escape(t) for t in _SCOPE_TERM_POOL)),
}


def public_text_files():
    """Yield (path_object, repo-relative-name) for every publishable text file."""
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".git/", "scripts/__pycache__/")) or rel == ".gitignore":
            continue
        if p.suffix in ALLOWED_TEXT_SUFFIXES:
            yield p, rel


def scan_text(text):
    """Return a list of (rule_name, matched_snippet) hits in one text blob."""
    hits = []
    for name, pattern in {**PATTERNS, **SCOPE_PATTERNS}.items():
        for m in pattern.finditer(text):
            snippet = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ")
            hits.append((name, snippet))
    return hits


class TestFileTree(unittest.TestCase):
    def test_expected_public_files_exist(self):
        names = {rel for _, rel in public_text_files()}
        for expected in (
            "README.md",
            "SKILL.md",
            "test-prompts.json",
            "docs/preview.html",
            "docs/assets/banner-light.svg",
            "docs/assets/banner-dark.svg",
            "references/sources_catalog.md",
            "references/geo_scan_schema.md",
            "scripts/verify.sh",
            "scripts/webcite_cli.py",
        ):
            self.assertIn(expected, names)

    def test_no_cache_or_backup_files_published(self):
        names = {rel for _, rel in public_text_files()}
        for rel in names:
            self.assertFalse(rel.endswith((".pyc", ".bak")), rel)
            self.assertNotIn("__pycache__", rel)
            self.assertFalse("auto-optimize" in rel, rel)
            self.assertFalse("westock_cli" in rel, rel)

    def test_gitignore_covers_caches(self):
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for needle in ("__pycache__", "*.pyc", "*.bak"):
            self.assertIn(needle, gi)


class TestPrivacyScan(unittest.TestCase):
    def test_public_files_have_zero_privacy_hits(self):
        # The guard file itself is excluded: it necessarily contains the
        # pattern literals and planted-probe fixtures. Scanner effectiveness
        # is proven separately by the two planted-leak self-checks below.
        findings = []
        for p, rel in public_text_files():
            if rel == "test_public_privacy.py":
                continue
            hits = scan_text(p.read_text(encoding="utf-8", errors="ignore"))
            for rule, snippet in hits:
                findings.append(f"{rel} [{rule}] ...{snippet}...")
        self.assertEqual(findings, [], "\n".join(findings))

    def test_scanner_detects_a_planted_leak(self):
        probe = ROOT / "_probe_leak.txt"
        try:
            probe.write_text("contact me at /Users/someone/secret and gho_ABCDEFGHIJK\n", encoding="utf-8")
            hits = scan_text(probe.read_text(encoding="utf-8"))
            rules = {rule for rule, _ in hits}
            self.assertIn("local_absolute_path", rules)
            self.assertIn("credential", rules)
        finally:
            probe.unlink(missing_ok=True)

    def test_scanner_detects_a_planted_scope_drift(self):
        probe = ROOT / "_probe_scope.txt"
        try:
            probe.write_text("本工具可用于" + "炒" + "股决策与" + "基" + "金筛选\n", encoding="utf-8")
            hits = scan_text(probe.read_text(encoding="utf-8"))
            rules = {rule for rule, _ in hits}
            self.assertIn("market_context", rules)
        finally:
            probe.unlink(missing_ok=True)

    def test_scope_patterns_cover_key_terms(self):
        for term in _SCOPE_TERM_POOL[:5] + ("".join(["持", "仓"]),):
            self.assertTrue(SCOPE_PATTERNS["market_context"].search(term), term)


class TestDocsConsistency(unittest.TestCase):
    def test_readme_badges_and_nav(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"img\.shields\.io", readme)), 5, "expect exactly 5 badges")
        self.assertEqual(len([l for l in readme.splitlines() if l.startswith("**[")]), 1, "expect exactly 1 nav line")
        self.assertIn("docs/preview.html", readme)
        self.assertIn("banner-light.svg", readme)

    def test_readme_describes_four_channels_and_eight_rules(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("四通道查证", readme)
        self.assertNotIn("三通道", readme)
        for rule in ("窗口覆盖报告日", "影响度评分", "第三源标签"):
            self.assertIn(rule, readme)

    def test_preview_matches_readme_channel_count(self):
        html = (ROOT / "docs/preview.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("CHANNEL ①"), 1)
        self.assertEqual(html.count("CHANNEL ④"), 1)
        self.assertNotIn("三通道", html)
        self.assertIn("#ratings", html)
        self.assertNotIn("<script", html.lower())
        for forbidden in ("src=\"http", "@import", "<link", "http://"):
            self.assertNotIn(forbidden, html.lower().replace("xmlns=\"http", ""), forbidden)

    def test_skill_doc_is_four_channel_version(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("四通道", skill)
        self.assertIn("本地数据终端", skill)
        self.assertNotIn("alice", skill.lower())


if __name__ == "__main__":
    unittest.main()
