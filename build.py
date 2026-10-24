#!/usr/bin/env python3
"""Citizen Observer — static site generator.

Usage:  python3 build.py   -> writes dist/
Site settings: site.json. Stories: content/stories/*.md. Pages: content/pages/*.md.
Election data: data/*.json. Stories and pages are edited from the newsroom panel (/admin/).
"""
import shutil, json, hashlib, datetime as dt, re
from email.utils import format_datetime
from pathlib import Path
import markdown, yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
ET = dt.timezone(dt.timedelta(hours=-5))
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
SITE["v"] = hashlib.md5(b"".join((ROOT / "static" / f).read_bytes() for f in ("site.css", "site.js"))).hexdigest()[:8]
SECTIONS = SITE["sections"]
SEC = {s["slug"]: s for s in SECTIONS}


def data(name, default):
    f = ROOT / "data" / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


RESULTS = data("results_urls.json", {})
CLOSING = data("poll_closing.json", {})
NIGHT = data("election_night.json", {"status": "", "updates": []})

STATES = {"al":"Alabama","ak":"Alaska","az":"Arizona","ar":"Arkansas","ca":"California","co":"Colorado","ct":"Connecticut","de":"Delaware","dc":"District of Columbia","fl":"Florida","ga":"Georgia","hi":"Hawaii","id":"Idaho","il":"Illinois","in":"Indiana","ia":"Iowa","ks":"Kansas","ky":"Kentucky","la":"Louisiana","me":"Maine","md":"Maryland","ma":"Massachusetts","mi":"Michigan","mn":"Minnesota","ms":"Mississippi","mo":"Missouri","mt":"Montana","ne":"Nebraska","nv":"Nevada","nh":"New Hampshire","nj":"New Jersey","nm":"New Mexico","ny":"New York","nc":"North Carolina","nd":"North Dakota","oh":"Ohio","ok":"Oklahoma","or":"Oregon","pa":"Pennsylvania","ri":"Rhode Island","sc":"South Carolina","sd":"South Dakota","tn":"Tennessee","tx":"Texas","ut":"Utah","vt":"Vermont","va":"Virginia","wa":"Washington","wv":"West Virginia","wi":"Wisconsin","wy":"Wyoming"}

MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]


def as_dt(d):
    if not d:
        return None
    if isinstance(d, str):
        d = dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
    if isinstance(d, dt.date) and not isinstance(d, dt.datetime):
        d = dt.datetime(d.year, d.month, d.day, 9)
    if d.tzinfo is None:
        d = d.replace(tzinfo=ET)
    return d.astimezone(ET)


def apdate(d):  # AP style: Oct. 23, 2026
    return f"{MONTHS[d.month-1]} {d.day}, {d.year}"


def aptime(d):
    h = d.hour % 12 or 12
    m = "" if d.minute == 0 else f":{d.minute:02d}"
    return f"{h}{m} {'a.m.' if d.hour < 12 else 'p.m.'} ET"


env.filters["apdate"] = apdate
env.filters["aptime"] = aptime
env.filters["iso"] = lambda d: d.isoformat()
md = lambda s: markdown.markdown((s or "").strip(), extensions=["extra", "sane_lists"])


def front(f):
    raw = f.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None, None
    _, head, body = raw.split("---", 2)
    return (yaml.safe_load(head) or {}), body


def load_stories():
    out = []
    for f in sorted((ROOT / "content" / "stories").glob("*.md")):
        m, body = front(f)
        if m is None or m.get("draft") or m.get("section") not in SEC:
            continue
        m["date"] = as_dt(m["date"])
        m["updated"] = as_dt(m.get("updated"))
        m["slug"] = f.stem
        m["url"] = f"/{m['section']}/{f.stem}/"
        m["sec"] = SEC[m["section"]]
        m["html"] = md(body)
        m["minutes"] = max(1, round(len(body.split()) / 230))
        m.setdefault("author", "Citizen Observer Editorial")
        m.setdefault("ai_assisted", True)
        m.setdefault("sources", [])
        m.setdefault("corrections", [])
        if not m.get("image"):
            m["image"] = SEC[m["section"]]["image"]
            m["image_alt"] = ""
        m["thumb"] = m["image"]
        yt = re.search(r"(?:youtu\.be/|v=|embed/)([\w-]{11})", m.get("video_url") or "")
        m["yt"] = yt.group(1) if yt else None
        out.append(m)
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def load_pages():
    pages = {}
    for f in sorted((ROOT / "content" / "pages").glob("*.md")):
        m, body = front(f)
        if m is None:
            continue
        m["slug"] = f.stem
        m["html"] = md(body)
        m["updated"] = as_dt(m.get("updated"))
        pages[f.stem] = m
    return pages


def write(path, html):
    p = DIST / path.strip("/") / "index.html" if not path.endswith(".html") else DIST / path.strip("/")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    stories = load_stories()
    pages = load_pages()
    now = dt.datetime.now(ET)
    eday = dt.datetime.fromisoformat(SITE["election_date"]).replace(tzinfo=ET)
    common = dict(site=SITE, sections=SECTIONS, today=now, election_days=(eday.date() - now.date()).days,
                  latest=stories[:5])
    render = lambda tpl, **kw: env.get_template(tpl).render(**common, **kw)
    urls = ["/"]

    # Home slots
    lead = next((s for s in stories if s.get("featured")), stories[0] if stories else None)
    rest = [s for s in stories if s is not lead]
    picks = [s for s in rest if s.get("editors_pick")][:3]
    picks += [s for s in rest if s not in picks][:3 - len(picks)]
    used = set(id(s) for s in [lead] + picks)
    river = [s for s in rest if id(s) not in used][:4]
    blocks = [(sec, [s for s in stories if s["section"] == sec["slug"]][:3])
              for sec in SECTIONS if sec["slug"] not in ("fact-check", "video")]
    blocks = [b for b in blocks if b[1]]
    write("/", render("home.html", page="home", path="/", ptitle="", pdesc=SITE["description"], lead=lead, picks=picks, river=river, blocks=blocks,
                      factchecks=[s for s in stories if s["section"] == "fact-check"][:3],
                      videos=[s for s in stories if s["section"] == "video"][:3]))

    # Sections
    for sec in SECTIONS:
        items = [s for s in stories if s["section"] == sec["slug"]]
        write(f"/{sec['slug']}/", render("section.html", page=sec["slug"], sec=sec, items=items,
              path=f"/{sec['slug']}/", ptitle=sec["name"], pdesc=sec["desc"]))
        urls.append(f"/{sec['slug']}/")

    # Stories
    for s in stories:
        related = [r for r in stories if r is not s and r["section"] == s["section"]][:4]
        write(s["url"], render("story.html", page=s["section"], s=s, related=related, path=s["url"], ptitle=s["title"], pdesc=s.get("dek",""), ogimg=s["image"] if s.get("image_alt") else None))
        urls.append(s["url"])

    # Election hub
    names = STATES
    groups = []
    for g in CLOSING.get("groups", []):
        rows = [dict(code=c, name=names[c], close=CLOSING["states"][c]["most_et"],
                     last=CLOSING["states"][c]["last_et"], note=CLOSING["states"][c].get("note", ""),
                     url=RESULTS.get(c, {}).get("url"), authority=RESULTS.get(c, {}).get("authority", "State election office"))
                for c in g["states"] if c in names]
        if rows:
            groups.append(dict(et=g["et"], rows=sorted(rows, key=lambda r: r["name"])))
    az = sorted([r for g in groups for r in g["rows"]], key=lambda r: r["name"])
    upd = []
    for u in NIGHT.get("updates", []):
        u = dict(u); u["time"] = as_dt(u["time"]); upd.append(u)
    upd.sort(key=lambda u: u["time"], reverse=True)
    night = dict(NIGHT); night["updates"] = upd; night["updated"] = as_dt(NIGHT.get("updated"))
    write("/elections/2026/", render("hub.html", page="elections", path="/elections/2026/", ptitle="Election 2026: Midterm Election Hub", pdesc="Poll closing times and links to every state\u2019s official results page for the Nov. 3, 2026, midterm elections.", groups=groups, az=az, night=night,
                                     n_links=sum(1 for r in az if r["url"]),
                                     stories=[s for s in stories if s["section"] == "elections"][:6],
                                     sources=CLOSING.get("sources", [])))
    urls.append("/elections/2026/")

    # Static pages
    for slug, p in pages.items():
        write(f"/{slug}/", render("page.html", page=slug, p=p, path=f"/{slug}/", ptitle=p["title"], pdesc=p.get("dek","")))
        urls.append(f"/{slug}/")

    # Search index + page
    (DIST / "search.json").write_text(json.dumps(
        [dict(t=s["title"], d=s.get("dek", ""), u=s["url"], s=s["sec"]["name"], dt=apdate(s["date"])) for s in stories]),
        encoding="utf-8")
    write("/search/", render("search.html", page="search", path="/search/", ptitle="Search", pdesc=""))

    # 404
    write("404.html", render("page.html", page="404", path="/404", ptitle="Page not found", pdesc="", p=dict(
        title="Page not found", dek="This address does not exist or has moved.",
        html='<p><a href="/">Go to the home page</a> or <a href="/search/">search the site</a>.</p>')))

    # RSS, sitemap, robots, headers
    base = f"https://{SITE['domain']}"
    items = "".join(
        f"<item><title>{esc(s['title'])}</title><link>{base}{s['url']}</link><guid>{base}{s['url']}</guid>"
        f"<pubDate>{format_datetime(s['date'])}</pubDate><description>{esc(s.get('dek',''))}</description>"
        f"<category>{esc(s['sec']['name'])}</category></item>" for s in stories[:40])
    (DIST / "rss.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Citizen Observer</title>'
        f'<link>{base}/</link><description>{esc(SITE["description"])}</description><language>en-us</language>'
        f'{items}</channel></rss>', encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    pre = SITE.get("prelaunch")
    (DIST / "robots.txt").write_text(("User-agent: *\nDisallow: /\n" if pre else "User-agent: *\nAllow: /\nDisallow: /admin/\n")
                                     + f"Sitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (DIST / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n"
        + ("  X-Robots-Tag: noindex\n" if pre else "")
        + "/static/*\n  Cache-Control: public, max-age=604800\n/admin/*\n  X-Robots-Tag: noindex\n", encoding="utf-8")
    shutil.copytree(ROOT / "static", DIST / "static")
    if (ROOT / "admin").exists():
        shutil.copytree(ROOT / "admin", DIST / "admin")
    print(f"dist/ ready: {len(urls)} pages, {len(stories)} stories, {len(pages)} static pages, "
          f"{sum(1 for r in az if r['url'])} official results links")


if __name__ == "__main__":
    build()
