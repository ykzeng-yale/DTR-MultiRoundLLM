#!/usr/bin/env python3
"""Local, data-only LCB stdio roster/instrument export. Never execute task code.

All private values stay in fresh ignored gzip storage. Cached parquet reads have
no network fallback; the pinned inquiry's inert opcode decoder is reused without
an Unpickler. Source-only contract clearance is not semantic truth or efficacy.
"""
import argparse
import collections
from fractions import Fraction
import gc
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import struct
import subprocess
import sys
import time

try:
    import inquire_lcb_private_instrument_20260930 as inquiry
except ModuleNotFoundError:
    from scripts import inquire_lcb_private_instrument_20260930 as inquiry

ROOT = Path(__file__).resolve().parents[1]
SEED = 'lcb-stdio-sprint-split-v1:20260930'
ASCII_TOKENS = 'ascii_whitespace_tokens_v1'
SINGLE_LINE = 'single_line_exact_optional_final_newline_v1'
NORMALIZATIONS = {ASCII_TOKENS, SINGLE_LINE}
MAX_CASE_BYTES = 16 * 1024**2
MAX_ROOT_PLAIN = 512 * 1024**2
R = {'development': 16, 'tuning': 4, 'evaluation': 32}


class BundleError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def jsonl(path):
    with Path(path).open('r', encoding='utf-8') as f:
        for line in f:
            yield inquiry.strict_json(line)


def normalize(value, rule):
    """Deterministic, source-declared comparison; no numeric/case/order repair."""
    if type(value) is not str or rule not in NORMALIZATIONS:
        raise BundleError('normalization-schema')
    raw = value.encode('utf-8', errors='strict')
    if len(raw) > MAX_CASE_BYTES:
        raise BundleError('case-byte-cap')
    if rule == ASCII_TOKENS:
        return tuple(v for v in re.split(rb'[ \t\r\n\v\f]+', raw) if v)
    raw = raw.replace(b'\r\n', b'\n')
    if raw.endswith(b'\n'):
        raw = raw[:-1]
    if b'\n' in raw or b'\r' in raw:
        raise BundleError('single-line-shape')
    return (raw,)


def normalized_hash(value, rule):
    # Length-prefix each token, so distinct token boundaries cannot collide.
    h = hashlib.sha256()
    for token in normalize(value, rule):
        h.update(struct.pack('<Q', len(token))); h.update(token)
    return h.hexdigest()


def split_components(nodes, eligible, seed=SEED):
    """Outcome-blind entire operational components; exact rational weights."""
    by_component = collections.defaultdict(list)
    for node in nodes:
        if node['node_id'] in eligible:
            by_component[node['operational_component']].append(node['node_id'])
    ordered = sorted(by_component, key=lambda c: (digest((seed+'\0'+c).encode()), c))
    cut1, cut2 = len(ordered)*60//100, len(ordered)*80//100
    assignment = {}
    for i, component in enumerate(ordered):
        split = 'development' if i < cut1 else ('tuning' if i < cut2 else 'evaluation')
        assignment[component] = split
    group_counts = collections.Counter(assignment.values())
    root_rows = {}
    for component, roots in by_component.items():
        split = assignment[component]
        weight = Fraction(1, group_counts[split] * len(roots))
        episode_weight = weight/R[split]
        for root in roots:
            root_rows[root] = {'split': split, 'family_id': component,
                'replicates': R[split], 'component_root_count': len(roots),
                'root_weight': {'numerator': weight.numerator, 'denominator': weight.denominator},
                'episode_weight': {'numerator': episode_weight.numerator, 'denominator': episode_weight.denominator}}
    return root_rows, assignment, dict(group_counts)


def case_metadata(cases, public_cases, rule):
    """Keep all cases, with a separate input-disjoint diagnostic index."""
    public_inputs = collections.defaultdict(set)
    private_inputs = collections.defaultdict(set)
    public_raw = collections.defaultdict(set)
    private_raw = collections.defaultdict(set)
    for c in public_cases:
        ih = digest(c['input'].encode()); oh = digest(c['output'].encode())
        public_inputs[ih].add(normalized_hash(c['output'], rule)); public_raw[ih].add(oh)
    diagnostic = []
    ledger = []
    for i, c in enumerate(cases):
        ih = digest(c['input'].encode()); oh = digest(c['output'].encode())
        nh = normalized_hash(c['output'], rule)
        private_inputs[ih].add(nh); private_raw[ih].add(oh)
        if ih not in public_inputs:
            diagnostic.append(i)
        ledger.append({'ordinal': i, 'stdin_sha256': ih, 'expected_stdout_sha256': oh,
                       'canonical_expected_sha256': nh,
                       'stdin_bytes': len(c['input'].encode()),
                       'expected_stdout_bytes': len(c['output'].encode())})
    return {'case_count': len(cases), 'case_metadata_sha256': digest(canonical(ledger)),
        'private_input_disjoint_ordinals': diagnostic,
        'public_input_overlap_cases': len(cases)-len(diagnostic),
        'raw_overlapping_expected_set_differences': sum(private_raw[k] != v for k,v in public_raw.items() if k in private_raw),
        'canonical_overlapping_expected_set_differences': sum(private_inputs[k] != v for k,v in public_inputs.items() if k in private_inputs),
        'private_inputs_with_canonical_expected_conflicts': sum(len(v)>1 for v in private_inputs.values()),
        'input_bytes': sum(x['stdin_bytes'] for x in ledger),
        'output_bytes': sum(x['expected_stdout_bytes'] for x in ledger),
        'maximum_input_bytes': max((x['stdin_bytes'] for x in ledger), default=0),
        'maximum_output_bytes': max((x['expected_stdout_bytes'] for x in ledger), default=0)}, ledger


class Budget:
    def __init__(self, plan):
        self.plan = plan; self.started = time.monotonic(); self.retained = 0
    def check(self, additional=0):
        u = resource.getrusage(resource.RUSAGE_SELF)
        rss = u.ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        if time.monotonic()-self.started > self.plan['wall_seconds']:
            raise BundleError('wall-cap')
        if u.ru_utime+u.ru_stime > self.plan['cpu_seconds']:
            raise BundleError('cpu-cap')
        if rss > self.plan['rss_bytes']:
            raise BundleError('rss-post-allocation-cap')
        if self.retained+additional > self.plan['retained_bytes']:
            raise BundleError('pre-write-retained-cap')
        if shutil.disk_usage(ROOT).free < self.plan['remaining_free_floor_bytes']:
            raise BundleError('remaining-free-storage-floor')
    def written(self, n):
        self.check(n); self.retained += n


class CountingWriter:
    def __init__(self, handle, budget): self.handle = handle; self.budget = budget
    def write(self, data):
        self.budget.written(len(data)); return self.handle.write(data)
    def flush(self): return self.handle.flush()
    def __getattr__(self, name): return getattr(self.handle, name)


def write_json(path, value, budget, compressed=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise BundleError('fresh-output-file')
    plain = 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                              separators=(',', ':'), allow_nan=False)
    with path.open('xb') as file:
        os.chmod(path, 0o600)
        writer = CountingWriter(file, budget)
        stream = gzip.GzipFile(filename='', mode='wb', compresslevel=1, mtime=0,
                               fileobj=writer) if compressed else writer
        try:
            for piece in encoder.iterencode(value):
                raw = piece.encode(); plain += len(raw)
                if plain > MAX_ROOT_PLAIN and compressed:
                    raise BundleError('root-plaintext-cap')
                stream.write(raw)
            stream.write(b'\n'); plain += 1
        finally:
            if compressed: stream.close()
    return {'path': str(path.relative_to(ROOT)), 'stored_bytes': path.stat().st_size,
            'sha256': file_hash(path), 'plain_bytes': plain,
            'compression': 'gzip' if compressed else 'none'}


class LocalRangeFile(inquiry.PrivateRangeFile):
    """Seekable pinned cached projection only. No opener/network fallback."""
    def __init__(self, directory, expected_size, pin, budget):
        io.RawIOBase.__init__(self)
        self.directory = Path(directory); self.position=0; self.size=expected_size
        self.budget=budget; self.cache=[]; self.receipts=[]; self.metadata_only=True
        self.max_request=inquiry.source.MAX_REQUEST
        self.footer_length=pin['footer_bytes']; self.footer_start=self.size-8-self.footer_length
        for receipt in jsonl(self.directory/'requests.jsonl'):
            left, right = receipt['start'], receipt['end_inclusive']+1
            path = self.directory/receipt['payload_path']
            if (receipt['status']!='VERIFIED' or receipt['server_total_bytes']!=self.size or
                receipt['fetched_bytes']!=right-left or path.stat().st_size!=right-left or
                file_hash(path)!=receipt['payload_sha256']):
                raise BundleError('cached-range-pin-drift')
            self.cache.append((left,right,path)); self.receipts.append(receipt)
        self.allowed=[(0,4),(self.footer_start,self.size)]
        self.footer_sha256=digest(self._interval(self.footer_start,self.size-8))
        if (self._interval(0,4)!=b'PAR1' or self._interval(self.size-4,self.size)!=b'PAR1' or
            self.footer_sha256!=pin['footer_sha256'] or
            struct.unpack('<I',self._interval(self.size-8,self.size-4))[0]!=self.footer_length):
            raise BundleError('cached-footer-pin-drift')
    def _fetch(self, start, end):
        raise BundleError('uncached-read-refused-no-network')


def exposure_inventory(public, plan):
    """Inspect only identity/public-source metadata, never outcome/model content.

    Finite tracked history plus explicitly pinned ignored request/task manifests.
    Absence of a link is not a novelty or global unseen-family certificate.
    """
    paths = inquiry.strict_json((ROOT/plan['exposure_inventory_path']).read_text())['paths']
    ids = {r['platform']+':'+str(r['question_id']): i for i,r in enumerate(public)}
    qids = collections.defaultdict(set)
    statements = collections.defaultdict(set)
    source_hashes = collections.defaultdict(set)
    for root, i in ids.items():
        qids[str(public[i]['question_id'])].add(root)
        statements[digest(public[i]['question_content'].encode())].add(root)
        source_hashes[digest(canonical(public[i]))].add(root)
    identities = {'root','task_id','question_id','problem_id','uid','task'}
    text_fields = {'question_content','prompt','task_prompt','problem_statement'}
    hash_fields = {'statement_sha256','public_row_sha256','root_source_sha256','prompt_sha256'}
    forbidden = {'output','outputs','response','responses','completion','completions','artifact',
        'artifacts','code','stdout','stderr','grade','grades','outcome','outcomes','score','scores',
        'label','labels','private','private_test_cases','public_test_cases','test_cases',
        'expected','expected_stdout','hidden_tests','terminal_label','reward','rewards'}
    links = collections.defaultdict(list)
    inspected = []
    def walk(value, path, position='$'):
        if isinstance(value,dict):
            platform = value.get('platform')
            for k,v in value.items():
                if k in forbidden or k.startswith(('private_','hidden_')): continue
                found = set()
                if k in identities and isinstance(v,str):
                    if v in ids: found.add(v)
                    if platform in {'atcoder','codeforces','leetcode'} and platform+':'+v in ids:
                        found.add(platform+':'+v)
                    if not v.isdecimal() and len(qids.get(v,()))==1:
                        found.update(qids[v])
                elif k in text_fields and isinstance(v,str):
                    found.update(statements.get(digest(v.encode()),()))
                elif k in hash_fields and isinstance(v,str):
                    found.update(statements.get(v,())); found.update(source_hashes.get(v,()))
                for root in found:
                    links[root].append({'path':path,'json_location':position+'.'+k,
                                        'match':'exact_identity_or_public_source_hash'})
                if isinstance(v,(dict,list)): walk(v,path,position+'.'+k)
        elif isinstance(value,list):
            for i,item in enumerate(value):
                if isinstance(item,(dict,list)): walk(item,path,position+'['+str(i)+']')
    for pin in paths:
        path=ROOT/pin['path']
        if path.stat().st_size!=pin['bytes'] or file_hash(path)!=pin['sha256']:
            raise BundleError('historical-metadata-pin-drift')
        try:
            if path.suffix=='.jsonl':
                for record in jsonl(path): walk(record,pin['path'])
            else: walk(inquiry.strict_json(path.read_text()),pin['path'])
            inspected.append({'path':pin['path'],'sha256':pin['sha256'],'status':'IDENTITY_METADATA_SCANNED'})
        except (json.JSONDecodeError,UnicodeDecodeError,inquiry.InstrumentError):
            inspected.append({'path':pin['path'],'sha256':pin['sha256'],'status':'UNPARSEABLE_METADATA'})
    return dict(links), inspected


def load_root_cases(bundle, root, scope, battery='primary'):
    """Trusted host adapter; sealed expectations must never enter policy view.

    Materializes one bounded root only. Returned observer schema is exactly
    {case_id,scope,stdin,expected_stdout}; no task code is imported/executed.
    """
    bundle=Path(bundle).resolve()
    if not bundle.is_relative_to(ROOT/'work'): raise BundleError('ignored-bundle-only')
    index=inquiry.strict_json((bundle/'instruments.json').read_text())
    if root not in index or scope not in {'public','private'}:
        raise BundleError('root-scope')
    entry=index[root][scope]
    path=ROOT/entry['path']
    if not path.resolve().is_relative_to(bundle) or file_hash(path)!=entry['sha256']:
        raise BundleError('sealed-file-hash')
    with gzip.open(path,'rb') as f:
        raw=f.read(MAX_ROOT_PLAIN+1)
    if len(raw)>MAX_ROOT_PLAIN or len(raw)!=entry['plain_bytes']:
        raise BundleError('sealed-root-size')
    cases=inquiry.strict_json(raw.decode('utf-8'))
    if len(cases)!=entry['case_count'] or digest(canonical(cases))!=entry['cases_sha256']:
        raise BundleError('sealed-case-ledger-hash')
    if scope=='private' and battery=='private_input_disjoint':
        cases=[cases[i] for i in entry['private_input_disjoint_ordinals']]
    elif battery!='primary': raise BundleError('declared-battery')
    return {'root':root,'scope':scope,'normalization':index[root]['normalization'],
            'source_sha256':index[root]['root_source_sha256'],
            'resource_contract':index[root]['resource_contract'],'cases':cases}


def run(plan, out):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if plan['runner_sha256']!=file_hash(__file__): raise BundleError('runner-pin')
    for pin in plan['input_pins']:
        if file_hash(ROOT/pin['path'])!=pin['sha256']:
            raise BundleError('input-pin-drift')
    if pa.__version__!=plan['pyarrow_version'] or sys.version.split()[0]!=plan['python_version']:
        raise BundleError('parser-runtime-pin')
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work') or out==ROOT/'work':
        raise BundleError('fresh-ignored-output')
    if shutil.disk_usage(ROOT).free<plan['minimum_free_bytes']:
        raise BundleError('free-storage-preflight')
    out.mkdir(parents=True,mode=0o700)
    budget=Budget(plan); pa.set_cpu_count(1); pa.set_io_thread_count(1)
    public=list(jsonl(ROOT/plan['public_rows_path']))
    old=inquiry.strict_json((ROOT/plan['disposition_path']).read_text())['rows']
    reviews={r['source_row']:r for r in jsonl(ROOT/plan['contract_review_path'])}
    nodes=list(jsonl(ROOT/plan['nodes_path']))
    journal=list(jsonl(ROOT/plan['private_journal_path']))
    private_plan=inquiry.strict_json((ROOT/plan['private_plan_path']).read_text())
    if any(len(x)!=1055 for x in (public,old,nodes,journal)): raise BundleError('assigned-row-count')
    clear={nodes[i]['node_id'] for i,r in reviews.items() if r['ruling']=='clear'}
    if len(clear)!=567: raise BundleError('frozen-contract-count')
    roster, components, group_counts=split_components(nodes,clear,plan['split_seed'])
    exposure, exposure_scanned=exposure_inventory(public,plan)
    if any(r in clear for r in exposure):
        # No automatic reassignment/exclusion; retain evidence and require lead disposition.
        raise BundleError('eligible-historical-controller-link-requires-disposition')
    instruments={}; allrows=[]; tasks=[]; conflicts=[]; counts=collections.Counter()
    prompt_bound=0; offset=0; started=budget.started
    summary={'schema':'lcb-stdio-sprint-bundle-result-v1','status':'FAILED',
        'plan_sha256':digest(canonical(plan)),'source_rows':1055,'rows_redecoded':0,
        'provisional_roots':567,'admitted_tasks':0,'model_calls':0,'task_code_executions':0,
        'reference_executions':0,'unpickler_executions':0,'network_calls':0}
    write_json(out/'plan.json',plan,budget)
    try:
        for si,shard in enumerate(private_plan['shards']):
            pin=private_plan['footer_pins'][si]
            with LocalRangeFile(ROOT/plan['private_cache_path']/'ranges'/f'shard-{si:02d}',
                    private_plan['shard_bytes'][shard],pin,budget) as raw:
                parquet=pq.ParquetFile(raw,pre_buffer=False,memory_map=False,buffer_size=0)
                if parquet.metadata.num_rows!=pin['rows']: raise BundleError('cached-shard-count')
                raw.permit_instrument_columns(parquet.metadata)
                for batch in parquet.iter_batches(batch_size=1,columns=list(inquiry.COLUMNS),use_threads=False):
                    budget.check()
                    for value in batch.to_pylist():
                        i=offset; pub=public[i]; node=nodes[i]; previous=journal[i]
                        root=node['node_id']; rowhash=digest(canonical(pub))
                        if ((value['platform'],value['question_id'])!=(pub['platform'],pub['question_id']) or
                            root!=pub['platform']+':'+str(pub['question_id']) or
                            rowhash!=node['public_row_sha256'] or rowhash!=previous['public_row_sha256'] or
                            digest(value['private_test_cases'].encode())!=previous['private_field_sha256']):
                            raise BundleError('source-alignment-pin')
                        cases,encoding=inquiry.decode_cases(value['private_test_cases'])
                        public_cases=inquiry.strict_json(pub['public_test_cases'])
                        metrics=inquiry.summarize_cases(cases,public_cases)
                        if encoding!=previous['encoding'] or any(previous[k]!=v for k,v in metrics.items()):
                            raise BundleError('private-journal-independent-redecode-drift')
                        review=reviews.get(i)
                        ruling=(review['ruling'] if review else old[i]['disposition'])
                        record={'source_row':i,'root':root,'platform':pub['platform'],
                            'question_id':pub['question_id'],'public_row_sha256':rowhash,
                            'statement_sha256':digest(pub['question_content'].encode()),
                            'private_field_sha256':previous['private_field_sha256'],
                            'private_case_ledger_sha256':metrics['case_ledger_sha256'],
                            'source_contract_disposition':ruling,'operational_component':node['operational_component'],
                            'split':components.get(node['operational_component']),'admitted':False,
                            'semantic_family_verified':False,'pretraining_novelty_certificate':False,
                            'historical_controller_exposure':('exact_prior_link_found' if root in exposure else
                                'no_exact_link_in_frozen_identity_metadata_inventory'),
                            'historical_links':exposure.get(root,[]),'private_case_count':len(cases)}
                        if root in clear:
                            if pub['starter_code'] or any(c['testtype']!='stdin' for c in cases+public_cases):
                                raise BundleError('stdio-interface-drift')
                            rule=SINGLE_LINE if root=='atcoder:abc325_a' else ASCII_TOKENS
                            info,metadata=case_metadata(cases,public_cases,rule)
                            pub_info,pub_metadata=case_metadata(public_cases,[],rule)
                            if info['private_inputs_with_canonical_expected_conflicts'] or info['canonical_overlapping_expected_set_differences']:
                                conflicts.append({'root':root,**{k:info[k] for k in (
                                    'raw_overlapping_expected_set_differences','canonical_overlapping_expected_set_differences',
                                    'private_inputs_with_canonical_expected_conflicts')}})
                            safe=root.replace(':','__')
                            entry={'root_source_sha256':rowhash,'normalization':rule,
                                   'resource_contract':plan['observer_resource_contract']}
                            for scope,source_cases,meta in [('public',public_cases,pub_info),('private',cases,info)]:
                                converted=[{'case_id':root+':'+scope+':'+str(j),'scope':scope,
                                            'stdin':c['input'],'expected_stdout':c['output']}
                                           for j,c in enumerate(source_cases)]
                                ref=write_json(out/'sealed'/safe/(scope+'.json.gz'),converted,budget,compressed=True)
                                ref.update(case_count=len(converted),cases_sha256=digest(canonical(converted)))
                                if scope=='private': ref.update(info)
                                entry[scope]=ref
                                del converted
                            metadata_ref=write_json(out/'sealed'/safe/'case-metadata.json.gz',
                                {'public':pub_metadata,'private':metadata},budget,compressed=True)
                            entry['case_metadata']=metadata_ref; instruments[root]=entry
                            task={**roster[root],'root':root,'root_source_sha256':rowhash,
                                'prompt':pub['question_content'],'public_instrument':{
                                    'bundle_path':str(out.relative_to(ROOT)),'root':root,'scope':'public',
                                    'normalization':rule,'sealed_reference':entry['public']}}
                            tasks.append(task); record.update(roster[root],normalization=rule,
                                private_metrics=info,public_case_count=len(public_cases),
                                instrument_status='SOURCE_BOUND_PROPOSED_NOT_RUNTIME_QUALIFIED')
                            counts['private_cases']+=len(cases); counts['public_cases']+=len(public_cases)
                            counts['private_input_bytes']+=info['input_bytes']; counts['private_output_bytes']+=info['output_bytes']
                            counts['public_input_overlap_cases']+=info['public_input_overlap_cases']
                            counts['private_input_disjoint_cases']+=len(info['private_input_disjoint_ordinals'])
                            counts['raw_expected_set_difference_roots']+=bool(info['raw_overlapping_expected_set_differences'])
                            counts['canonical_expected_set_difference_roots']+=bool(info['canonical_overlapping_expected_set_differences'])
                            prompt_bound=max(prompt_bound,len(pub['question_content'].encode()))
                        allrows.append(record); offset+=1; summary['rows_redecoded']=offset
                        if offset%100==0:
                            print(json.dumps({'rows_redecoded':offset,'retained_bytes':budget.retained,
                                'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
                        del cases; gc.collect()
                    del batch
                del parquet
            gc.collect()
        if offset!=1055 or len(tasks)!=567: raise BundleError('complete-bundle-count')
        write_json(out/'instruments.json',instruments,budget)
        write_json(out/'all-source-dispositions.json',allrows,budget)
        write_json(out/'tasks.json',tasks,budget)
        write_json(out/'exposure-inventory.json',{'paths':exposure_scanned,'exact_links':exposure},budget)
        write_json(out/'canonical-comparison-flags.json',conflicts,budget)
        summary.update(status='COMPLETE_SOURCE_BOUND_PROPOSAL',counts=dict(counts),
            group_counts=group_counts,split_root_counts=dict(collections.Counter(r['split'] for r in tasks)),
            normalization_counts=dict(collections.Counter(v['normalization'] for v in instruments.values())),
            operational_components=1034,active_operational_components=sum(group_counts.values()),
            historical_metadata_files=len(exposure_scanned),historical_exact_link_roots=len(exposure),
            canonical_flag_roots=len(conflicts),maximum_prompt_utf8_bytes=prompt_bound,
            all_original_holds_retained=True,source_specific_conditional_census_only=True,
            limitations=['Source comparison clearance is provisional, not all-input semantic truth.',
                'Operational co-split components are not verified broad semantic families.',
                'Historical inventory covers frozen repository identity metadata, not global pretraining or external logs.',
                'Full publisher private battery retains public-input overlaps; disjoint diagnostic is separate.',
                'Canonical expected-set flags require source-backed disposition, no generated outcomes were read.',
                'No runtime/control qualification, policy fit, task admission or efficacy is implied.'])
    except Exception as exc:
        summary.update(failure_type=type(exc).__name__,failure_tag=str(exc) if isinstance(exc,BundleError) else 'non-content-bearing-parser-or-io-failure')
    finally:
        u=resource.getrusage(resource.RUSAGE_SELF)
        summary.update(elapsed_seconds=time.monotonic()-started,cpu_user_seconds=u.ru_utime,
            cpu_system_seconds=u.ru_stime,maximum_rss_platform_units=u.ru_maxrss,
            rss_units='bytes-on-macos-kib-on-linux',retained_bytes_before_summary=budget.retained,
            unattempted_rows=1055-offset)
        summary['artifacts']={p.name:{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':file_hash(p)}
            for p in out.glob('*.json') if p.name!='summary.json'}
        write_json(out/'summary.json',summary,budget)
    return summary


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--plan',required=True); parser.add_argument('--out',required=True)
    args=parser.parse_args(); plan=inquiry.strict_json(Path(args.plan).read_text())
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(BundleError('global-wall-alarm')))
    signal.alarm(plan['wall_seconds'])
    summary=run(plan,args.out); print(json.dumps({k:summary[k] for k in (
        'status','rows_redecoded','elapsed_seconds','retained_bytes_before_summary')},sort_keys=True))
    return 0 if summary['status']=='COMPLETE_SOURCE_BOUND_PROPOSAL' else 1


if __name__=='__main__':
    sys.exit(main())
