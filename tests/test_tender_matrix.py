"""Execute real contract code with a narrow GenLayer host double; no simulated LLM claims."""
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
class UserError(Exception):
    pass
class Return:
    def __init__(self, calldata): self.calldata = calldata
class Contract:
    def __init_subclass__(cls): pass
    def __new__(cls):
        obj = super().__new__(cls)
        obj.tenders = {}
        return obj

gl = types.SimpleNamespace(Contract=Contract, public=types.SimpleNamespace(write=lambda f:f, view=lambda f:f),
    vm=types.SimpleNamespace(UserError=UserError, Return=Return),
    message=types.SimpleNamespace(sender_address='0xaaa', contract_address='0xcontract', chain_id=61999),
    nondet=types.SimpleNamespace(web=types.SimpleNamespace(), exec_prompt=None))
stub = types.ModuleType('genlayer')
stub.gl, stub.TreeMap, stub.u256 = gl, dict, int
sys.modules['genlayer'] = stub
spec = importlib.util.spec_from_file_location('tender_matrix', ROOT/'contracts/tender_matrix.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

@pytest.fixture
def env():
    gl.message.sender_address = '0xaaa'
    clock = patch.object(m, 'now', return_value=100)
    clock.start()
    yield m.TenderMatrix()
    clock.stop()

def rubric():
    return {'criteria':[{'id':f'c{i}', 'requirement':f'Requirement {i}', 'mandatory':i<3, 'weight':20, 'basis':'proposal'} for i in range(5)], 'sources':[]}
def proposal(): return {'text':'Guaranteed uptime 99.99%; 24h backups; AES-256; 24/7 support; $400/month.', 'evidence':[]}
def create(c, r=None): return c.create_tender('Cloud', m.canonical(r or rubric()), 200, 300)
def commit(c, t, p=None, salt='a'*64):
    p = p or proposal()
    data = json.loads(c.get_tender(t))
    h = m.commitment(61999,'0xcontract',t,data['rubric_hash'],gl.message.sender_address,p,salt)
    c.commit_bid(t,h)
    return p,salt

def rows(labels=None):
    return [{'id':f'c{i}','result':(labels or ['PASS']*5)[i], 'source':'proposal','quote':'24h backups','reason':'explicit offer'} for i in range(5)]

def test_full_lifecycle_and_immutable_finalization(env):
    t=create(env); p,s=commit(env,t)
    with patch.object(m,'now',return_value=200): env.reveal_bid(t,m.canonical(p),s)
    with patch.object(m,'now',return_value=300), patch.object(m,'assess',return_value={'rows':rows(),'documents':[]}):
        env.evaluate_bid(t,'0xaaa'); env.finalize_evaluation(t)
        rank=json.loads(env.get_ranking(t))
        assert rank['eligible']==[{'supplier':'0xaaa','score':100}]
        with pytest.raises(UserError): env.evaluate_bid(t,'0xaaa')
        with pytest.raises(UserError): env.finalize_evaluation(t)

@pytest.mark.parametrize('instant,allowed',[(199,True),(200,False),(300,False)])
def test_commit_boundary(env,instant,allowed):
    t=create(env)
    with patch.object(m,'now',return_value=instant):
        if allowed: commit(env,t)
        else:
            with pytest.raises(UserError): commit(env,t)

@pytest.mark.parametrize('instant,allowed',[(199,False),(200,True),(299,True),(300,False)])
def test_reveal_boundary(env,instant,allowed):
    t=create(env);p,s=commit(env,t)
    with patch.object(m,'now',return_value=instant):
        if allowed: env.reveal_bid(t,m.canonical(p),s)
        else:
            with pytest.raises(UserError): env.reveal_bid(t,m.canonical(p),s)

def test_commitment_replay_domains():
    args=[61999,'0xcontract','1','f'*64,'0xaaa',proposal(),'a'*64]
    base=m.commitment(*args)
    for i,other in [(0,61997),(1,'0xother'),(2,'2'),(3,'e'*64),(4,'0xbbb'),(5,{'text':'edited','evidence':[]}),(6,'b'*64)]:
        changed=list(args);changed[i]=other
        assert m.commitment(*changed)!=base

def test_canonical_whitespace():
    assert m.digest(json.loads('{"a": 1, "b": 2}'))==m.digest(json.loads('{"b":2,"a":1}'))

def test_reveal_wrong_sender_salt_and_mutation(env):
    t=create(env);p,s=commit(env,t)
    with patch.object(m,'now',return_value=200):
        with pytest.raises(UserError): env.reveal_bid(t,m.canonical(p),'z'*64)
        with pytest.raises(UserError): env.reveal_bid(t,m.canonical({'text':'changed','evidence':[]}),s)
        gl.message.sender_address='0xbbb'
        with pytest.raises(UserError): env.reveal_bid(t,m.canonical(p),s)
        gl.message.sender_address='0xaaa'
        env.reveal_bid(t,m.canonical(p),s)
        with pytest.raises(UserError): env.reveal_bid(t,m.canonical(p),s)

def test_capacity_and_duplicate(env):
    t=create(env);commit(env,t)
    with pytest.raises(UserError): commit(env,t)
    for address in ['0xbbb','0xccc']:
        gl.message.sender_address=address;commit(env,t)
    gl.message.sender_address='0xddd'
    with pytest.raises(UserError): commit(env,t)

def test_finalize_pending_and_unrevealed(env):
    t=create(env);p,s=commit(env,t)
    with patch.object(m,'now',return_value=200): env.reveal_bid(t,m.canonical(p),s)
    with patch.object(m,'now',return_value=300):
        with pytest.raises(UserError): env.finalize_evaluation(t)
    t2=create(env);commit(env,t2)
    with patch.object(m,'now',return_value=300):
        env.finalize_evaluation(t2)
        assert json.loads(env.get_ranking(t2))['excluded'][0]['status']=='UNREVEALED'

@pytest.mark.parametrize('labels,status,score',[
    (['PASS']*5,'QUALIFIED',100),(['FAIL']+['UNKNOWN']*4,'DISQUALIFIED',0),
    (['UNKNOWN']+['PASS']*4,'INCONCLUSIVE',80),(['PASS']*3+['FAIL','PASS'],'QUALIFIED',80),
    (['PASS']*4+['UNKNOWN'],'INCONCLUSIVE',80)])
def test_gate_and_score(labels,status,score):
    assert m.summarize(rubric()['criteria'],rows(labels))=={'status':status,'score':score}

def test_evidence_and_quote_validation():
    r=rubric();p=proposal();rs=rows()
    m.validate_rows(rs,r['criteria'],p,[])
    rs[0]['quote']='fabrication'
    with pytest.raises(UserError): m.validate_rows(rs,r['criteria'],p,[])
    rs=rows();r['criteria'][0]['basis']='external'
    with pytest.raises(UserError): m.validate_rows(rs,r['criteria'],p,[])
    rs[0].update(result='UNKNOWN',source='',quote='')
    m.validate_rows(rs,r['criteria'],p,[])

def test_bad_rubric():
    r=rubric();r['criteria'][0]['weight']=True
    with pytest.raises(UserError):m.parse_rubric(m.canonical(r))
    r=rubric();r['criteria'][0]['id']='c1'
    with pytest.raises(UserError):m.parse_rubric(m.canonical(r))

@pytest.mark.parametrize('mode',['status','hash','size','decode','exception','ok'])
def test_fetch_fail_closed(mode):
    body=b'proof'
    item={'url':'https://example.org/proof','sha256':m.hashlib.sha256(body).hexdigest()}
    response=types.SimpleNamespace(status=200,body=body)
    if mode=='status':response.status=500
    if mode=='hash':item['sha256']='0'*64
    if mode=='size':response.body=b'x'*12001
    if mode=='decode':response.body=b'\xff';item['sha256']=m.hashlib.sha256(response.body).hexdigest()
    get=types.SimpleNamespace()
    def fetch(url):
        if mode=='exception':raise RuntimeError()
        return response
    with patch.object(gl.nondet.web,'get',fetch,create=True):
        assert m.fetch_document(item)['available']==(mode=='ok')

@pytest.mark.parametrize('disagree',[False,True])
def test_validator_independently_reexecutes_and_compares_decisions(disagree):
    calls=[]
    def prompt(*args,**kwargs):
        calls.append(args[0]); result=rows()
        if disagree and len(calls)>1:result[0]['result']='FAIL'
        return {'rows':result}
    def run(leader,validator):
        candidate=leader()
        assert validator(Return(candidate)) is (not disagree)
        return candidate
    with patch.object(gl.nondet,'exec_prompt',prompt),patch.object(gl.vm,'run_nondet_unsafe',run,create=True):
        m.assess(rubric(),proposal())
    assert len(calls)==2 and calls[0]==calls[1]

def test_ranking_score_and_address_tie(env):
    t=create(env);data=json.loads(env.get_tender(t))
    for addr,score in [('0xccc',100),('0xbbb',80),('0xaaa',100)]:
        data['bids'][addr]={'proposal':proposal(),'evaluation':{'status':'QUALIFIED','score':score}}
    data['finalized']=True;env._save(t,data)
    assert [r['supplier'] for r in json.loads(env.get_ranking(t))['eligible']]==['0xaaa','0xccc','0xbbb']

def test_offline_helper_matches_contract():
    spec=importlib.util.spec_from_file_location('prepare_bid',ROOT/'scripts/prepare_bid.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    tender={'chain_id':61997,'contract':'0xABCD','id':'7','rubric_hash':m.digest(rubric())}
    salt='c'*64
    assert helper.bid_hash(tender,'0xAaA',proposal(),salt)==m.commitment(61997,'0xABCD','7',tender['rubric_hash'],'0xAaA',proposal(),salt)

def test_validator_rejects_tampered_snapshots_and_errors():
    def run(leader,validator):
        original=leader()
        assert validator(object()) is False
        tampered=dict(original);tampered['documents']=[{'url':'https://evil.example/','text':'fake'}]
        assert validator(Return(tampered)) is False
        missing=dict(original);missing['rows']=original['rows'][:-1]
        assert validator(Return(missing)) is False
        return original
    with patch.object(gl.nondet,'exec_prompt',lambda *a,**kw:{'rows':rows()}),patch.object(gl.vm,'run_nondet_unsafe',run,create=True):
        m.assess(rubric(),proposal())

def test_ranking_unavailable_before_finalization(env):
    with pytest.raises(UserError):env.get_ranking(create(env))

@pytest.mark.parametrize('url',['http://example.org/x','https://127.0.0.1/x','https://user:pass@example.org/x','https://example.org/x#fragment','https://service.local/x'])
def test_invalid_evidence_urls(url):
    assert not m.valid_url(url)
