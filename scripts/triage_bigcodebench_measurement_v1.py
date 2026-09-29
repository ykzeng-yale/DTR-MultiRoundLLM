#!/usr/bin/env python3
"""Static source-wide measurement triage; never execute source or admit tasks."""
import ast,collections,hashlib,json,re,sys
from pathlib import Path

PIN='d9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'
SOURCE=Path('work/task_sources/bigcodebench_v014_20260927/v0.1.4.parquet')
NETWORK=('requests','urllib','socket','aiohttp','http','selenium','bs4','scrapy')
WEB=('django','flask','fastapi','starlette','werkzeug','wtforms')
NATIVE=('numpy','pandas','scipy','sklearn','matplotlib','seaborn','plotly','PIL','cv2','torch')
PLOT=('matplotlib','seaborn','plotly','bokeh','altair')
FILE_MARKERS=('open(','.read_csv(','.to_csv(','.read_json(','.to_json(','.read_excel(','.to_excel(',
              'os.listdir(','.glob(','.connect(','.copy(','.move(','.write_text(','.read_text(')
PLOT_VALUE_MARKERS=('get_ydata(', 'get_xdata(', '.patches', 'get_height(', 'get_width(', 'get_array(')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def classify(row):
    libs=ast.literal_eval(row['libs'])
    if type(libs) is not list or any(type(x) is not str for x in libs):
        raise ValueError('malformed libraries')
    heads={x.split('.')[0] for x in libs}
    source=row['canonical_solution']
    test=row['test']
    found=lambda roots:bool(heads & set(roots))
    flags={
      'network_library':found(NETWORK),
      'web_framework':found(WEB),
      'native_object_library':found(NATIVE),
      'plot_library':found(PLOT),
      'randomness_static':found(('random','secrets','faker')) or bool(re.search(r'\b(?:np|numpy)\.random\b',source)),
      'reference_file_io_static':any(x in source for x in FILE_MARKERS),
      'test_plot_values_static':any(x in test for x in PLOT_VALUE_MARKERS),
    }
    return {'task_id':row['task_id'],'flags':flags,'libs':libs,
            'prompt_sha256':hashlib.sha256(row['complete_prompt'].encode()).hexdigest(),
            'test_sha256':hashlib.sha256(test.encode()).hexdigest()}

def main():
    import pyarrow.parquet as pq  # reader-only environment, not project runtime
    out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('refuse overwrite')
    if sha(SOURCE)!=PIN:raise ValueError('source drift')
    rows=pq.read_table(SOURCE).to_pylist()
    if len(rows)!=1140 or [r['task_id'] for r in rows]!=[f'BigCodeBench/{i}' for i in range(1140)]:
        raise ValueError('row roster')
    items=[classify(r) for r in rows]
    counts=dict(collections.Counter(k for item in items for k,v in item['flags'].items() if v))
    record={'classification':'static measurement triage, not family/admission or runnable-task ledger',
            'source_sha256':PIN,'builder_sha256':sha(__file__),'source_rows':len(items),
            'flag_counts':counts,'flags_scope':'Overlapping source-text/library flags only. Absence is not evidence of semantic validity, no-network safety, independent family or dependency completeness.',
            'rows':items,'admitted_tasks':0,'benchmark_executions':0,'receiver_calls':0}
    out.write_text(json.dumps(record,separators=(',',':'))+'\n')
    print(json.dumps(counts,sort_keys=True))
if __name__=='__main__':main()
