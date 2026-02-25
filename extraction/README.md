# PDF VLM Extraction Pipeline

Processes 441 raw TIFF page scans of *History of the Retriangulation of
Great Britain* through the Anthropic Claude vision API, extracting
structured text, tables, diagram descriptions, trig point mentions, and
inter-trig relationships into JSON files ready for RAG ingestion.

## Prerequisites

```bash
cd extraction
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

For entity linking (step 3), set the database URL:

```bash
export DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
```

## Pipeline Steps

Run each step in order.  Every step is resumable — re-running skips
already-completed work.

### 1. Convert TIFFs to JPEG

```bash
python 01_convert_tiffs.py --input-dir /path/to/tiff/directory
```

### 2. Extract pages with Claude Vision

```bash
python 02_extract_pages.py
```

Optional flags: `--start 1 --end 441` to process a page range,
`--reprocess 42 105` to re-extract specific pages.

### 3. Link trig point names to database records

```bash
python 03_link_entities.py
```

### 4. Build RAG-ready chunks

```bash
python 04_build_chunks.py
```

### 5. Review extraction quality

```bash
python 05_review.py                # random page
python 05_review.py --page 42      # specific page
python 05_review.py --diagrams     # diagram pages only
python 05_review.py --unmatched    # pages with unmatched trig names
```

## Output

All generated files live in `output/` (gitignored):

| Directory        | Contents                                   |
|------------------|--------------------------------------------|
| `output/jpeg/`   | Converted page images                      |
| `output/pages/`  | Per-page structured JSON from Claude        |
| `output/linked/` | Entity-linked JSON with `trig_id` matches  |
| `output/chunks/` | Final RAG-ready JSONL                      |

## Iteration

1. Run `05_review.py --diagrams` to check diagram extractions
2. Tune the prompt in `prompts/page_extraction.txt`
3. Delete specific `output/pages/NNN.json` files and re-run step 2
4. Re-run steps 3–4 to regenerate linked chunks (no API cost)
