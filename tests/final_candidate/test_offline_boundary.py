"""Native offline admission controls do not start actual development from invalid input."""

import pytest

from loometric.final_candidate import service


def test_actual_hard_limited_worker_rejects_unauthorized_operation():
    with pytest.raises(ValueError, match="CLOSED_AUTHORIZED_OFFLINE_OPERATION_REQUIRED"):
        service._execute({"operation": "develop", "authorized": False})


@pytest.mark.parametrize("operation", ["fit", "tune", "../develop", "publish"])
def test_only_three_fixed_offline_operations_are_accepted(operation):
    with pytest.raises(ValueError, match="CLOSED_OFFLINE_OPERATION_REQUIRED"):
        service.execute(operation)
