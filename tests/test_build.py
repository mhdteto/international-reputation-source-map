import importlib.util
from pathlib import Path
import csv
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT/'build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class SourceMapTests(unittest.TestCase):
    def row(self):
        return dict(source_id='x', market='Global', category='identity', name='Example', publisher='Example', url='https://example.org/', supports='Specific record', limits='Not proof of excellence', access_note='Check terms', language='en', checked_on='2026-11-01', verification='official_page_read', verification_url='https://example.org/about', verification_note='Page read')

    def test_public_dataset_has_six_markets_and_global(self):
        rows=b.load_sources(ROOT/'data/sources.csv','2026-11-01')
        self.assertEqual({r['market'] for r in rows}, {'United States','United Kingdom','Canada','France','United Arab Emirates','Morocco','Global'})
        self.assertGreaterEqual(len(rows),14)

    def test_unsafe_urls_rejected(self):
        for field in ['url','verification_url']:
            for url in ['javascript:alert(1)','https://user:pass@example.org/','https://example.org/\nsecret']:
                row=self.row();row[field]=url
                with self.subTest(field=field,url=url),self.assertRaises(ValueError):b.validate_rows([row],'2026-11-01')

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):b.validate_rows([self.row(),self.row()],'2026-11-01')

    def test_dates_and_verification_rejected(self):
        for key,value in [('checked_on','2026-11-02'),('checked_on','2026-02-30'),('verification','verified authority')]:
            row=self.row();row[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):b.validate_rows([row],'2026-11-01')

    def test_required_scope_is_not_optional(self):
        for field in ['supports','limits','verification_note']:
            row=self.row();row[field]=''
            with self.subTest(field=field),self.assertRaises(ValueError):b.validate_rows([row],'2026-11-01')

    def test_html_escapes_untrusted_fields(self):
        row=self.row();row['name']='<script>alert(1)</script>'
        text=b.render_html([row],'2026-11-01')
        self.assertNotIn('<script>alert',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertIn('Official page read',text)
        self.assertIn('search',text)

    def test_csv_malformed_quote_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.csv';p.write_text(','.join(b.FIELDS)+'\n"unfinished')
            with self.assertRaises((ValueError,csv.Error)):b.load_sources(p,'2026-11-01')

    def test_input_output_alias_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'sources.csv';source.write_text('keep');target=Path(d)/'report.json';os.link(source,target)
            with self.assertRaises(ValueError):b.guard_outputs(Path(d),source)
            self.assertEqual(source.read_text(),'keep')

if __name__=='__main__':unittest.main()
