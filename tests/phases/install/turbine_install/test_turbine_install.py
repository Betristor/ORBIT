"""Tests for the `MonopileInstallation` class without feeder barges."""

__author__ = "Jake Nunemaker"
__copyright__ = "Copyright 2019, National Renewable Energy Laboratory"
__maintainer__ = "Jake Nunemaker"
__email__ = "jake.nunemaker@nrel.gov"


from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from tests.data import test_weather
from ORBIT.library import initialize_library, extract_library_specs
from ORBIT.core._defaults import process_times as pt
from ORBIT.phases.install import TurbineInstallation

initialize_library(pytest.library)
config_wtiv = extract_library_specs("config", "turbine_install_wtiv")
config_wtiv_feeder = extract_library_specs("config", "turbine_install_feeder")
config_wtiv_multi_feeder = deepcopy(config_wtiv_feeder)
config_wtiv_multi_feeder["num_feeders"] = 2


@pytest.mark.parametrize(
    "config",
    (config_wtiv, config_wtiv_feeder, config_wtiv_multi_feeder),
    ids=["wtiv_only", "single_feeder", "multi_feeder"],
)
def test_simulation_setup(config):

    sim = TurbineInstallation(config)
    assert sim.config == config
    assert sim.env
    assert sim.port.crane.capacity == config["port"]["num_cranes"]
    assert sim.num_turbines == config["plant"]["num_turbines"]

    t = len([i for i in sim.port.items if i.type == "TowerSection"])
    assert t == sim.num_turbines

    n = len([i for i in sim.port.items if i.type == "Nacelle"])
    assert n == sim.num_turbines

    b = len([i for i in sim.port.items if i.type == "Blade"])
    assert b == sim.num_turbines * 3


@pytest.mark.parametrize(
    "config",
    (config_wtiv, config_wtiv_feeder, config_wtiv_multi_feeder),
    ids=["wtiv_only", "single_feeder", "multi_feeder"],
)
def test_vessel_creation(config):

    sim = TurbineInstallation(config)
    assert sim.wtiv
    assert sim.wtiv.jacksys
    assert sim.wtiv.crane
    assert sim.wtiv.storage

    if config.get("feeder", None) is not None:
        assert len(sim.feeders) == config["num_feeders"]

        for feeder in sim.feeders:
            assert feeder.jacksys
            assert feeder.storage


@pytest.mark.parametrize(
    "config",
    (config_wtiv, config_wtiv_feeder, config_wtiv_multi_feeder),
    ids=["wtiv_only", "single_feeder", "multi_feeder"],
)
@pytest.mark.parametrize(
    "weather", (None, test_weather), ids=["no_weather", "test_weather"]
)
def test_for_complete_logging(weather, config):

    sim = TurbineInstallation(config)
    sim.run()

    df = pd.DataFrame(sim.env.actions)
    df = df.assign(shift=(df["time"] - df["time"].shift(1)))

    for vessel in df["agent"].unique():
        _df = df[df["agent"] == vessel].copy()
        _df = _df.assign(shift=(_df["time"] - _df["time"].shift(1)))
        assert (_df["shift"] - _df["duration"]).abs().max() < 1e-9

    assert ~df["cost"].isnull().any()


@pytest.mark.parametrize(
    "config",
    (config_wtiv, config_wtiv_feeder, config_wtiv_multi_feeder),
    ids=["wtiv_only", "single_feeder", "multi_feeder"],
)
def test_for_complete_installation(config):

    sim = TurbineInstallation(config)
    sim.run()

    installed_nacelles = len(
        [a for a in sim.env.actions if a["action"] == "Attach Nacelle"]
    )
    assert installed_nacelles == sim.num_turbines


# @pytest.mark.parametrize(
#     "config",
#     (config_wtiv, config_wtiv_feeder, config_wtiv_multi_feeder),
#     ids=["wtiv_only", "single_feeder", "multi_feeder"],
# )
# def test_for_efficiencies(config):

#     sim = TurbineInstallation(config)
#     sim.run()

#     assert 0 <= sim.detailed_output["Example WTIV_operational_efficiency"] <= 1
#     if sim.feeders is None:
#         assert (
#             0
#             <= sim.detailed_output["Example WTIV_cargo_weight_utilization"]
#             <= 1
#         )
#         assert (
#             0
#             <= sim.detailed_output["Example WTIV_deck_space_utilization"]
#             <= 1
#         )
#     else:
#         for feeder in sim.feeders:
#             name = feeder.name
#             assert (
#                 0 <= sim.detailed_output[f"{name}_operational_efficiency"] <= 1
#             )
#             assert (
#                 0
#                 <= sim.detailed_output[f"{name}_cargo_weight_utilization"]
#                 <= 1
#             )
#             assert (
#                 0 <= sim.detailed_output[f"{name}_deck_space_utilization"] <= 1
#             )


def test_kwargs():

    sim = TurbineInstallation(config_wtiv)
    sim.run()
    baseline = sim.total_phase_time

    keywords = [
        "tower_section_fasten_time",
        "tower_section_release_time",
        "tower_section_attach_time",
        "nacelle_fasten_time",
        "nacelle_release_time",
        "nacelle_attach_time",
        "blade_fasten_time",
        "blade_release_time",
        "blade_attach_time",
        "site_position_time",
        "crane_reequip_time",
    ]

    failed = []

    for kw in keywords:

        default = pt[kw]
        kwargs = {kw: default + 2}

        new_sim = TurbineInstallation(config_wtiv, **kwargs)
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


def test_multiple_tower_sections():

    sim = TurbineInstallation(config_wtiv)
    sim.run()
    baseline = len(
        [a for a in sim.env.actions if a["action"] == "Attach Tower Section"]
    )

    two_sections = deepcopy(config_wtiv)
    two_sections["turbine"]["tower"]["sections"] = 2

    sim2 = TurbineInstallation(two_sections)
    sim2.run()
    new = len(
        [a for a in sim2.env.actions if a["action"] == "Attach Tower Section"]
    )

    assert new == 2 * baseline

    df = pd.DataFrame(sim.env.actions)
    for vessel in df["agent"].unique():

        vl = df[df["agent"] == vessel].copy()
        vl = vl.assign(shift=(vl["time"] - vl["time"].shift(1)))

        assert (vl["shift"] - vl["duration"]).abs().max() < 1e-9
