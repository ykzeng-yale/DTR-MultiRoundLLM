import json
import pytest
from experiments.bouchet import calibrate_h100_v1 as pilot


@pytest.mark.parametrize('model,build',[('wrong','build'),('model',None),('model','wrong')])
def test_unfrozen_or_wrong_artifacts_refuse_before_subprocess(tmp_path,monkeypatch,model,build):
    monkeypatch.chdir(tmp_path)
    p=tmp_path/'experiments/bouchet';p.mkdir(parents=True)
    (p/'calibration_plan_v1.json').write_text(json.dumps({'files':{},'model_sha256':model,'build_manifest_sha256':build}))
    monkeypatch.setattr(pilot,'sha',lambda p:'model' if p=='model.gguf' else 'build')
    def forbidden(*args,**kwargs):raise AssertionError('subprocess before artifact validation')
    monkeypatch.setattr(pilot.subprocess,'run',forbidden)
    monkeypatch.setattr(pilot.subprocess,'Popen',forbidden)
    with pytest.raises(ValueError):pilot.main()
