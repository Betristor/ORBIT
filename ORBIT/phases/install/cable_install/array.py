"""`ArrayCableInstallation` class and related processes."""

__author__ = "Jake Nunemaker"
__copyright__ = "Copyright 2020, National Renewable Energy Laboratory"
__maintainer__ = "Jake Nunemaker"
__email__ = "jake.nunemaker@nrel.gov"


from copy import deepcopy

from marmot import process

from ORBIT.core import Vessel
from ORBIT.core.logic import position_onsite
from ORBIT.phases.install import InstallPhase
from ORBIT.core.exceptions import InsufficientCable

from .common import SimpleCable as Cable
from .common import (
    lay_cable,
    bury_cable,
    prep_cable,
    lower_cable,
    pull_in_cable,
    lay_bury_cable,
    terminate_cable,
    load_cable_on_vessel,
    dig_trench,
)


class ArrayCableInstallation(InstallPhase):
    """Array Cable Installation Phase"""

    phase = "Array Cable Installation"

    #:
    expected_config = {
        "array_cable_install_vessel": "str",
        "array_cable_bury_vessel": "str (optional)",
        "array_cable_trench_vessel": "str (optional)",
        "site": {"distance": "km"},
        "array_system": {
            "cables": {
                "name (variable)": {
                    "linear_density": "t/km",
                    "cable_sections": [
                        ("length, km", "int", "speed, km/h (optional)")
                    ],
                }
            }
        },
    }

    def __init__(self, config, weather=None, **kwargs):
        """
        Creates an instance of ArrayCableInstallation.

        Parameters
        ----------
        config : dict
            Simulation specific configuration.
        weather : np.ndarray
            Weather profile at site.
        """

        super().__init__(weather, **kwargs)

        config = self.initialize_library(config, **kwargs)
        self.config = self.validate_config(config)
        self.extract_defaults()

        self.initialize_port()
        self.setup_simulation(**kwargs)

    def setup_simulation(self, **kwargs):
        """
        Setup method for ArrayCableInstallation phase.
        - Extracts key inputs
        -
        """

        self.initialize_installation_vessel()
        self.initialize_burial_vessel()
        self.initialize_trench_vessel()

        self.cable_data = [
            (Cable(data["linear_density"]), deepcopy(data["cable_sections"]))
            for _, data in self.config["array_system"]["cables"].items()
        ]

        # Perform cable installation
        install_array_cables(
            self.install_vessel,
            distance=self.config["site"]["distance"],
            cable_data=self.cable_data,
            burial_vessel=self.bury_vessel,
            trench_vessel=self.trench_vessel,
            **kwargs,
        )

    def initialize_installation_vessel(self):
        """Creates the array cable installation vessel."""

        # Vessel name and costs
        vessel_specs = self.config.get("array_cable_install_vessel", None)
        name = vessel_specs.get("name", "Array Cable Installation Vessel")

        vessel = Vessel(name, vessel_specs)
        self.env.register(vessel)

        vessel.initialize()
        vessel.at_port = True
        vessel.at_site = False
        self.install_vessel = vessel

    def initialize_burial_vessel(self):
        """Creates the array cable burial vessel."""

        # Vessel name and costs
        vessel_specs = self.config.get("array_cable_bury_vessel", None)
        if vessel_specs is None:
            self.bury_vessel = None
            return
        name = vessel_specs.get("name", "Array Cable Burial Vessel")

        vessel = Vessel(name, vessel_specs)
        self.env.register(vessel)

        vessel.initialize()
        vessel.at_port = True
        vessel.at_site = False
        self.bury_vessel = vessel

    def initialize_trench_vessel(self):
        """Creates the array cable trenching vessel."""

        # Vessel name and costs
        vessel_specs = self.config.get("array_cable_trench_vessel", None)
        if vessel_specs is None:
            self.trench_vessel = None
            return
        name = vessel_specs.get("name", "Array Cable Trench Vessel")

        vessel = Vessel(name, vessel_specs)
        self.env.register(vessel)

        vessel.initialize()
        vessel.at_port = True
        vessel.at_site = False
        self.trench_vessel = vessel

    @property
    def detailed_output(self):
        """Detailed outputs of the array system installation."""

        outputs = {self.phase: {**self.agent_efficiencies}}

        return outputs


@process
def install_array_cables(
    vessel, distance, cable_data, burial_vessel=None, trench_vessel=None, **kwargs
):
    """
    Simulation of the installation of array cables.

    Parameters
    ----------
    vessel : Vessel
        Cable installation vessel.
    cable_data : list
        List of tuples containing `Cable` instances and sections.
    burial_vessel : Vessel
        Optional configuration for burial vessel. If configured, the
        installation vessel only lays the cable on the seafloor and this
        vessel will bury them at the end of the simulation.
    trench_vessel: Vessel
        Optional configuration for trenching vessel.  If configured, the
        trenching vessel travels along the cable route prior to arrival of
        the cable lay vessel and digs a trench.
    """
    # print(cable_data)
    # for c,s in cable_data:
    #     print(c,s)
    # Conduct trenching along cable routes before laying cable
    if trench_vessel is None:
        pass
    else:
        for cable, sections in cable_data:
            vessel.cable_storage.reset()

            while True:
                if trench_vessel.at_port:
                    trench_vessel.at_port = False
                    yield trench_vessel.transit(distance, **kwargs)
                    trench_vessel.at_site = True

                elif trench_vessel.at_site:
                    try:
                        print(sections)
                        length, num_sections, *extra = sections.pop(0)
                        print('length',length,'ns',num_sections)
                        for _ in range(num_sections):
                            print('installing',length,'for',_,'of',num_sections,'sections')
                            # section = vessel.cable_storage.get_cable(length)
                            dig_array_cables_trench(trench_vessel, length, **kwargs)
                    except IndexError:
                        trench_vessel.at_site = False
                        yield trench_vessel.transit(distance, **kwargs)
                        trench_vessel.at_port = True
                        break
            # Transit back to port
            trench_vessel.at_site = False
            yield trench_vessel.transit(distance, **kwargs)
            trench_vessel.at_port = True

    to_bury = []

    for cable, sections in cable_data:
        vessel.cable_storage.reset()

        while True:
            if vessel.at_port:
                yield load_cable_on_vessel(vessel, cable, **kwargs)

                vessel.at_port = False
                yield vessel.transit(distance, **kwargs)
                vessel.at_site = True

            elif vessel.at_site:

                try:
                    length, num_sections, *extra = sections.pop(0)
                    if extra:
                        speed = extra[0]

                        if burial_vessel is None:
                            specs = {**kwargs, "cable_lay_bury_speed": speed}

                        else:
                            specs = {**kwargs, "cable_lay_speed": speed}

                    else:
                        specs = deepcopy(kwargs)

                except IndexError:
                    vessel.at_site = False
                    yield vessel.transit(distance, **kwargs)
                    vessel.at_port = True
                    break

                for _ in range(num_sections):

                    try:
                        section = vessel.cable_storage.get_cable(length)

                    except InsufficientCable:

                        yield vessel.transit(distance, **kwargs)
                        yield load_cable_on_vessel(vessel, cable, **kwargs)
                        yield vessel.transit(distance, **kwargs)
                        section = vessel.cable_storage.get_cable(length)

                    # Prep for cable laying procedure (at substructure 1)
                    yield position_onsite(vessel, **kwargs)
                    yield prep_cable(vessel, **kwargs)
                    yield pull_in_cable(vessel, **kwargs)
                    yield terminate_cable(vessel, **kwargs)
                    yield lower_cable(vessel, **kwargs)

                    # Cable laying procedure
                    if burial_vessel is None:
                        yield lay_bury_cable(vessel, section, **specs)

                    else:
                        yield lay_cable(vessel, section, **specs)
                        to_bury.append(section)

                    # Post cable laying procedure (at substructure 2)
                    yield prep_cable(vessel, **kwargs)
                    yield pull_in_cable(vessel, **kwargs)
                    yield terminate_cable(vessel, **kwargs)

        # Transit back to port
        vessel.at_site = False
        yield vessel.transit(distance, **kwargs)
        vessel.at_port = True

    if burial_vessel is None:
        vessel.submit_debug_log(
            message="Array cable lay/burial process completed!"
        )

    else:
        vessel.submit_debug_log(message="Array cable lay process completed!")
        bury_array_cables(burial_vessel, to_bury, **kwargs)


@process
def bury_array_cables(vessel, sections, **kwargs):
    """
    Simulation for the burial of array cables if configured.

    Parameters
    ----------
    vessel : Vessel
        Performing vessel.
    sections : list
        List of cable sections that need to be buried at site.
    """

    for length in sections:
        yield position_onsite(vessel, site_position_time=2)
        yield bury_cable(vessel, length, **kwargs)

    vessel.submit_debug_log(message="Array cable burial process completed!")

@process
def dig_array_cables_trench(vessel, sections, **kwargs):
    """
    Simulation for digging a trench for the array cables (if configured).

    Parameters
    ----------
    vessel : Vessel
        Performing vessel.
    sections : list
        List of cable sections that need to be buried at site.
    """

    for length in sections:
        yield position_onsite(vessel, site_position_time=2)
        yield dig_trench(vessel, length, **kwargs)

    vessel.submit_debug_log(message="Array cable trench digging process completed!")
