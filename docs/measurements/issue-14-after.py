import sys,tempfile,time,statistics
from pathlib import Path
sys.path[:0]=['scripts','tests']
import ingest,session,pdftext
from test_pdftext import unicode_pdf
from test_ingest import build_pdf,stream,_pages,CATALOG

def measure(fn):
    vals=[]
    for _ in range(5):
        t=time.perf_counter();fn();vals.append(time.perf_counter()-t)
    return round(statistics.median(vals)*1000,3)
with tempfile.TemporaryDirectory() as d:
    c=Path(d);logs=c/'.state/logs';logs.mkdir(parents=True)
    for i in range(1000): (logs/f'{i:04}.md').write_text('first_contact: 2026-10-01\n'+'x'*10000)
    print('first_contact_1000_logs_ms',measure(lambda:session._first_contact(c)))
    base=unicode_pdf();objs=pdftext._objects(base,ingest._Budget(ingest.PDF_INFLATE_BUDGET))
    raw={k:h for k,(h,s) in objs.items() if s is None}
    raw.update({k:stream(s) for k,(h,s) in objs.items() if s is not None})
    raw.update(_pages(200,b'<< /Font << /F1 5 0 R >> >>'))
    p=c/'deck.pdf';p.write_bytes(build_pdf(raw))
    print('pdf_200_shared_fonts_ms',measure(lambda:pdftext.builtin_text(p,1,200)))
    lines=['## Topics','| topic | source |','|---|---|']+[f'| T{i} | notes/a.md |' for i in range(2000)]
    cells=[f'| New{i} | notes/a.md |' for i in range(200)]
    def index():
        rows=lines.copy()
        first,end=ingest._section_table(rows,ingest._TOPICS)
        existing={tuple(ingest._split_row(rows[i])[:2]) for i in range(first,end)}
        additions=[]
        for cell in cells:
            key=tuple(ingest._split_row(cell))
            if key not in existing:
                existing.add(key);additions.append(cell)
        rows[end:end]=additions
    print('index_2000_plus_200_topics_ms',measure(index))
