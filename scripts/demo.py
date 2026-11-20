#!/usr/bin/env python3
"""Offline lifecycle demonstration with explicit fixture decisions, NOT live AI consensus."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('contract_test_host',ROOT/'tests/test_tender_matrix.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
m=host.m;gl=host.gl;c=m.TenderMatrix()
r=json.loads((ROOT/'examples/rubric.json').read_text())
with patch.object(m,'now',return_value=100):
    t=c.create_tender('DAO cloud infrastructure',m.canonical(r),200,300)
    data=json.loads(c.get_tender(t));bids=[]
    for suffix in 'abc':
        supplier='0x'+suffix*40;gl.message.sender_address=supplier
        p=json.loads((ROOT/f'examples/supplier-{suffix}.json').read_text());salt=suffix*64
        h=m.commitment(61999,'0xcontract',t,data['rubric_hash'],supplier,p,salt)
        c.commit_bid(t,h);bids.append((supplier,p,salt))
with patch.object(m,'now',return_value=200):
    for supplier,p,salt in bids:
        gl.message.sender_address=supplier;c.reveal_bid(t,m.canonical(p),salt)
with patch.object(m,'now',return_value=300):
    for index,(supplier,p,salt) in enumerate(bids):
        labels=['PASS']*5
        if index==1:labels[4]='FAIL'
        if index==2:labels[2]='UNKNOWN'
        quotes=[['99.95% monthly uptime','every 12 hours','AES-256 encryption at rest and TLS 1.3 in transit','24 hours daily, seven days a week','USD 450 per month, inclusive of all mandatory charges'],
                ['99.99% uptime monthly','daily backups','AES-256 at rest and TLS 1.3 in transit','24/7','USD 650 per month inclusive of all mandatory charges'],
                ['99.9% monthly uptime','every 24 hours','','around the clock, every day','USD 400 monthly inclusive of all mandatory charges']][index]
        rows=[{'id':criterion['id'],'result':label,'source':'proposal' if label!='UNKNOWN' else '',
               'quote':quote,'reason':'Offline fixture decision; no LLM called.'}
              for criterion,label,quote in zip(r['criteria'],labels,quotes)]
        m.validate_rows(rows,r['criteria'],p,[])
        with patch.object(m,'assess',return_value={'rows':rows,'documents':[]}):c.evaluate_bid(t,supplier)
    c.finalize_evaluation(t)
result=json.loads(c.get_ranking(t))
assert len(result['eligible'])==1 and result['eligible'][0]['score']==100
assert {x['status'] for x in result['excluded']}=={'DISQUALIFIED','INCONCLUSIVE'}
print(json.dumps({'mode':'OFFLINE_FIXTURE_NOT_LIVE_CONSENSUS','ranking':result},indent=2))
