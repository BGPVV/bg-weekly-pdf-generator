"""CSV + HTML -> PDF. Запуск: python pdf_generator.py [--no-open]."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
FIELDS = ('id','category','title','event','meaning','action','source_name','source_url','source_page')

def read_news(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError('В CSV отсутствуют поля: ' + ', '.join(sorted(missing)))
        rows = list(reader)
    if not rows:
        raise ValueError('CSV не содержит записей.')
    seen = set()
    for number, row in enumerate(rows, 2):
        if None in row or any(row.get(key) is None for key in FIELDS):
            raise ValueError(f'Строка CSV {number}: неверное число столбцов.')
        for key in ('id','category','title','event','meaning','action'):
            if not row[key].strip():
                raise ValueError(f'Строка CSV {number}: пустое поле {key}.')
        if row['id'] in seen:
            raise ValueError('Повтор ID: ' + row['id'])
        seen.add(row['id'])
        check_url(row['source_url'])
    return rows

def check_url(value):
    if value and (urlparse(value).scheme not in ('http', 'https') or not urlparse(value).netloc):
        raise ValueError('Ожидается ссылка http/https: ' + value)

def open_pdf(path):
    try:
        if sys.platform == 'win32':
            os.startfile(str(path))
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])
    except (OSError, AttributeError) as error:
        print('PDF создан. Откройте его вручную:', error)

def run():
    parser = argparse.ArgumentParser(description='Генератор краткого обзора рынка БГ')
    parser.add_argument('--data', type=Path, default=ROOT/'data/news.csv')
    parser.add_argument('--meta', type=Path, default=ROOT/'data/issue.json')
    parser.add_argument('--template', type=Path, default=ROOT/'templates/weekly.html')
    parser.add_argument('--output', type=Path, default=ROOT/'output/BG_WEEKLY_SHORT_2026_09_28.pdf')
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
        from playwright.sync_api import sync_playwright
        rows = read_news(args.data)
        issue = json.loads(args.meta.read_text(encoding='utf-8-sig'))
        for key in ('website', 'full_url'):
            check_url(issue.get(key, ''))
        environment = Environment(loader=FileSystemLoader(str(args.template.resolve().parent)),
                                  autoescape=select_autoescape(['html']), undefined=StrictUndefined)
        result = environment.get_template(args.template.name).render(issue=issue, news=rows)
        args.output = args.output.resolve()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        html_path = args.output.with_suffix('.html')
        html_path.write_text(result, encoding='utf-8')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                # Документ собирается локально; внешние запросы при рендеринге запрещены.
                page.route('http://**/*', lambda route: route.abort())
                page.route('https://**/*', lambda route: route.abort())
                page.goto(html_path.as_uri(), wait_until='load')
                page.evaluate('document.fonts.ready')
                page.pdf(path=str(args.output), format='A4', print_background=True,
                         prefer_css_page_size=True, display_header_footer=True,
                         header_template='<span></span>',
                         footer_template='<div style="width:100%;font-size:8px;color:#60748d;text-align:center">Виталий Патраков · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
            finally:
                browser.close()
        print(f'Готово: {args.output}\nОбработано блоков: {len(rows)}')
        if not args.no_open:
            open_pdf(args.output)
        return 0
    except ImportError:
        print('Установите зависимости: python -m pip install -r requirements.txt', file=sys.stderr)
    except Exception as error:
        print(f'Ошибка: {error}', file=sys.stderr)
        print('Если не установлен Chromium: python -m playwright install chromium', file=sys.stderr)
    return 1

if __name__ == '__main__':
    raise SystemExit(run())
