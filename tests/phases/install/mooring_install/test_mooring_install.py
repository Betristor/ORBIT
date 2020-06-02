"""
Testing framework for the `MooringSystemInstallation` class.
"""

__author__ = "Jake Nunemaker"
__copyright__ = "Copyright 2020, National Renewable Energy Laboratory"
__maintainer__ = "Jake Nunemaker"
__email__ = "Jake.Nunemaker@nrel.gov"


from copy import deepcopy

import pandas as pd
import pytest

from tests.data import test_weather
from ORBIT.library import extract_library_specs
from ORBIT.core._defaults import process_times as pt
from ORBIT.phases.install import MooringSystemInstallation

config = extract_library_specs("config", "mooring_system_install")


def test_simulation_creation():
    sim = MooringSystemInstallation(config)

    assert sim.config == config
    assert sim.env
    assert sim.port
    assert sim.vessel
    assert sim.number_systems


@pytest.mark.parametrize(
    "weather", (None, test_weather), ids=["no_weather", "test_weather"]
)
def test_full_run_logging(weather):
    sim = MooringSystemInstallation(config, weather=weather)
    sim.run()

    lines = (
        config["plant"]["num_turbines"] * config["mooring_system"]["num_lines"]
    )

    df = pd.DataFrame(sim.env.actions)
    df = df.assign(shift=(df.time - df.time.shift(1)))
    assert (df.duration - df["shift"]).fillna(0.0).abs().max() < 1e-9
    assert df[df.action == "Install Mooring Line"].shape[0] == lines

    assert ~df["cost"].isnull().any()
    _ = sim.agent_efficiencies
    _ = sim.detailed_output


@pytest.mark.parametrize(
    "anchor, key",
    [
        ("Suction Pile", "suction_pile_install_time"),
        ("Drag Embedment", "drag_embed_install_time"),
    ],
)
def test_kwargs(anchor, key):

    new = deepcopy(config)
    new["mooring_system"]["anchor_type"] = anchor

    sim = MooringSystemInstallation(new)
    sim.run()
    baseline = sim.total_phase_time

    keywords = ["mooring_system_load_time", "mooring_site_survey_time", key]

    failed = []

    for kw in keywords:

        default = pt[kw]
        kwargs = {kw: default + 2}

        new_sim = MooringSystemInstallation(new, **kwargs)
        new_sim.run()
        new_time = new_sim.total_phase_time

        if new_time > baseline:
            pass

        else:
            failed.append(kw)

    if failed:
        raise Exception(f"'{failed}' not affecting results.")

    else:
        assert True
