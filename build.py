#!/usr/bin/env python3
"""Build an offline, scoped source catalogue. No network requests are made."""
import argparse
import csv
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

FIELDS=['source_id','market','category','name','publisher','url','supports','limits','access_note','language','checked_on','verification','verification_url','verification_note']
MARKETS={'United States','United Kingdom','Canada','France','United Arab Emirates','Morocco','Global'}
LABELS={'official_page_read':'Official page read','official_link_confirmed':'Official link confirmed','official_indexed_description':'Official indexed description'}

def checked_date(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Dates must use YYYY-MM-DD')
    return date.fromisoformat(value)

def safe_url(value):
    if not isinstance(value,str) or re.search(r'[\x00-\x20\x7f\\]',value):raise ValueError('Unsafe URL')
    p=urlsplit(value)
    if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:raise ValueError('Use credential-free HTTP(S) URLs')
    p.port
    return value

def validate_rows(rows,as_of):
    reference=checked_date(as_of);seen=set()
    if not rows:raise ValueError('At least one source is required')
    for row in rows:
        if set(row)!=set(FIELDS) or any(not isinstance(row[k],str) or not row[k].strip() for k in FIELDS):raise ValueError('Every source field is required')
        if row['source_id'] in seen:raise ValueError('Duplicate source ID')
        seen.add(row['source_id'])
        if row['market'] not in MARKETS or row['verification'] not in LABELS:raise ValueError('Unknown market or verification level')
        if checked_date(row['checked_on'])>reference:raise ValueError('Source check date is after as-of')
        safe_url(row['url']);safe_url(row['verification_url'])
    return rows

def load_sources(path,as_of):
    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle,strict=True)
        if reader.fieldnames is None or len(reader.fieldnames)!=len(FIELDS) or set(reader.fieldnames)!=set(FIELDS):raise ValueError('Unexpected source CSV headers')
        rows=list(reader)
    return validate_rows(rows,as_of)

def guard_outputs(directory,source):
    source=Path(source);targets=[Path(directory)/'report.json',Path(directory)/'report.html']
    for target in targets:
        if target.resolve()==source.resolve() or (target.exists() and source.exists() and target.samefile(source)):raise ValueError('Output would overwrite source input')
        if target.is_symlink():raise ValueError('Output symlinks are not accepted')
    if targets[0].resolve()==targets[1].resolve() or (all(t.exists() for t in targets) and targets[0].samefile(targets[1])):raise ValueError('Output files alias each other')
    return targets

def render_html(rows,as_of):
    def h(s):return escape(str(s),quote=True)
    def link(url,label):
        try:safe_url(url)
        except ValueError:return h(label)
        return '<a href="'+h(url)+'" rel="noreferrer">'+h(label)+'</a>'
    cards=[]
    for row in rows:
        detail=''.join('<dt>'+h(label)+'</dt><dd>'+h(row[key])+'</dd>' for key,label in [('supports','Can help substantiate'),('limits','Limits'),('access_note','Access note'),('language','Language'),('verification_note','What was checked')])
        cards.append('<article data-market="'+h(row['market'])+'"><p class="tag">'+h(row['market'])+' · '+h(row['category'])+'</p><h2>'+link(row['url'],row['name'])+'</h2><p>'+h(row['publisher'])+'</p><dl>'+detail+'</dl><p class="status">'+h(LABELS[row['verification']])+' · '+h(row['checked_on'])+'</p><p>'+link(row['verification_url'],'Primary verification reference')+'</p></article>')
    options=''.join('<option>'+h(m)+'</option>' for m in sorted({r['market'] for r in rows}))
    script="""const q=document.getElementById('search'),m=document.getElementById('market');function filter(){let n=0;for(const card of document.querySelectorAll('article')){const show=(!m.value||card.dataset.market===m.value)&&card.textContent.toLowerCase().includes(q.value.toLowerCase());card.hidden=!show;if(show)n++;}document.getElementById('count').textContent=n+' sources shown';}q.addEventListener('input',filter);m.addEventListener('change',filter);filter();"""
    return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>International Reputation Source Map</title><style>body{background:#081321;color:#e8f2f8;font:16px/1.6 system-ui,sans-serif;margin:0}main{max-width:1100px;padding:32px 20px;margin:auto}h1,a,.tag{color:#36d9ee}h1{line-height:1.2}.notice,article{background:#0d2539;border:1px solid #28485e;border-radius:12px;padding:22px;margin:20px 0}article[hidden]{display:none}h2{font-size:22px}a,dd{overflow-wrap:anywhere}dt{color:#98dce7;font-weight:600}dd{margin:0 0 12px}.controls{display:flex;gap:16px;flex-wrap:wrap}.controls label{display:flex;flex-direction:column;max-width:100%}input,select{font:inherit;padding:10px;box-sizing:border-box;max-width:100%}.status{font-size:14px;color:#b8cedd}</style></head><body><main><p class="tag">MOHAMMED TETO / EVIDENCE & SOURCES</p><h1>International Reputation Source Map</h1><div class="notice">A curated starting catalogue, not a list of endorsements or guaranteed backlinks. Verify the specific record, identity and time period. Source presence does not prove every claim or predict search/AI visibility. Research snapshot as of '+h(as_of)+'.</div><div class="controls"><label>Search<input id="search" type="search" placeholder="Source, claim or publisher"></label><label>Market<select id="market"><option value="">All markets</option>'+options+'</select></label></div><p id="count" aria-live="polite"></p>'+''.join(cards)+'<p>Source descriptions are original curation notes. Rights in the linked records remain with their respective publishers. No network requests are made by this catalogue.</p></main><script>'+script+'</script></body></html>\n'

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('sources');parser.add_argument('--as-of',required=True);parser.add_argument('--output-dir',default='reports');args=parser.parse_args(argv)
    try:
        targets=guard_outputs(args.output_dir,args.sources);rows=load_sources(args.sources,args.as_of)
        data=json.dumps({'as_of':args.as_of,'scope':'Curated source entry points; no entity record or endorsement verified','sources':rows},ensure_ascii=False,indent=2)+'\n';page=render_html(rows,args.as_of)
        Path(args.output_dir).mkdir(parents=True,exist_ok=True)
        for p,text in zip(targets,[data,page]):p.write_text(text,encoding='utf-8')
    except (ValueError,OSError,csv.Error,TypeError) as exc:parser.exit(2,'Error: '+str(exc)+'\n')
    print('Wrote '+str(len(rows))+' curated sources. No network requests performed.')
    return 0
if __name__=='__main__':sys.exit(main())
