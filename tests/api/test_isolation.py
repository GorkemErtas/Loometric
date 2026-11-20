import os
import subprocess
import sys
from pathlib import Path


def test_http_and_native_children_cannot_read_ml_data_or_import_models(tmp_path):
    root = Path(__file__).resolve().parents[2]
    # Python loads this in the clean server probe AND its actual native children.
    # This hook is test-only evidence; no production request may configure it.
    (tmp_path / "sitecustomize.py").write_text(
        r"""
import importlib.abc,pathlib,sys
root=pathlib.Path.cwd().resolve()
def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=pathlib.Path(args[0].decode() if isinstance(args[0],bytes) else args[0]).resolve()
        if path.is_relative_to(root/'data') or path.is_relative_to(root/'src/loometric/prediction'):
            raise AssertionError('Protected ML path access')
class NoML(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        roots=('pandas','numpy','sklearn','joblib','ortools')
        packages=('loometric.prediction','loometric.data','loometric.evaluation','loometric.benchmarks')
        if fullname.split('.')[0] in roots or fullname.startswith(packages):
            raise AssertionError('Protected model import')
sys.addaudithook(guard)
sys.meta_path.insert(0,NoML())
""",
        encoding="utf-8",
    )
    code = r"""
import anyio,httpx,json,pathlib,secrets,sys
from pydantic import SecretStr
from loometric.api.app import create_app
from loometric.api.settings import Settings
from loometric.api.codec import input_json
from loometric.planning.loading import parse_json
try:
    open('data/raw/forbidden-probe.csv')
except AssertionError:
    pass
else:
    raise AssertionError('Relative protected path bypass')
def load(name):
    return parse_json(pathlib.Path('examples',name).read_text(encoding='utf-8'))
async def run():
    settings=Settings(token=SecretStr(secrets.token_urlsafe(32)))
    app=create_app(settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),
            base_url='http://127.0.0.1',headers={
            'Authorization':'Bearer '+settings.token.get_secret_value(),
            'Content-Type':'application/json'}) as client:
        async def post(path,body):
            r=await client.post('/api/v1/'+path,content=input_json(body))
            assert r.status_code==200,r.text
            return r.json()['data']
        assert (await client.get('/api/v1/health')).status_code==200
        assert (await client.get('/api/v1/capabilities')).status_code==200
        await post('planning/capacity',{'scenario':load('planning/capacity-demo.json')})
        instance=load('scenarios/capacity-baseline.json')
        dispatched=await post('scheduling/dispatch',{'instance':instance})
        await post('scheduling/verify',{'instance':instance,'schedule':dispatched['schedule']})
        compared=await post('scenarios/compare',{'baseline':instance,
            'specification':load('scenarios/additional-workers.json')})
        assert compared['scenario']['evaluation']['metrics']['scheduled_units']==55
    assert not any(name.split('.')[0] in ('pandas','numpy','sklearn','joblib','ortools') or
        name.startswith(('loometric.prediction','loometric.data')) for name in sys.modules)
anyio.run(run)
print('HTTP and native-child ML isolation verified')
"""
    env = {**os.environ, "PYTHONPATH": str(tmp_path) + os.pathsep + str(root / "src")}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "isolation verified" in result.stdout
