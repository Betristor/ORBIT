"""WISDEM Monopile API"""

__author__ = ["Jake Nunemaker"]
__copyright__ = "Copyright 2020, National Renewable Energy Laboratory"
__maintainer__ = "Jake Nunemaker"
__email__ = "jake.nunemaker@nrel.gov"


import os

import yaml
import openmdao.api as om

import ORBIT
from ORBIT import ProjectManager


class OrbitWisdemFixed(om.ExplicitComponent):
    """ORBIT-WISDEM Fixed Substructure API"""

    def setup(self):
        """"""
        # Inputs
        # self.add_discrete_input('weather_file', 'block_island', desc='Weather file to use for installation times.')

        # Vessels
        self.add_discrete_input(
            "wtiv",
            "example_wtiv",
            desc="Vessel configuration to use for installation of foundations and turbines.",
        )
        self.add_discrete_input(
            "feeder",
            "example_feeder",
            desc="Vessel configuration to use for (optional) feeder barges.",
        )
        self.add_discrete_input(
            "num_feeders",
            0,
            desc="Number of feeder barges to use for installation of foundations and turbines.",
        )
        self.add_discrete_input(
            "oss_install_vessel",
            "example_heavy_lift_vessel",
            desc="Vessel configuration to use for installation of offshore substations.",
        )

        # Site
        self.add_input("site_depth", 40.0, units="m", desc="Site depth.")
        self.add_input(
            "site_distance",
            40.0,
            units="km",
            desc="Distance from site to installation port.",
        )
        self.add_input(
            "site_distance_to_landfall",
            50.0,
            units="km",
            desc="Distance from site to landfall for export cable.",
        )
        self.add_input(
            "site_distance_to_interconnection",
            3.0,
            units="km",
            desc="Distance from landfall to interconnection.",
        )
        self.add_input(
            "site_mean_windspeed",
            9.0,
            units="m/s",
            desc="Mean windspeed of the site.",
        )

        # Plant
        self.add_discrete_input(
            "plant_num_turbines", 60, desc="Number of turbines."
        )
        self.add_input(
            "plant_turbine_spacing",
            7,
            desc="Turbine spacing in rotor diameters.",
        )
        self.add_input(
            "plant_row_spacing",
            7,
            desc="Row spacing in rotor diameters. Not used in ring layouts.",
        )
        self.add_input(
            "plant_substation_distance",
            1,
            units="km",
            desc="Distance from first turbine in string to substation.",
        )

        # Turbine
        self.add_input(
            "turbine_rating",
            8.0,
            units="MW",
            desc="Rated capacity of a turbine.",
        )
        self.add_input(
            "turbine_rated_windspeed",
            11.0,
            units="m/s",
            desc="Rated windspeed of the turbine.",
        )
        self.add_input(
            "turbine_capex", 1100, units="USD/kW", desc="Turbine CAPEX"
        )
        self.add_input(
            "turbine_hub_height", 100.0, units="m", desc="Turbine hub height."
        )
        self.add_input(
            "turbine_rotor_diameter",
            130,
            units="m",
            desc="Turbine rotor diameter.",
        )
        self.add_input(
            "tower_weight", 400.0, units="t", desc="Weight of the total tower."
        )
        self.add_input(
            "tower_length", 100, units="m", desc="Total tower length."
        )
        self.add_discrete_input(
            "num_tower_sections", 1, desc="Number of tower sections."
        )
        self.add_input(
            "tower_deck_space",
            0.0,
            desc="Deck space required to transport the tower. Defaults to 0 in order to not be a constraint on installation.",
        )
        self.add_input(
            "nacelle_weight",
            500.0,
            units="t",
            desc="Weight of the rotor nacelle assembly (RNA).",
        )
        self.add_input(
            "nacelle_deck_space",
            0.0,
            desc="Deck space required to transport the rotor nacelle assembly (RNA). Defaults to 0 in order to not be a constraint on installation.",
        )
        self.add_input(
            "blade_weight",
            50.0,
            units="t",
            desc="Weight of an individual blade.",
        )
        self.add_input(
            "blade_deck_space",
            0.0,
            desc="Deck space required to transport a blade. Defaults to 0 in order to not be a constraint on installation.",
        )

        # Port
        self.add_input(
            "port_cost_per_month",
            2e6,
            units="USD/mo",
            desc="Monthly port costs.",
        )

        # Monopile
        self.add_input(
            "monopile_length", 100.0, units="m", desc="Length of monopile."
        )
        self.add_input(
            "monopile_diameter", 7.0, units="m", desc="Diameter of monopile."
        )
        self.add_input(
            "monopile_weight",
            900.0,
            units="t",
            desc="Weight of an individual monopile.",
        )
        self.add_input(
            "monopile_deck_space",
            0.0,
            desc="Deck space required to transport a monopile. Defaults to 0 in order to not be a constraint on installation.",
        )
        self.add_input(
            "transition_piece_weight",
            250.0,
            units="t",
            desc="Weight of an individual transition piece.",
        )
        self.add_input(
            "transition_piece_deck_space",
            0.0,
            desc="Deck space required to transport a transition piece. Defaults to 0 in order to not be a constraint on installation.",
        )

        # Other
        self.add_input(
            "commissioning_pct", 0.01, desc="Commissioning percent."
        )
        self.add_input(
            "decommissioning_pct", 0.15, desc="Decommissioning percent."
        )

        # Outputs
        # Totals
        self.add_output(
            "bos_capex",
            0.0,
            units="USD",
            desc="Total BOS CAPEX not including commissioning or decommissioning.",
        )
        self.add_output(
            "total_capex",
            0.0,
            units="USD",
            desc="Total BOS CAPEX including commissioning and decommissioning.",
        )
        self.add_output(
            "installation_time",
            0.0,
            units="h",
            desc="Total balance of system installation time.",
        )
        self.add_output(
            "installation_capex",
            0.0,
            units="USD",
            desc="Total balance of system installation cost.",
        )

    def compile_orbit_config_file(
        self, inputs, outputs, discrete_inputs, discrete_outputs
    ):
        """"""

        config = {
            # Vessels
            "wtiv": discrete_inputs["wtiv"],
            "feeder": discrete_inputs["feeder"],
            "num_feeders": discrete_inputs["num_feeders"],
            "scour_protection_install_vessel": "example_scour_protection_vessel",
            "trench_dig_vessel": "example_trench_dig_vessel",
            "array_cable_lay_vessel": "example_cable_lay_vessel",
            "array_cable_bury_vessel": "example_cable_lay_vessel",
            "export_cable_lay_vessel": "example_cable_lay_vessel",
            "export_cable_bury_vessel": "example_cable_lay_vessel",
            # Site/plant
            "site": {
                "depth": float(inputs["site_depth"]),
                "distance": float(inputs["site_distance"]),
                "distance_to_landfall": float(
                    inputs["site_distance_to_landfall"]
                ),
                "distance_to_beach": 0,
                "distance_to_interconnection": float(
                    inputs["site_distance_to_interconnection"]
                ),
                "mean_windspeed": float(inputs["site_mean_windspeed"]),
            },
            "plant": {
                "layout": "grid",
                "num_turbines": discrete_inputs["plant_num_turbines"],
                "row_spacing": float(inputs["plant_row_spacing"]),
                "turbine_spacing": float(inputs["plant_turbine_spacing"]),
                "substation_distance": float(
                    inputs["plant_substation_distance"]
                ),
            },
            "port": {
                "num_cranes": 1,
                "monthly_rate": float(inputs["port_cost_per_month"]),
            },
            # Turbine + components
            "turbine": {
                "hub_height": float(inputs["turbine_hub_height"]),
                "rotor_diameter": float(inputs["turbine_rotor_diameter"]),
                "turbine_rating": float(inputs["turbine_rating"]),
                "rated_windspeed": float(inputs["turbine_rated_windspeed"]),
                "tower": {
                    "type": "Tower",
                    "deck_space": float(inputs["tower_deck_space"]),
                    "weight": float(inputs["tower_weight"]),
                    "length": float(inputs["tower_length"]),
                    "sections": discrete_inputs["num_tower_sections"],
                },
                "nacelle": {
                    "type": "Nacelle",
                    "deck_space": float(inputs["nacelle_deck_space"]),
                    "weight": float(inputs["nacelle_weight"]),
                },
                "blade": {
                    "type": "Blade",
                    "deck_space": float(inputs["blade_deck_space"]),
                    "weight": float(inputs["blade_weight"]),
                },
            },
            # Substructure components
            "monopile": {
                "type": "Monopile",
                "length": float(inputs["monopile_length"]),
                "diameter": float(inputs["monopile_diameter"]),
                "deck_space": float(inputs["monopile_deck_space"]),
                "weight": float(inputs["monopile_weight"]),
            },
            "transition_piece": {
                "type": "Transition Piece",
                "deck_space": float(inputs["transition_piece_deck_space"]),
                "weight": float(inputs["transition_piece_weight"]),
            },
            "scour_protection_design": {"cost_per_tonne": 20,},
            # Electrical
            "array_system_design": {
                "cables": ["XLPE_400mm_33kV", "XLPE_630mm_33kV"]
            },
            "array_system": {"strategy": "simultaneous"},
            "export_system": {"strategy": "simultaneous"},
            "export_system_design": {
                "cables": "XLPE_500mm_132kV",
                "percent_added_length": 0.1,
            },
            "substation_design": {},
            "monopile_design": {},
            # Phase Specific
            "OffshoreSubstationInstallation": {
                "oss_install_vessel": "example_heavy_lift_vessel",
                "feeder": "example_heavy_feeder",
                "num_feeders": 1,
            },
            # Other
            "commissioning": float(inputs["commissioning_pct"]),
            "decomissioning": float(inputs["decommissioning_pct"]),
            "turbine_capex": float(inputs["turbine_capex"]),
            # Phases
            "design_phases": [
                "MonopileDesign",
                "ScourProtectionDesign",
                "ArraySystemDesign",
                "ExportSystemDesign",
                "OffshoreSubstationDesign",
            ],
            "install_phases": [
                "MonopileInstallation",
                "ScourProtectionInstallation",
                "TurbineInstallation",
                "ArrayCableInstallation",
                "ExportCableInstallation",
                "OffshoreSubstationInstallation",
            ],
        }

        self._orbit_config = config
        return config

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):

        config = self.compile_orbit_config_file(
            inputs, outputs, discrete_inputs, discrete_outputs
        )

        project = ProjectManager(config)
        project.run_project()

        outputs["bos_capex"] = project.bos_capex
        outputs["total_capex"] = project.total_capex
        outputs["installation_time"] = project.installation_time
        outputs["installation_capex"] = project.installation_capex


if __name__ == "__main__":

    prob = om.Problem()
    prob.model = OrbitWisdemFixed()
    prob.setup()

    prob.run_driver()

    prob.model.list_inputs()
    prob.model.list_outputs()
