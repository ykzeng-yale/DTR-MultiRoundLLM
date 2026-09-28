"""Strict public pre-decision view for future text learners; no fitting/dispatch.

This validates schema and timing fields, not semantic secrecy of arbitrary text.
Source provenance and information-content audits remain the collector's duty.
A hash is a binding identifier, not a causally sufficient embedding.
"""
import copy
import hashlib
import json

FIELDS={'messages','public_observations','remaining_calls','receiver_sha256','generator_sha256','slate'}


def public_view(record):
    if type(record) is not dict or set(record)!=FIELDS:raise ValueError('public-only exact schema required')
    messages=record['messages'];observations=record['public_observations'];slate=record['slate']
    if type(messages) is not list or not messages:raise ValueError('messages')
    for m in messages:
        if type(m) is not dict or set(m)!={'role','content'} or m['role'] not in ('system','user','assistant') or type(m['content']) is not str:raise ValueError('message schema')
    if messages[-1]['role']!='assistant':raise ValueError('decision must follow receiver answer')
    if type(observations) is not list:raise ValueError('observations')
    previous=-1
    for o in observations:
        if type(o) is not dict or set(o)!={'message_index','status','observer_sha256'}:raise ValueError('public observation schema')
        i=o['message_index']
        if type(i) is not int or not previous<i<len(messages) or messages[i]['role']!='assistant':raise ValueError('observation chronology')
        if o['status'] not in ('PASS','FAIL','INCOMPLETE'):raise ValueError('status')
        digest(o['observer_sha256']);previous=i
    for k in ('receiver_sha256','generator_sha256'):digest(record[k])
    if type(record['remaining_calls']) is not int or record['remaining_calls']<0:raise ValueError('remaining calls')
    if type(slate) is not list or not slate:raise ValueError('slate identities')
    stops=0
    for c in slate:
        if type(c) is not dict or set(c)!={'id','kind','text','calls_required'}:raise ValueError('candidate schema')
        if type(c['id']) is not str or not c['id'] or type(c['text']) is not str:raise ValueError('candidate text')
        if c['kind']=='STOP':
            stops+=1
            if c['text']!='' or type(c['calls_required']) is not int or c['calls_required']!=0:raise ValueError('STOP has no prompt/call')
        elif c['kind']=='PROMPT':
            if not c['text'] or type(c['calls_required']) is not int or c['calls_required']<1 or c['calls_required']>record['remaining_calls']:raise ValueError('candidate budget')
        else:raise ValueError('candidate kind')
    if len({c['id'] for c in slate})!=len(slate):raise ValueError('duplicate candidate IDs')
    if stops!=1:raise ValueError('exactly one STOP')
    return copy.deepcopy(record)


def digest(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('version digest')


def serialize(record):
    return json.dumps(public_view(record),ensure_ascii=False,sort_keys=True,separators=(',',':'))


def history_sha256(record):
    return hashlib.sha256(serialize(record).encode()).hexdigest()


def bind_selection(record,probabilities,chosen_id):
    view=public_view(record)
    import math
    ids=[c['id'] for c in view['slate']]
    if type(probabilities) is not list or len(probabilities)!=len(ids) or any(type(p) not in (int,float) or not math.isfinite(p) or p<0 for p in probabilities) or abs(sum(probabilities)-1)>1e-12:raise ValueError('selection vector')
    if chosen_id not in ids or probabilities[ids.index(chosen_id)]<=0:raise ValueError('chosen action unsupported')
    # These are selector probabilities conditional on the realized frozen slate,
    # never generator token likelihoods or marginal text probabilities.
    return {'history_sha256':history_sha256(view),'slate_ids':ids,'probabilities':list(probabilities),'chosen_id':chosen_id,'selected_probability':probabilities[ids.index(chosen_id)]}
