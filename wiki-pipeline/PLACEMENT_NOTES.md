# Placement Notes

## Lore
Lore is not a separate pageType. It is a subtype of `concept`.

- frontmatter: `pageType: concept`
- callout status: `#lore`
- directory: `concepts/`
- filename/id pattern: `concept.some-slug.md`

## Disambiguation
Disambiguation is navigational, not topical content.

Recommended policy:
- frontmatter: `pageType: concept`
- tags: `[disambiguation]`
- directory: vault root
- filename pattern: `disambig-some-topic.md` or `concept.some-topic-disambiguation.md`

Reason: disambiguation behaves like `index.md` / `WIKI.md` — a navigational page spanning multiple typed areas.
