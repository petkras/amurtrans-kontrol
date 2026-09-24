"""Check generated static pages for missing local targets and unresolved source links."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent / "site"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        key = "href" if tag == "a" else "src" if tag in {"img", "script"} else None
        if key and props.get(key):
            self.refs.append(props[key])


def main():
    problems = []
    pages = list(ROOT.glob("*.html"))
    for page in pages:
        data = page.read_text(encoding="utf-8")
        if "[[" in data or "```mermaid" in data:
            problems.append(f"{page.name}: unresolved source markup")
        parser = References()
        parser.feed(data)
        for ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            target = page.parent / unquote(url.path)
            if not target.exists():
                problems.append(f"{page.name}: missing {ref}")
    if problems:
        print("\n".join(problems))
        raise SystemExit(1)
    print(f"Checked {len(pages)} pages: all local links resolve")


if __name__ == "__main__":
    main()
