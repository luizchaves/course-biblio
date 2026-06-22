#!/usr/bin/env python3
"""
Fetch the course list from Koha (opac-course-reserves.pl) via Playwright,
then update subjects.json with reserves and bibtex files for each discipline.
ISBNs are extracted from each book's opac-detail page.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent / "course" / "engenharia-de-software"
SUBJECTS_FILE = PROJECT_ROOT / "koha" / "reserva-de-curso" / "subjects.json"
BIBTEX_DIR = PROJECT_ROOT / "bibtex"
BIBTEX_RELATIVE_PREFIX = "bibtex"
KOHA_BASE = "https://biblioteca.ifpb.edu.br/cgi-bin/koha/"

# Runtime maps: bib (str) ↔ key (str), built at startup and updated as we go
_bib_to_key: dict[str, str] = {}
_key_to_bib: dict[str, str] = {}

# Cache: url → isbn list, populated from existing subjects.json at startup
_isbn_cache: dict[str, list[str]] = {}


def add_bibtex_isbns_if_missing(content: str, isbns: list[str]) -> str:
    """Add fallback ISBNs only when the downloaded BibTeX has no ISBN field."""
    if not isbns or re.search(r"^\s*isbn\s*=", content, re.IGNORECASE | re.MULTILINE):
        return content

    closing_brace = content.rfind("}")
    if closing_brace == -1:
        return content

    before = content[:closing_brace].rstrip()
    if not before.endswith(","):
        before += ","
    isbn_field = f"\n\tisbn = {{{', '.join(isbns)}}}\n"
    return before + isbn_field + content[closing_brace:]


def sync_missing_bibtex_isbns(subjects: list[dict]) -> int:
    """Fill missing BibTeX ISBN fields with values from subjects.json."""
    isbn_by_path: dict[str, list[str]] = {}
    for subject in subjects:
        for reserve in subject.get("reservas", []):
            bibtex_path = reserve.get("bibtex")
            if not bibtex_path:
                continue
            merged = isbn_by_path.setdefault(bibtex_path, [])
            for isbn in reserve.get("isbn", []):
                if isbn not in merged:
                    merged.append(isbn)

    updated = 0
    for relative_path, isbns in isbn_by_path.items():
        bibtex_file = PROJECT_ROOT / relative_path
        if not bibtex_file.is_file():
            continue
        content = bibtex_file.read_text(encoding="utf-8")
        new_content = add_bibtex_isbns_if_missing(content, isbns)
        if new_content != content:
            bibtex_file.write_text(new_content, encoding="utf-8")
            updated += 1
    return updated


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def is_year_only(key: str) -> bool:
    return bool(re.match(r"^\d{4}[a-z]?$", key))


def author_from_bibtex(content: str) -> str:
    """Extract first author (or editor) last name from bibtex content."""
    for field in ("author", "editor"):
        m = re.search(rf"{field}\s*=\s*\{{([^}}]+)\}}", content, re.IGNORECASE)
        if m:
            first = m.group(1).split(" and ")[0].strip()
            last = first.split(",")[0].strip()
            last = re.sub(r"[^A-Za-zÀ-ÿ]", "", last)
            if last:
                return last.upper()
    return ""


def year_from_num_chamada(num_chamada: str) -> str:
    m = re.search(r"\bc?(\d{4})\b", num_chamada)
    return m.group(1) if m else "0000"


def author_from_num_chamada(autor_cell: str) -> str:
    """Extract last name from Koha's 'Lastname, Firstname' author cell."""
    last = autor_cell.split(",")[0].strip()
    last = re.sub(r"[^A-Za-zÀ-ÿ]", "", last)
    return last.upper()


def cutter_letter(num_chamada: str) -> str:
    """Fallback: first letter of Cutter code (e.g. 'G' from 'G943')."""
    m = re.search(r"\s([A-Z])\d+", num_chamada)
    return m.group(1) if m else "X"


def assign_key(base_key: str, bib: str) -> str:
    """Return the key to use for this bib, adding a/b/c suffix on collision."""
    if bib in _bib_to_key:
        return _bib_to_key[bib]

    candidate = base_key
    for suffix in [""] + list("abcdefghijklmnopqrstuvwxyz"):
        candidate = base_key + suffix
        if candidate not in _key_to_bib:
            _bib_to_key[bib] = candidate
            _key_to_bib[candidate] = bib
            return candidate
    return base_key  # should never reach here


def extract_isbns(html: str) -> list[str]:
    """Extract ISBNs from a Koha opac-detail page.

    Primary source: <span property="isbn">VALUE</span>
    Fallback:       data-isbn="VALUE" attribute on the cover slider div.
    """
    found = []

    for m in re.finditer(r'<span\s+property="isbn">([^<]+)</span>', html, re.IGNORECASE):
        raw = re.sub(r"[\s\-]", "", m.group(1))
        digits = re.sub(r"[^0-9X]", "", raw.upper())
        if len(digits) in (10, 13):
            found.append(digits)

    if not found:
        m = re.search(r'data-isbn="([^"]+)"', html)
        if m:
            raw = re.sub(r"[\s\-]", "", m.group(1))
            digits = re.sub(r"[^0-9X]", "", raw.upper())
            if len(digits) in (10, 13):
                found.append(digits)

    return list(dict.fromkeys(found))


def fetch_isbn(url: str) -> list[str]:
    """Fetch a book detail page and return its ISBN list (cached)."""
    if url in _isbn_cache:
        return _isbn_cache[url]
    try:
        html = fetch(url)
        isbns = extract_isbns(html)
    except Exception as e:
        print(f"    WARNING: ISBN fetch failed for {url}: {e}")
        isbns = []
    _isbn_cache[url] = isbns
    return isbns


def build_initial_maps(subjects: list[dict]) -> None:
    """Populate _bib_to_key/_key_to_bib and _isbn_cache from subjects.json."""
    for s in subjects:
        for r in s.get("reservas", []):
            # ISBN cache
            url = r.get("url", "")
            if url and "isbn" in r:
                _isbn_cache[url] = r["isbn"]

            # BibTeX key map
            bib_m = re.search(r"biblionumber=(\d+)", url)
            bibtex_path = r.get("bibtex", "")
            if not (bib_m and bibtex_path):
                continue
            bib = bib_m.group(1)
            key = Path(bibtex_path).stem
            if is_year_only(key):
                # Remove the stale file so it gets re-downloaded with a proper key
                stale = BIBTEX_DIR / f"{key}.bib"
                if stale.exists():
                    stale.unlink()
                    print(f"  Removed stale year-only bibtex: {key}.bib")
                continue
            _bib_to_key[bib] = key
            _key_to_bib[key] = bib


def download_bibtex(bib: str, key: str) -> str | None:
    """Download bibtex from Koha, rewrite citation key, save. Returns filename or None."""
    url = f"{KOHA_BASE}opac-export.pl?op=export&bib={bib}&format=bibtex"
    try:
        content = fetch(url)
    except Exception as e:
        print(f"    WARNING: could not fetch bibtex for {bib}: {e}")
        return None

    if not content.strip().startswith("@"):
        print(f"    WARNING: invalid bibtex for {bib}")
        return None

    content = re.sub(r"^@book\{[^,]+,", f"@book{{{key},", content, count=1)
    filename = f"{key}.bib"
    (BIBTEX_DIR / filename).write_text(content, encoding="utf-8")
    return filename


def resolve_key(bib: str, autor_cell: str, num_chamada: str) -> tuple[str, str | None]:
    """
    Determine the bibtex key for this bib.
    Returns (key, bibtex_content_or_None).
    bibtex_content is returned when we had to pre-download to get the author.
    """
    year = year_from_num_chamada(num_chamada)

    if autor_cell:
        last = author_from_num_chamada(autor_cell)
        base = f"{last}{year}"
        return assign_key(base, bib), None

    # Empty author cell: download bibtex first to extract author
    url = f"{KOHA_BASE}opac-export.pl?op=export&bib={bib}&format=bibtex"
    try:
        content = fetch(url)
        time.sleep(0.2)
    except Exception as e:
        print(f"    WARNING: could not pre-fetch bibtex for {bib}: {e}")
        base = cutter_letter(num_chamada) + year
        return assign_key(base, bib), None

    last = author_from_bibtex(content)
    if not last:
        last = cutter_letter(num_chamada)

    base = f"{last}{year}"
    key = assign_key(base, bib)
    # Rewrite citation key in the already-fetched content
    content = re.sub(r"^@book\{[^,]+,", f"@book{{{key},", content, count=1)
    return key, content


def parse_reserves(course_html: str) -> list[tuple[str, dict]]:
    section = re.search(
        r'id="course_reserves"(.*?)<!-- / #course_reserves', course_html, re.DOTALL
    )
    if not section:
        return []

    reserves = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section.group(1), re.DOTALL)
    for row in rows:
        link = re.search(r'href="(opac-detail\.pl\?biblionumber=(\d+))"', row)
        if not link:
            continue
        bib = link.group(2)
        url = KOHA_BASE + link.group(1)

        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) < 9:
            continue

        titulo = strip_html(cells[0]).rstrip(" /:")
        autor_cell = strip_html(cells[1]).rstrip(",")
        tipo = strip_html(cells[2])

        local_col = strip_html(cells[3])
        local_match = re.match(r"(Biblioteca[^A-Z]*?)\s{2,}(.+)", local_col)
        if local_match:
            local = local_match.group(1).strip()
            colecao = local_match.group(2).strip()
        else:
            parts = local_col.split("  ", 1)
            local = parts[0].strip() if parts else local_col
            colecao = parts[1].strip() if len(parts) > 1 else ""

        num_chamada = strip_html(cells[4])
        exemplar = strip_html(cells[5])
        situacao = strip_html(cells[6])

        disp_text = strip_html(cells[8])
        disp_match = re.search(r"(\d+)", disp_text)
        disponiveis = int(disp_match.group(1)) if disp_match else 0

        entry = {
            "titulo": titulo,
            "autor": autor_cell,
            "tipoExemplar": tipo,
            "local": local,
            "colecao": colecao,
            "numeroChamada": num_chamada,
            "exemplar": exemplar,
            "situacao": situacao,
            "disponiveis": disponiveis,
            "url": url,
        }
        reserves.append((bib, entry))
    return reserves


def fetch_course_list() -> list[dict]:
    """Fetch the list of disciplines from Koha using Playwright."""
    from playwright.sync_api import sync_playwright

    koha_base = KOHA_BASE
    url = koha_base + "opac-course-reserves.pl"
    search = "engenharia de software"

    print(f"Buscando lista de disciplinas em {url} …")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("input#dt-search-0", timeout=15_000)
        page.fill("input#dt-search-0", search)
        page.wait_for_timeout(1_200)

        rows = page.query_selector_all("table tbody tr:not(.dataTables_empty)")
        print(f"  {len(rows)} disciplinas encontradas.\n")

        result = []
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 7:
                continue
            secao = cells[3].inner_text().strip()
            raw_nome = cells[0].inner_text().strip()
            nome = re.sub(rf"\s*-\s*{re.escape(secao)}\s*$", "", raw_nome).strip().rstrip(" .:;,")
            link_el = cells[0].query_selector("a")
            href = link_el.get_attribute("href") if link_el else None
            url_reserva = (koha_base + href) if (href and not href.startswith("http")) else href
            instrutores = list(dict.fromkeys(
                x.strip()
                for x in re.split(r"[\n,]+", cells[5].inner_text())
                if x.strip()
            ))
            result.append({
                "nome": nome,
                "urlReserva": url_reserva,
                "instrutores": instrutores,
                "notas": cells[6].inner_text().strip(),
            })
        browser.close()
    return result


def main():
    BIBTEX_DIR.mkdir(exist_ok=True)
    subjects = json.loads(SUBJECTS_FILE.read_text(encoding="utf-8"))
    updated_bibtex = sync_missing_bibtex_isbns(subjects)
    print(f"Filled missing ISBN field in {updated_bibtex} existing BibTeX files.\n")

    reservas = fetch_course_list()

    print("Building bib↔key map and ISBN cache from existing data…")
    build_initial_maps(subjects)
    print(f"  {len(_bib_to_key)} existing valid bibtex entries loaded")
    print(f"  {len(_isbn_cache)} existing ISBN entries cached\n")

    existing = {s["disciplina"]: s for s in subjects}

    for reserva in reservas:
        disciplina = reserva["nome"]
        url = reserva["urlReserva"]
        print(f">>> {disciplina}")

        try:
            html = fetch(url)
        except Exception as e:
            print(f"    ERROR fetching {url}: {e}")
            continue

        raw_reserves = parse_reserves(html)
        if not raw_reserves:
            print("    No reserves found — skipping\n")
            continue

        reserve_list = []
        for bib, entry in raw_reserves:
            key, prefetched_content = resolve_key(
                bib, entry["autor"], entry["numeroChamada"]
            )
            bibtex_path = f"{BIBTEX_RELATIVE_PREFIX}/{key}.bib"
            bibtex_file = BIBTEX_DIR / f"{key}.bib"

            if prefetched_content is not None:
                # Already downloaded — just save
                bibtex_file.write_text(prefetched_content, encoding="utf-8")
                print(f"    Saved (author from bibtex): {key}.bib")
                entry["bibtex"] = bibtex_path
            elif bibtex_file.exists():
                print(f"    exists: {key}.bib")
                entry["bibtex"] = bibtex_path
            else:
                print(f"    Downloading: {key}.bib (bib={bib})")
                result = download_bibtex(bib, key)
                if result:
                    entry["bibtex"] = bibtex_path
                    print(f"    Saved {result}")
                else:
                    print(f"    WARNING: no bibtex for {entry['titulo']}")

            # ISBN — use cache when available, otherwise fetch detail page
            cached = entry["url"] in _isbn_cache
            isbns = fetch_isbn(entry["url"])
            entry["isbn"] = isbns
            if cached:
                print(f"    isbn (cached): {isbns or '—'}")
            else:
                print(f"    isbn: {isbns or '—'}")
                time.sleep(0.3)

            # Keep an ISBN supplied by Koha; use subjects.json/detail-page data
            # only as a fallback for downloaded BibTeX without the field.
            if "bibtex" in entry and bibtex_file.is_file():
                content = bibtex_file.read_text(encoding="utf-8")
                new_content = add_bibtex_isbns_if_missing(content, isbns)
                if new_content != content:
                    bibtex_file.write_text(new_content, encoding="utf-8")

            reserve_list.append(entry)
            time.sleep(0.3)

        meta = {
            "urlReserva": reserva.get("urlReserva"),
            "instrutores": reserva.get("instrutores", []),
            "notas": reserva.get("notas", ""),
        }
        if disciplina in existing:
            existing[disciplina].update({**meta, "reservas": reserve_list})
            print(f"    Updated ({len(reserve_list)} reservas)\n")
        else:
            existing[disciplina] = {"disciplina": disciplina, **meta, "reservas": reserve_list}
            print(f"    Added ({len(reserve_list)} reservas)\n")

        subjects_out = list(existing.values())
        SUBJECTS_FILE.write_text(
            json.dumps(subjects_out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        time.sleep(0.5)

    updated_bibtex = sync_missing_bibtex_isbns(list(existing.values()))
    print(f"Filled missing ISBN field in {updated_bibtex} new BibTeX files.")
    print("Done.")


if __name__ == "__main__":
    main()
