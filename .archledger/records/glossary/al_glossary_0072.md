---
schema_version: 2
id: al_glossary_0072
type: glossary_term
title: "Front Matter"
status: proposed
section: glossary
order: 120
date: "2026-05-23"
term: "Front Matter"
definition: "The YAML metadata block at the top of a canonical record file, delimited by ---."
body_format: markdown
created_at: "2026-05-23T12:31:26Z"
updated_at: "2026-05-23T12:31:26Z"
---

The YAML metadata block at the top of a canonical record file, delimited by `---`. Contains structured fields (ID, type, status, dates, schema version) parsed by `read_markdown_front_matter` in `taskledger/storage/frontmatter.py`. The body after the front matter is Markdown content.
