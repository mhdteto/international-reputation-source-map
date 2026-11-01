# Catalogue data and export

`data/sources.csv` is UTF-8 with one source per row. Every field is required:

`source_id,market,category,name,publisher,url,supports,limits,access_note,language,checked_on,verification,verification_url,verification_note`

source_id must be unique. market must be one of the six named markets or Global. checked_on uses YYYY-MM-DD and must not be after --as-of. verification uses official_page_read, official_link_confirmed or official_indexed_description. URLs must be credential-free HTTP(S), without control characters or whitespace. A syntactically valid URL is not an availability check.

Language labels describe the entry point observed; they are not an exhaustive inventory of every translation offered. `supports` describes the type of assertion a record might help substantiate. It is not a finding that any particular claim was verified.

## Exports

report.json contains the snapshot, scope and all rows. report.html embeds readable cards and local text/market filtering. All source-controlled text is HTML escaped. The builder makes no network requests and includes no third-party script or tracking asset.

Invalid input exits 2 before report writing. Input/output aliases (resolved paths, symlinks and existing hard links) are rejected. Valid runs replace the two report files; keep outputs in a dedicated directory. An I/O error can leave partial exports. No source CSV cells are executed or exported as spreadsheet formulas by this tool.
