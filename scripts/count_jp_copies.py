#!/usr/bin/env python3
"""
Conta exemplares na Biblioteca de João Pessoa para cada bibliografia do ementario.json.
Acessa os links do Koha (extraídos dos arquivos .bib) e conta os itens com
localização "Biblioteca João Pessoa", salvando o resultado em quantidadeEmJP.
"""

import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMENTARIO_PATH = os.path.join(BASE_DIR, 'course/engenharia-de-software/ementas/ementario.json')
BIBTEX_DIR = os.path.join(BASE_DIR, 'course/engenharia-de-software/bibtex')

LOCATION_JP = 'João Pessoa'
REQUEST_DELAY = 0.4  # segundos entre requisições


class HoldingsParser(HTMLParser):
    """Conta linhas da tabela holdingst com localização em João Pessoa."""

    def __init__(self):
        super().__init__()
        self._in_holdingst = False
        self._in_tbody = False
        self._depth = 0
        self._table_depth = 0
        self._current_row_has_jp = False
        self.jp_count = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'table' and attrs_dict.get('id') == 'holdingst':
            self._in_holdingst = True
            self._table_depth = self._depth
            self._depth += 1
            return

        if self._in_holdingst:
            self._depth += 1
            if tag == 'tbody':
                self._in_tbody = True
            elif tag == 'tr' and self._in_tbody:
                self._current_row_has_jp = False
            elif tag == 'td' and self._in_tbody:
                data_order = attrs_dict.get('data-order', '')
                if LOCATION_JP in data_order:
                    self._current_row_has_jp = True

    def handle_endtag(self, tag):
        if not self._in_holdingst:
            return

        if tag == 'tr' and self._in_tbody and self._current_row_has_jp:
            self.jp_count += 1
            self._current_row_has_jp = False

        if tag == 'tbody':
            self._in_tbody = False

        self._depth -= 1
        if tag == 'table' and self._depth == self._table_depth:
            self._in_holdingst = False


def fetch_html(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f'    [ERRO] {e}')
        return None


def count_jp_copies(koha_url):
    html = fetch_html(koha_url)
    if not html:
        return None
    parser = HoldingsParser()
    parser.feed(html)
    return parser.jp_count


def extract_koha_url_from_bibtex(bib_path):
    """Lê um arquivo .bib e retorna a URL do Koha, se presente."""
    try:
        with open(bib_path, encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'url\s*=\s*\{([^}]+biblioteca\.ifpb\.edu\.br[^}]+)\}', content, re.I)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


def resolve_bibtex_paths(bibtex_refs):
    """Converte referências relativas a paths absolutos do diretório bibtex."""
    paths = []
    for ref in bibtex_refs:
        if ref.startswith('bibtex/'):
            abs_path = os.path.join(BIBTEX_DIR, os.path.basename(ref))
        else:
            abs_path = os.path.join(BASE_DIR, ref)
        paths.append(abs_path)
    return paths


def main():
    with open(EMENTARIO_PATH, encoding='utf-8') as f:
        data = json.load(f)

    # Cache: url → contagem (evita requisições duplicadas)
    url_cache = {}

    stats = {'processados': 0, 'sem_bibtex': 0, 'sem_url': 0, 'erros': 0, 'ja_tinha': 0}

    for disc_idx, disc in enumerate(data):
        disciplina = disc.get('disciplina', f'Disciplina {disc_idx}')
        bibliografias = disc.get('bibliografias', [])

        for bib in bibliografias:
            bibtex_refs = bib.get('bibtex', [])

            if not bibtex_refs:
                stats['sem_bibtex'] += 1
                continue

            # Procura URL nos arquivos bibtex referenciados
            koha_url = None
            for ref in bibtex_refs:
                bib_paths = resolve_bibtex_paths([ref])
                for path in bib_paths:
                    koha_url = extract_koha_url_from_bibtex(path)
                    if koha_url:
                        break
                if koha_url:
                    break

            if not koha_url:
                stats['sem_url'] += 1
                continue

            # Usa cache para não repetir requisições
            if koha_url in url_cache:
                count = url_cache[koha_url]
                bib['quantidadeEmJP'] = count
                stats['processados'] += 1
                continue

            ref_text = bib.get('referencia', '')[:70]
            print(f'  Buscando: {ref_text}')
            print(f'    URL: {koha_url}')

            count = count_jp_copies(koha_url)
            time.sleep(REQUEST_DELAY)

            if count is None:
                print(f'    → Falha ao acessar')
                stats['erros'] += 1
                continue

            url_cache[koha_url] = count
            bib['quantidadeEmJP'] = count
            stats['processados'] += 1
            print(f'    → {count} exemplar(es) em JP')

        # Salva progresso a cada disciplina
        if (disc_idx + 1) % 10 == 0:
            with open(EMENTARIO_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'\n[Progresso] Salvo após disciplina {disc_idx + 1}/{len(data)}\n')

    # Salva resultado final
    with open(EMENTARIO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n=== CONCLUÍDO ===')
    print(f'Processados:  {stats["processados"]}')
    print(f'Sem bibtex:   {stats["sem_bibtex"]}')
    print(f'Sem URL Koha: {stats["sem_url"]}')
    print(f'Erros HTTP:   {stats["erros"]}')


if __name__ == '__main__':
    main()
