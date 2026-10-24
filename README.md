# Citizen Observer (thecitizen.observer)

A business unit of Atlas Media Network, LLC. Static site generated with Python (Jinja2 + Markdown), edited through Decap CMS at `/admin/`, deployed on Netlify from this repository.

## How publishing works
- Writers create and edit stories in the newsroom panel at `/admin/` (sign in with GitHub).
- The panel uses an editorial workflow: every draft lives on its own branch as a pull request (Draft → In review → Ready).
- **Publishing = merging into `main`.** Netlify rebuilds the site on every merge. Nothing on a draft branch is public.

## Content
- Stories: `content/stories/*.md` (front matter: title, section, kind, dek, author, date, sources…). Every story needs a byline, a date and linked sources.
- Pages: `content/pages/` (About, Standards, Corrections, Privacy, Contact).
- Election night: `data/election_night.json` (status and race calls, each with source and time). Poll closing times: `data/poll_closing.json`. Official results links: `data/results_urls.json`.
- Site settings and sections: `site.json`. Set `"prelaunch": false` to allow search engine indexing.

## Local build
```
pip install -r requirements.txt
python3 build.py      # writes dist/
```

## Pending before or soon after launch
- Privacy notice: legal review.
- About Us: add funding sources and the editorial team (names and roles) once confirmed.
- Section images are low-resolution crops; replace with the Pexels originals (same file names in `static/img/sections/`).
- Election data: re-check results links and poll closing notes for New Hampshire and North Dakota (set locally).
