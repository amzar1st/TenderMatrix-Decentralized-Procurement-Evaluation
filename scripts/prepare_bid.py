#!/usr/bin/env python3
"""Create a commitment offline. Never submit salt or proposal to a public hash helper."""
import argparse
import hashlib
import json
import secrets
from pathlib import Path

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)

def bid_hash(tender,supplier,proposal,salt):
    payload={'domain':'TenderMatrix.bid.v1','chain_id':tender['chain_id'],'contract':tender['contract'].lower(),
             'tender_id':tender['id'],'rubric_hash':tender['rubric_hash'],'supplier':supplier.lower(),
             'proposal':proposal,'salt':salt}
    return hashlib.sha256(canonical(payload).encode()).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tender',type=Path,required=True,help='Saved get_tender JSON result')
    p.add_argument('--supplier',required=True)
    p.add_argument('--proposal',type=Path,required=True)
    p.add_argument('--secret',type=Path,required=True,help='New private *.secret.json path; never commit it')
    a=p.parse_args()
    tender=json.loads(a.tender.read_text());proposal=json.loads(a.proposal.read_text());salt=secrets.token_hex(32)
    # Exclusive creation avoids silently destroying the only reveal salt.
    import os
    fd=os.open(a.secret,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump({'tender_id':tender['id'],'supplier':a.supplier.lower(),'proposal_json':canonical(proposal),'salt':salt},f,indent=2)
    print(bid_hash(tender,a.supplier,proposal,salt))
