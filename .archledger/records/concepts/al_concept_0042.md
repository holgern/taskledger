---
schema_version: 2
id: al_concept_0042
type: concept
title: "YAML front matter serialization"
status: proposed
section: cross_cutting_concepts
order: 30
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:31:00Z"
updated_at: "2026-05-23T12:31:00Z"
---

All canonical records are `.md` files with YAML front matter (`---` delimited) containing structured metadata and a Markdown body. Read/write is handled by `read_markdown_front_matter` and `write_markdown_front_matter` in `taskledger/storage/frontmatter.py`. Models implement `to_dict()` / `from_dict()` for serialization. Schema version and object type fields enforce contract integrity on read.
