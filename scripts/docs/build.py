"""Build the curated handbook, validate local links and package a static ZIP.

Only explicitly selected documentation enters the delivery; planning and application
files stay outside. Out-of-scope references link to the matching repository commit.
"""

import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".docs-build"
SOURCE = BUILD / "source"
SITE = BUILD / "site"
REFERENCE_FILES = [
    "docs/user-guide.md",
    "docs/domains/configuration.md",
    "docs/domains/roles-and-permissions.md",
    "docs/domains/external-sync-spond.md",
    *[
        f"docs/operations/{name}.md"
        for name in (
            "ops-install",
            "ops-overview",
            "ops-jfctl",
            "ops-backup-restore-update",
            "ops-migration",
            "ops-release",
            "production-security",
            "session-auth",
            "encryption-rotation",
        )
    ],
]
LINK = re.compile(r"(!?\[[^\]\n]*\]\()([^\s)]+)(\))")


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append((tag, attrs[key]))


def check_site():
    pages = {p.resolve(): Page(p.read_text()) for p in SITE.rglob("*.html")}
    failures = []
    for path, page in pages.items():
        for tag, href in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                if tag in ("script", "img", "link") and url.scheme in ("http", "https"):
                    failures.append(f"{path.name}: external runtime asset {href}")
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(SITE.resolve()) or not target.exists():
                failures.append(
                    f"{path.relative_to(SITE.resolve())}: missing target {href}"
                )
            elif (
                url.fragment
                and target in pages
                and unquote(url.fragment) not in pages[target].ids
            ):
                failures.append(
                    f"{path.relative_to(SITE.resolve())}: missing anchor {href}"
                )
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {len(pages)} HTML pages: local links, anchors and assets.")


def main():
    BUILD.mkdir(exist_ok=True)
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    SOURCE.mkdir()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    repo = f"https://github.com/Jugendfeuerwehr-Manager/JF-Manager/blob/{commit}/"
    files = [p for p in (ROOT / "docs/handbook").rglob("*") if p.is_file()]
    files += [ROOT / p for p in REFERENCE_FILES]
    files += [ROOT / "docs/README.md"]
    selected = {p.resolve() for p in files}

    def rewrite(match, source):
        url = urlsplit(match[2])
        if url.scheme or url.netloc or not url.path:
            return match[0]
        target = (source.parent / unquote(url.path)).resolve()
        if not target.exists():
            raise ValueError(
                f"{source.relative_to(ROOT)}: missing source target {match[2]}"
            )
        if target not in selected:
            if not target.is_relative_to(ROOT):
                raise ValueError(f"Link leaves repository: {match[2]}")
            # Images referenced by canonical domain docs become local runtime assets.
            if match[1].startswith("!"):
                dest = SOURCE / target.relative_to(ROOT / "docs")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, dest)
                return match[0]
            return (
                match[1]
                + repo
                + target.relative_to(ROOT).as_posix()
                + ("#" + url.fragment if url.fragment else "")
                + match[3]
            )
        if target.name == "README.md" and target.parent == ROOT / "docs":
            return match[1] + match[2].replace("README.md", "index.md") + match[3]
        return match[0]

    for source in files:
        relative = source.relative_to(ROOT / "docs")
        if relative.as_posix() == "README.md":
            relative = Path("index.md")
        dest = SOURCE / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".md":
            dest.write_text(
                LINK.sub(
                    lambda m, source=source: rewrite(m, source), source.read_text()
                )
            )
        else:
            shutil.copy2(source, dest)
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--clean"],
        cwd=ROOT,
        check=True,
    )
    check_site()
    (SITE / ".nojekyll").touch()
    shutil.make_archive(str(BUILD / "jf-manager-handbook"), "zip", SITE)
    print(f"Delivery: {BUILD / 'jf-manager-handbook.zip'}")


if __name__ == "__main__":
    main()
