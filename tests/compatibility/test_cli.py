import json
from dataclasses import asdict, replace

from loometric.compatibility.cli import main
from loometric.compatibility.contracts import sha256_value
from loometric.planning.reporting import json_value
from loometric.scheduling.loading import instance_json


def test_declared_candidate_is_blocked_and_never_reexecuted(
    metadata_files, request_context, instance, tmp_path, capsys
):
    directory, manifest, digest = metadata_files
    request_context = replace(
        request_context,
        artifact_fingerprint=digest,
        model_configuration_fingerprint=manifest["model_configuration_fingerprint"],
    )
    request, planning = tmp_path / "request.json", tmp_path / "instance.json"
    wire_request = json_value(asdict(request_context))
    wire_request["predicted_productivity"] = 0.8
    request.write_text(json.dumps(wire_request), encoding="utf-8")
    planning.write_text(instance_json(instance), encoding="utf-8")
    arguments = [
        "assess",
        "--request",
        str(request),
        "--instance",
        str(planning),
        "--artifact",
        str(directory),
        "--expected-fingerprint",
        digest,
    ]
    before = sha256_value(asdict(instance))
    assert main(arguments) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["integration_readiness"] == "NOT_READY"
    assert result["target_to_efficiency"] == "BLOCKED"
    assert result["capacity_application_authorized"] is False
    assert result["converted_efficiency"] is None
    assert result["candidate_value_origin"] == "DECLARED_OFFLINE_CONTEXT_NOT_REEXECUTED"
    assert before == sha256_value(asdict(instance))
    output = tmp_path / "result.json"
    assert main([*arguments, "--output", str(output)]) == 0
    assert json.loads(output.read_text()) == result
    original = output.read_bytes()
    assert main([*arguments, "--output", str(output)]) == 2
    assert output.read_bytes() == original
    invalid = json.loads(request.read_text())
    invalid["actual_productivity"] = "sensitive final label should never be echoed"
    request.write_text(json.dumps(invalid), encoding="utf-8")
    capsys.readouterr()
    assert main(arguments) == 2
    error = capsys.readouterr()
    assert error.out == ""
    assert "sensitive final label" not in error.err
    assert json.loads(error.err)["status"] == "INVALID_INPUT"
