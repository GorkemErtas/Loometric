"""Verify the optional pinned native solver is installed and actually executable."""

from importlib.metadata import version

from ortools.sat.python import cp_model


def test_pinned_native_cp_sat_executes():
    assert version("ortools") == "9.15.6755"
    model = cp_model.CpModel()
    choice = model.new_bool_var("choice")
    model.minimize(choice)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    assert solver.solve(model) == cp_model.OPTIMAL
    assert solver.value(choice) == 0
