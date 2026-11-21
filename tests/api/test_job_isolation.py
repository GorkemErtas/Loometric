import os
import subprocess
import sys
from pathlib import Path


def test_server_and_actual_optimizer_children_read_no_protected_ml_data(tmp_path):
    root = Path(__file__).resolve().parents[2]
    (tmp_path / "sitecustomize.py").write_text(
        r"""
import importlib.abc,pathlib,sys
root=pathlib.Path.cwd().resolve()
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=pathlib.Path(args[0]).resolve()
        forbidden=(root/'data',root/'src/loometric/prediction',root/'src/loometric/data')
        assert not any(path.is_relative_to(p) for p in forbidden),'Protected ML path access'
class NoML(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        # OR-Tools' existing numpy/pandas dependencies are allowed; ML/data loaders are not.
        roots=('sklearn','joblib','loometric.prediction','loometric.data','loometric.evaluation')
        blocked=any(fullname==p or fullname.startswith(p+'.') for p in roots)
        assert not blocked,'Protected ML import'
sys.addaudithook(guard)
sys.meta_path.insert(0,NoML())
""",
        encoding="utf-8",
    )
    code = r"""
import anyio,httpx,pathlib,secrets
from pydantic import SecretStr
from loometric.api.app import create_app
from loometric.api.settings import Settings
from loometric.api.codec import input_json
from loometric.planning.loading import parse_json
try:
    open('data/raw/probe.csv')
except AssertionError:
    pass
else:
    raise AssertionError('Protected path probe bypassed')
def load(name):
    return parse_json(pathlib.Path('examples',name).read_text(encoding='utf-8'))
async def run():
    settings=Settings(token=SecretStr(secrets.token_urlsafe(32)))
    app=create_app(settings)
    async with app.router.lifespan_context(app),httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='http://127.0.0.1',
        headers={'Authorization':'Bearer '+settings.token.get_secret_value(),
                 'Content-Type':'application/json'}) as client:
        spec=load('scenarios/capacity-optimizer-recovery.json')
        spec['scheduling']['solver']={'wall_time_seconds_per_phase':1,'deterministic_time_per_phase':1}
        for kind,body in (
            ('scheduling',{'instance':load('scheduling/hand-enumerated.json')}),
            ('scenarios',{'baseline':load('scenarios/routing-baseline.json'),'specification':spec})):
            response=await client.post('/api/v1/jobs/'+kind,content=input_json(body))
            assert response.status_code==202,response.text
            info=response.json()['data']
            with anyio.fail_after(20):
                while True:
                    status=(await client.get(info['polling_url'])).json()['data']
                    if status['status'] not in ('QUEUED','RUNNING'):
                        break
                    await anyio.sleep(.01)
            assert status['status']=='SUCCEEDED',status
            result=await client.get(status['result_url'])
            assert result.status_code==200,result.text
anyio.run(run)
print('Job server and native children ML isolation verified')
"""
    env = {**os.environ, "PYTHONPATH": str(tmp_path) + os.pathsep + str(root / "src")}
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, cwd=root, capture_output=True, text=True, timeout=45
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "ML isolation verified" in result.stdout
