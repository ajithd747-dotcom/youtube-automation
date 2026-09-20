"""Blender knowledge base: build (ingest docs) + search (BM25 retrieval).

Sources ingested by `python blender_agent/knowledge/kb.py build`:
  * the installed Blender's own API           (dump_bpy_api.py, exact version)
  * cookbook/*.py                             (tested, working snippets -- ranked highest)
  * docs_inbox/*  .md .txt .rst .html .py .pdf   (anything you drop in)
  * --crawl URL [--limit N]                   (official manual / API pages, same-site crawl)
  * learned.jsonl                             (fixes the agent discovered by itself; grows over time)

Retrieval is plain BM25 -- no embeddings, no GPU, ~no RAM -- which suits API lookups well because
queries contain exact identifiers (bpy.ops.mesh.primitive_cube_add, keyframe_insert, ortho_scale...).
"""
import json
import math
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.jsonl"
LEARNED = HERE / "learned.jsonl"
COOKBOOK = HERE / "cookbook"
INBOX = HERE / "docs_inbox"
API_DUMP = HERE / "api_dump.jsonl"
CRAWLED = HERE / "crawled.jsonl"

STOP = set("a an the of to in is it and or for on with as at by be this that from are was if not you can".split())
BOOST = {"skill": 3.5, "cookbook": 3.0, "learned": 2.5, "inbox": 1.6, "crawl": 1.3}


def tokenize(text: str):
    toks = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", text.lower()):
        toks.append(w)
        if "." in w or "_" in w:
            toks.extend(p for p in re.split(r"[._]", w) if len(p) > 1)
    return [t for t in toks if t not in STOP]


def chunk_text(text: str, source: str, title: str, size=1400, overlap=150):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    out, i = [], 0
    while i < len(text):
        j = min(len(text), i + size)
        if j < len(text):  # break on a paragraph/line boundary when possible
            k = max(text.rfind("\n\n", i, j), text.rfind("\n", i + size // 2, j))
            j = k if k > i + size // 3 else j
        out.append({"source": source, "title": title, "text": text[i:j].strip()})
        if j >= len(text):
            break
        i = max(j - overlap, i + 1)
    return out


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buf, self.skip, self.links = [], 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self.skip += 1
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)
        if tag in ("p", "div", "br", "li", "pre", "h1", "h2", "h3", "h4", "tr"):
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def html_to_text(html: str):
    p = _Text()
    p.feed(html)
    return re.sub(r"[ \t]+", " ", "".join(p.buf)), p.links


# ----------------------------------------------------------------------------- build
def find_blender():
    import blender_runner  # local import: lives next to this package
    return blender_runner.find_blender()


def dump_api():
    print("[kb] dumping Blender's Python API from the installed binary...")
    subprocess.run([find_blender(), "-b", "--factory-startup", "--python", str(HERE / "dump_bpy_api.py"), "--", str(API_DUMP)],
                   check=True, stdout=subprocess.DEVNULL)


def crawl(start: str, limit: int):
    """Same-site, same-path-prefix crawl -> crawled.jsonl. Polite: sequential, small limit."""
    prefix = start.rsplit("/", 1)[0] + "/"
    seen, queue, chunks = set(), [start], []
    while queue and len(seen) < limit:
        url = urldefrag(queue.pop(0))[0]
        if url in seen or not url.startswith(prefix) or not re.search(r"(\.html?|/)$", url):
            continue
        seen.add(url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "blender-agent-kb/1.0"})
            html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[kb]   skip {url}: {e}")
            continue
        text, links = html_to_text(html)
        chunks += chunk_text(text, f"crawl:{urlparse(url).netloc}", url.replace(prefix, ""))
        queue += [urljoin(url, l) for l in links]
        print(f"[kb]   crawled {len(seen)}/{limit}: {url}")
    with open(CRAWLED, "a", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c) + "\n")
    print(f"[kb] crawl added {len(chunks)} chunks")


def read_inbox():
    chunks = []
    for f in sorted(INBOX.rglob("*")):
        if not f.is_file() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        try:
            if ext in (".md", ".txt", ".rst", ".py"):
                text = f.read_text(encoding="utf-8", errors="ignore")
            elif ext in (".html", ".htm"):
                text = html_to_text(f.read_text(encoding="utf-8", errors="ignore"))[0]
            elif ext == ".pdf":
                from pypdf import PdfReader  # optional dependency
                text = "\n".join(pg.extract_text() or "" for pg in PdfReader(str(f)).pages)
            else:
                continue
        except Exception as e:
            print(f"[kb]   could not read {f.name}: {e}")
            continue
        chunks += chunk_text(text, "inbox", f.name)
    return chunks


def build(with_api=True):
    chunks = []
    if with_api:
        if not API_DUMP.exists():
            dump_api()
        chunks += [dict(json.loads(l), kind="api") for l in API_DUMP.read_text(encoding="utf-8").splitlines() if l.strip()]
    for f in sorted(COOKBOOK.glob("*.py")):
        chunks.append({"source": "cookbook", "title": f.stem, "text": f.read_text(encoding="utf-8"), "kind": "cookbook"})
    try:  # verified + reference skills are retrieved by the coder like documentation (highest boost)
        import skills as _sk
        for sk in _sk.load_all():
            body = [sk.when, "triggers: " + ", ".join(sk.triggers), sk.procedure()[:1500], sk.section("Pitfalls")[:700],
                    "\n".join(sk.code_blocks())[:1200]]
            chunks.append({"source": f"skill:{sk.status}", "title": f"{sk.id}: {sk.name}", "kind": "skill",
                           "text": "\n".join(body)})
    except Exception as e:
        print(f"[kb] skills not indexed: {e}")
    chunks += [dict(c, kind="inbox") for c in read_inbox()]
    if CRAWLED.exists():
        chunks += [dict(json.loads(l), kind="crawl") for l in CRAWLED.read_text(encoding="utf-8").splitlines() if l.strip()]
    if LEARNED.exists():
        chunks += [dict(json.loads(l), kind="learned") for l in LEARNED.read_text(encoding="utf-8").splitlines() if l.strip()]
    with open(INDEX, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c) + "\n")
    kinds = Counter(c["kind"] for c in chunks)
    print(f"[kb] index built: {len(chunks)} chunks {dict(kinds)}")


# ----------------------------------------------------------------------------- search
class KB:
    def __init__(self):
        if not INDEX.exists():
            build()
        self.docs = [json.loads(l) for l in INDEX.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.tf, self.df, self.len = [], defaultdict(int), []
        for d in self.docs:
            toks = tokenize(d["title"] + " " + d["title"] + " " + d["text"])  # title counts double
            c = Counter(toks)
            self.tf.append(c)
            self.len.append(len(toks))
            for t in c:
                self.df[t] += 1
        self.avg = sum(self.len) / max(len(self.len), 1)

    def search(self, query: str, k=6, kinds=None, max_chars=1500):
        q = tokenize(query)
        n = len(self.docs)
        scores = []
        for i, d in enumerate(self.docs):
            if kinds and d["kind"] not in kinds:
                continue
            s, tf, dl = 0.0, self.tf[i], self.len[i]
            for t in set(q):
                f = tf.get(t)
                if not f:
                    continue
                idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * dl / self.avg))
            if s > 0:
                scores.append((s * BOOST.get(d["kind"], 1.0), i))
        scores.sort(reverse=True)
        return [dict(self.docs[i], score=round(s, 2), text=self.docs[i]["text"][:max_chars]) for s, i in scores[:k]]

    def context(self, query: str, k=6, budget=6000, kinds=None):
        """Formatted retrieval block ready to paste into an LLM prompt."""
        out, used = [], 0
        for r in self.search(query, k=k, kinds=kinds):
            block = f"### [{r['kind']}] {r['title']}\n{r['text']}"
            if used + len(block) > budget:
                break
            out.append(block)
            used += len(block)
        return "\n\n".join(out)


def remember(error: str, fix_code: str, note: str = ""):
    """Persist a discovered error->fix pair so future retrievals surface it."""
    with open(LEARNED, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"source": "learned", "title": "fix: " + error[:80],
                             "text": f"Error seen: {error}\n{note}\nWorking code:\n{fix_code}"}) + "\n")


if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parent))
    args = sys.argv[1:]
    cmd = args[0] if args else "build"
    if cmd == "build":
        if "--refresh-api" in args and API_DUMP.exists():
            API_DUMP.unlink()
        if "--crawl" in args:
            lim = int(args[args.index("--limit") + 1]) if "--limit" in args else 40
            crawl(args[args.index("--crawl") + 1], lim)
        build()
    elif cmd == "search":
        kb = KB()
        for r in kb.search(" ".join(args[1:]), k=5):
            print(f"--- [{r['kind']}] {r['title']}  (score {r['score']})\n{r['text'][:500]}\n")
    else:
        print("usage: kb.py build [--refresh-api] [--crawl URL --limit N] | kb.py search <query>")
