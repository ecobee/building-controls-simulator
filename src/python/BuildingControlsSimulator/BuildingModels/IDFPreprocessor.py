# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil
import logging

import pandas as pd
import attr
import numpy as np

from eppy.modeleditor import IDF

logger = logging.getLogger(__name__)


@attr.s(kw_only=True, init=True)
class IDFPreprocessor:
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs."""

    # user must supply an idf file as either 1) full path, or 2) a file in self.idf_dir
    idf_file = attr.ib()

    init_temperature = attr.ib(type=float, default=21.0)
    init_humidity = attr.ib(type=float, default=50.0)
    init_control_type = attr.ib(type=int, default=1)
    debug = attr.ib(type=bool, default=False)
    timesteps_per_hour = attr.ib(type=int, default=12)
    conditioned_zones = attr.ib(factory=list)
    occupied_zones = attr.ib(factory=list)
    thermostat_zones = attr.ib(factory=list)
    zone_lists = attr.ib(factory=dict)
    zone_outputs = attr.ib(factory=list)
    building_outputs = attr.ib(factory=list)
    # the output spec is created during preprocessing of IDF file
    output_spec = attr.ib(factory=dict)

    # first, terminate env vars, these will raise exceptions if undefined
    ep_version = attr.ib(default=os.environ.get("ENERGYPLUS_INSTALL_VERSION"))
    idf_dir = attr.ib(default=os.environ.get("IDF_DIR"))
    idd_path = attr.ib(default=os.environ.get("EPLUS_IDD"))

    # output variable spec
    # .rdd file for all output variables
    zone_output_spec = attr.ib()
    building_output_spec = attr.ib()

    # for reference on how attr defaults wor for mutable types (e.g. dict) see:
    # https://www.attrs.org/en/stable/init.html#defaults
    @zone_output_spec.default
    def get_zone_output_spec(self):
        return {
            "zone_air_temperature": {
                "dtype": "float32",
                "eplus_name": "Zone Air Temperature",
            },
            "zone_thermostat_heating_setpoint_temperature": {
                "dtype": "float32",
                "eplus_name": "Zone Thermostat Heating Setpoint Temperature",
            },
            "zone_thermostat_cooling_setpoint_temperature": {
                "dtype": "float32",
                "eplus_name": "Zone Thermostat Cooling Setpoint Temperature",
            },
            "zone_air_system_sensible_heating_rate": {
                "dtype": "float32",
                "eplus_name": "Zone Air System Sensible Heating Rate",
            },
            "zone_air_system_sensible_cooling_rate": {
                "dtype": "float32",
                "eplus_name": "Zone Air System Sensible Cooling Rate",
            },
            "zone_total_internal_total_heating_rate": {
                "dtype": "float32",
                "eplus_name": "Zone Total Internal Total Heating Rate",
            },
            "zone_mean_air_dewpoint_temperature": {
                "dtype": "float32",
                "eplus_name": "Zone Mean Air Dewpoint Temperature",
            },
            "zone_mean_air_humidity_ratio": {
                "dtype": "float32",
                "eplus_name": "Zone Mean Air Humidity Ratio",
            },
        }

    @building_output_spec.default
    def get_building_output_spec(self):
        return {
            "environment": {
                "site_outdoor_air_relative_humidity": {
                    "dtype": "float32",
                    "eplus_name": "Site Outdoor Air Relative Humidity",
                },
                "site_outdoor_air_drybulb_temperature": {
                    "dtype": "float32",
                    "eplus_name": "Site Outdoor Air Drybulb Temperature",
                },
                "eplus_name": "Environment",
            },
        }

    def __attrs_post_init__(self):
        """Initialize `IDFPreprocessor` with an IDF file and desired actions"""
        # make output dirs
        os.makedirs(self.idf_prep_dir, exist_ok=True)

        # set energyplus dictionary version for eppy
        IDF.setiddname(self.idd_path)

        # first make sure idf file exists
        if os.path.isfile(self.idf_file):
            self.idf_name = os.path.basename(self.idf_file)
        else:
            self.idf_name = self.idf_file
            self.idf_file = os.path.join(self.idf_dir, self.idf_name)
            if not os.path.isfile(self.idf_file):
                raise ValueError(f"""{self.idf_file} is not a file.""")
        # make sure idf is valid IDF file
        if not self.check_valid_idf(self.idf_file):
            raise ValueError(f"""{self.idf_file} is not a valid IDF file.""")

        logger.info(
            "IDFPreprocessor loading .idf file: {}".format(self.idf_file)
        )
        self.ep_idf = IDF(self.idf_file)
        # select .idf output type
        self.ep_idf.outputtype = "standard"

        # constants
        self.FMU_control_dual_stp_name = "FMU_T_dual_stp"
        self.FMU_control_cooling_stp_name = "FMU_T_cooling_stp"
        self.FMU_control_heating_stp_name = "FMU_T_heating_stp"
        self.FMU_control_type_name = "FMU_T_control_type"

    @property
    def idf_prep_name(self):
        return self.idf_name.replace(".idf", "_prep.idf")

    @property
    def idf_prep_dir(self):
        return os.path.join(self.idf_dir, "preprocessed")

    @property
    def idf_prep_path(self):
        return os.path.join(self.idf_prep_dir, self.idf_prep_name)

    def preprocess(
        self,
        init_temperature=21.0,
        preprocess_check=False,
    ):
        """add control signals to IDF before making FMU"""

        # check if preprocess idf already exists
        if preprocess_check and self.check_valid_idf(
            self.idf_prep_path, target_version=self.ep_version
        ):
            self.ep_idf = IDF(self.idf_prep_path)
            self.get_zone_info()
            # this sets fmu output keys
            # TODO: generalize so doesnt wrap editing .idf
            self.prep_ext_int_output()
            logger.info(
                f"Found correct preprocessed IDF: {self.idf_prep_path}"
            )
            logger.info(f"IDF version: {self.ep_version}")
        else:
            logger.info(f"Making new preprocessed IDF: {self.idf_prep_path}")
            self.prep_ep_version(self.ep_version)
            self.get_zone_info()
            self.prep_simulation_control()
            self.prep_timesteps(self.timesteps_per_hour)
            self.prep_runtime()
            self.prep_ext_int()

            # set the intial temperature via the initial setpoint which will be tracked
            # in the warmup simulation
            self.prep_onoff_setpt_control(
                FMU_control_type_init=self.init_control_type,
                FMU_control_heating_stp_init=self.init_temperature,
                FMU_control_cooling_stp_init=self.init_temperature,
            )
            # create per zone outputs depending on HVAC system type
            self.prep_ext_int_output()

            # finally before saving expand objects
            self.prep_expand_objects()
            self.ep_idf.saveas(self.idf_prep_path)

            # fix version line
            fix_idf_version_line(self.idf_prep_path, self.ep_version)

        return self.idf_prep_path

    def get_zone_info(self):
        self.zone_lists = self.get_zone_lists()
        # TODO: check that zone geometry exists

        self.get_condtioned_zones()
        self.get_occupied_zones()
        self.get_tstat_zone()

    def get_zone_lists(self):
        zone_lists = {}
        for obj in self.ep_idf.idfobjects["ZoneList"]:
            zone_lists[obj.Name] = [
                obj[f"Zone_{i}_Name"]
                for i in range(1, 500)
                if obj[f"Zone_{i}_Name"] != ""
            ]

        return zone_lists

    def zone_list_lookup(self, zone_name):
        for k, v in self.zone_lists.items():
            if zone_name in v:
                return k

    def expand_zones(self, zone_list):
        if zone_list in self.zone_lists.keys():
            return self.zone_lists[zone_list]
        else:
            return zone_list

    def get_tstat_zone(self):
        tstats = self.ep_idf.idfobjects["zonecontrol:thermostat"]
        if len(tstats) > 1:
            raise ValueError(
                f"Multiple thermostats in IDF file: {self.idf_file}"
            )

        self.thermostat_zone = fmu_variable_name_conversion(
            tstats[0].Zone_or_ZoneList_Name
        )

    def get_condtioned_zones(self):
        """get list of all zones that are condtioned
        conditioned zones are defined in IDF by:
        1. ZoneHVAC:EquipmentConnections
        2. ZoneVentilation:DesignFlowRate
        3. sizing:Zone
        """
        equip_conn_zones = [
            self.expand_zones(obj.Zone_Name)
            for obj in self.ep_idf.idfobjects["ZoneHVAC:EquipmentConnections"]
        ]

        vent_design_zones = [
            self.expand_zones(obj.Zone_or_ZoneList_Name)
            for obj in self.ep_idf.idfobjects["ZoneVentilation:DesignFlowRate"]
        ]

        sizing_zones = [
            self.expand_zones(obj.Zone_or_ZoneList_Name)
            for obj in self.ep_idf.idfobjects["sizing:Zone"]
        ]

        self.conditioned_zones = list(
            set(equip_conn_zones) | set(vent_design_zones) | set(sizing_zones)
        )

    def get_occupied_zones(self):
        """get list of all zones that are condtioned
        conditioned zones are defined in IDF by:
        1. people
        """
        self.occupied_zones = [
            self.expand_zones(obj.Zone_or_ZoneList_Name)
            for obj in self.ep_idf.idfobjects["people"]
        ]

        if any([z not in self.conditioned_zones for z in self.occupied_zones]):
            logger.error(
                f"IDF file: {self.idf_file} contains occupied zones that"
                " do not appear to be conditioned."
            )

    def prep_runtime(self):
        """
        Set runtime one full year without repeating.
        """
        self.popallidfobjects("RUNPERIOD")
        # if self.ep_version == "8-9-0":
        self.ep_idf.newidfobject(
            "RUNPERIOD",
            Name="FULLYEAR",
            Begin_Month=1,
            Begin_Day_of_Month=2,
            End_Month=12,
            End_Day_of_Month=31,
        )

    def prep_simulation_control(self):
        """
        See V8-9-0-Energy+.idd:
        and Input Reference
        """
        self.popallidfobjects("SimulationControl")
        self.ep_idf.newidfobject(
            "SimulationControl",
            Do_Zone_Sizing_Calculation="Yes",
            Do_System_Sizing_Calculation="Yes",
            Do_Plant_Sizing_Calculation="No",
            Run_Simulation_for_Sizing_Periods="Yes",
            Run_Simulation_for_Weather_File_Run_Periods="Yes",
            Do_HVAC_Sizing_Simulation_for_Sizing_Periods="No",
            Maximum_Number_of_HVAC_Sizing_Simulation_Passes=1,
        )

    def prep_timesteps(self, timesteps_per_hour):
        """
        See V8-9-0-Energy+.idd:
        """
        self.ep_idf.idfobjects["TIMESTEP"][
            0
        ].Number_of_Timesteps_per_Hour = timesteps_per_hour

    def prep_ep_version(self, target_version):
        """
        Checks if curent ep idf version is same as target version.
        If not equal upgrades to target version (or downgrades?)
        """
        conversion_dict = {
            "8-0-0": "Transition-V8-0-0-to-V8-1-0",
            "8-1-0": "Transition-V8-1-0-to-V8-2-0",
            "8-2-0": "Transition-V8-2-0-to-V8-3-0",
            "8-3-0": "Transition-V8-3-0-to-V8-4-0",
            "8-4-0": "Transition-V8-4-0-to-V8-5-0",
            "8-5-0": "Transition-V8-5-0-to-V8-6-0",
            "8-6-0": "Transition-V8-6-0-to-V8-7-0",
            "8-7-0": "Transition-V8-7-0-to-V8-8-0",
            "8-8-0": "Transition-V8-8-0-to-V8-9-0",
            "8-9-0": "Transition-V8-9-0-to-V9-0-0",
            "9-0-0": "Transition-V9-0-0-to-V9-1-0",
            "9-1-0": "Transition-V9-1-0-to-V9-2-0",
            "9-2-0": "Transition-V9-2-0-to-V9-3-0",
        }

        cur_version = self.get_idf_version(self.ep_idf)

        # check if current version above target
        if int(cur_version.replace("-", "")) > int(
            target_version.replace("-", "")
        ):
            logger.error(
                f".idf current_version={cur_version} above target_version={target_version}"
            )
        elif cur_version == target_version:
            logger.info(
                f"Correct .idf version {cur_version}. Using {self.idf_file}"
            )
        else:
            # first check for previous upgrade
            transition_fpath = self.idf_file.replace(
                ".idf", f"_{target_version}.idf"
            )
            if not os.path.isfile(transition_fpath):
                # upgrade .idf file repeatedly
                first_transition = True
                for i in range(len(conversion_dict)):
                    if cur_version != target_version:
                        transition_dir = os.path.join(
                            os.environ["EPLUS_DIR"],
                            "PreProcess/IDFVersionUpdater",
                        )
                        transistion_path = os.path.join(
                            transition_dir, conversion_dict[cur_version]
                        )
                        logger.info(
                            f"Upgrading idf file. cur_version={cur_version}, target_version={target_version}, transistion_path={transistion_path}"
                        )

                        # must use os.chdir() because a subprocess cannot change another subprocess's wd
                        # see https://stackoverflow.com/questions/21406887/subprocess-changing-directory/21406995
                        original_wd = os.getcwd()
                        os.chdir(transition_dir)
                        cmd = f"{transistion_path} {self.idf_file}"

                        # make transition call
                        subprocess.call(
                            shlex.split(cmd), stdout=subprocess.PIPE
                        )
                        os.chdir(original_wd)

                        cur_version = conversion_dict[cur_version][-5:]
                        if self.debug:
                            shutil.move(
                                self.idf_file + "new",
                                self.idf_file.replace(
                                    ".idf", f"_{cur_version}.idf"
                                ),
                            )

                        if first_transition:
                            shutil.move(
                                self.idf_file + "old",
                                self.idf_file + "original",
                            )
                            first_transition = False

                shutil.move(self.idf_file + "original", self.idf_file)

                if not self.debug:
                    shutil.move(
                        self.idf_file + "new",
                        self.idf_file.replace(".idf", f"_{cur_version}.idf"),
                    )
                if os.path.isfile(self.idf_file + "old"):
                    os.remove(self.idf_file + "old")
            self.idf_file = transition_fpath
            # after running transition need to reload .idf file
            self.ep_idf = IDF(self.idf_file)
            logger.info(f"Upgrading complete. Using: {self.idf_file}")

    def prep_expand_objects(self):
        # must use os.chdir() because a subprocess cannot change another subprocess's wd
        # see https://stackoverflow.com/questions/21406887/subprocess-changing-directory/21406995
        logger.info(f"Expanding objects. Using: {self.idf_file}")
        original_wd = os.getcwd()
        exp_dir = os.path.join(os.environ["EPLUS_DIR"])
        os.chdir(exp_dir)
        exp_path = os.path.join(exp_dir, "ExpandObjects")
        cmd = f"{exp_path} {self.idf_file}"

        # make transition call
        subprocess.call(shlex.split(cmd), stdout=subprocess.PIPE)
        os.chdir(original_wd)

    def prep_onoff_setpt_control(
        self,
        FMU_control_type_init,
        FMU_control_heating_stp_init,
        FMU_control_cooling_stp_init,
    ):
        """
        add external interface
        add external interface schedules for heatng and cooling setpoints
        add external interface schedule for HVAC control mode
        add HVAC setpoint schedule linked to external setpoint variable

        """
        # FMU_stp_control_schedule_name = "FMU_stp_control_schedule"
        control_schedule_type_name = "CONST_control_type_schedule"
        heating_stp_name = "CONST_heating_stp"
        cooling_stp_name = "CONST_cooling_stp"
        dual_stp_name = "CONST_heating_cooling_stp"
        cooling_stp_schedule_name = "CONST_cooling_stp_schedule"
        heating_stp_schedule_name = "CONST_heating_stp_schedule"
        dual_stp_schedule_name = "CONST_heating_stp_schedule"

        # create a temperature schedule limits
        self.popifdobject_by_name("ScheduleTypeLimits", "temperature")
        self.ep_idf.newidfobject(
            "ScheduleTypeLimits",
            Name="Temperature",
            Lower_Limit_Value=-100.0,
            Upper_Limit_Value=200.0,
            Numeric_Type="CONTINUOUS",
            Unit_Type="Temperature",
        )

        # remove all existing external schedule variables
        self.popallidfobjects(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule"
        )

        # create FMU heating setpoint schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule",
            Schedule_Name=heating_stp_schedule_name,
            Schedule_Type_Limits_Names="Temperature",
            FMU_Variable_Name=self.FMU_control_heating_stp_name,
            Initial_Value=FMU_control_heating_stp_init,
        )

        # create FMU cooling setpoint schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule",
            Schedule_Name=cooling_stp_schedule_name,
            Schedule_Type_Limits_Names="Temperature",
            FMU_Variable_Name=self.FMU_control_cooling_stp_name,
            Initial_Value=FMU_control_cooling_stp_init,
        )
        # create a control type schedule limits. See `ControllerModels.EPLUS_THERMOSTAT_MODES`
        if not [
            s_obj
            for s_obj in self.ep_idf.idfobjects["ScheduleTypeLimits"]
            if "Control Type" in s_obj.Name
        ]:
            self.ep_idf.newidfobject(
                "ScheduleTypeLimits",
                Name="Control Type",
                Lower_Limit_Value=0.0,
                Upper_Limit_Value=4.0,
                Numeric_Type="DISCRETE",
            )
        # create thermostat control type schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule",
            Schedule_Name=control_schedule_type_name,
            Schedule_Type_Limits_Names="Control Type",
            FMU_Variable_Name=self.FMU_control_type_name,
            Initial_Value=FMU_control_type_init,
        )

        # over write ZoneControl:Thermostat control objects
        for tstat in self.ep_idf.idfobjects["zonecontrol:thermostat"]:

            tstat.Control_Type_Schedule_Name = control_schedule_type_name
            tstat.Control_1_Object_Type = "ThermostatSetpoint:SingleHeating"
            tstat.Control_1_Name = heating_stp_name
            # tstat.Control_1_Object_Type = "ThermostatSetpoint:DualSetpoint"
            # tstat.Control_1_Name = dual_stp_name
            tstat.Control_2_Object_Type = "ThermostatSetpoint:SingleCooling"
            tstat.Control_2_Name = cooling_stp_name

        # create new thermostat setpoint for heating
        self.popallidfobjects("ThermostatSetpoint:SingleHeating")
        self.ep_idf.newidfobject(
            "ThermostatSetpoint:SingleHeating",
            Name=heating_stp_name,
            Setpoint_Temperature_Schedule_Name=heating_stp_schedule_name,
        )

        # create new thermostat setpoint for cooling
        self.popallidfobjects("ThermostatSetpoint:Singlecooling")
        self.ep_idf.newidfobject(
            "ThermostatSetpoint:SingleCooling",
            Name=cooling_stp_name,
            Setpoint_Temperature_Schedule_Name=cooling_stp_schedule_name,
        )

        # TODO: make equipment always available

    def prep_ext_int(self):
        """
        create external interface.
        """
        self.popallidfobjects("EXTERNALINTERFACE")
        self.ep_idf.newidfobject(
            "EXTERNALINTERFACE",
            Name_of_External_Interface="FunctionalMockupUnitExport",
        )

    def get_heating_equipment(self):
        """
        return E+ groups of heating equipment
        """
        ep_idf_keys = list(self.ep_idf.idfobjects.keys())
        # check for air loop
        air_loop_group = "AirLoopHVAC"
        if air_loop_group in ep_idf_keys:
            for g in self.ep_idf.idfobjects[air_loop_group]:
                amln = g.Availability_Manager_List_Name
        pass

    def get_heating_sched(self):
        """
        get heating system groups schedules that need to be linked with FMU control
        schedule
        """
        ep_idf_keys = list(self.ep_idf.idfobjects.keys())
        # check for air loop
        air_loop_group = "AirLoopHVAC"
        if air_loop_group in ep_idf_keys:
            for g in self.ep_idf.idfobjects[air_loop_group]:
                amln = g.Availability_Manager_List_Name
        pass

    def prep_ext_int_output(self):
        """
        add external interface output variables
        Note: FMU input variables cannot be read directly and must be read through an
        OUTPUT:VARIABLE set in the .idf file.
        """
        # no need for meter file
        self.popallidfobjects("Output:Meter:MeterFileOnly")
        self.popallidfobjects("Output:Table:Monthly")
        self.popallidfobjects("OutputControl:Table:Style")
        self.popallidfobjects("Output:Table:SummaryReports")
        self.popallidfobjects("Output:Constructions")

        # remove all existing output variables
        self.popallidfobjects("Output:variable")
        self.popallidfobjects(
            "EXTERNALINTERFACE:FUNCTIONALMOCKUPUNITEXPORT:FROM:VARIABLE"
        )

        # add building_outputs as flattened dict of variable meta data
        for ek, ev in self.building_output_spec.items():
            for ok, ov in ev.items():
                if ok != "eplus_name":
                    # set name of variable in FMU and internally
                    var_k = "FMU_{}_{}".format(
                        fmu_variable_name_conversion(ev["eplus_name"]),
                        fmu_variable_name_conversion(ov["eplus_name"]),
                    )

                    # add fmi name as key to output spec
                    self.output_spec[var_k] = ov

                    self.ep_idf.newidfobject(
                        "Output:variable",
                        Key_Value=ev["eplus_name"],
                        Variable_Name=ov["eplus_name"],
                        Reporting_Frequency="timestep",
                    )
                    self.ep_idf.newidfobject(
                        "ExternalInterface:FunctionalMockupUnitExport:From:Variable",
                        OutputVariable_Index_Key_Name=ev["eplus_name"],
                        OutputVariable_Name=ov["eplus_name"],
                        FMU_Variable_Name=var_k,
                    )

        # add zone_outputs
        # output IDF obj is broken out because the * key value can be used to select
        # all zones and is standard in E+ .idf files
        for z in self.conditioned_zones:
            for ok, ov in self.zone_output_spec.items():

                zk = fmu_variable_name_conversion(z)
                var_k = zk + "_" + ok

                # add fmi name as key to output spec
                self.output_spec[var_k] = ov

                self.ep_idf.newidfobject(
                    "Output:variable",
                    Key_Value=z,
                    Variable_Name=ov["eplus_name"],
                    Reporting_Frequency="Timestep",
                )

                self.ep_idf.newidfobject(
                    "ExternalInterface:FunctionalMockupUnitExport:From:Variable",
                    OutputVariable_Index_Key_Name=z,
                    OutputVariable_Name=ov["eplus_name"],
                    FMU_Variable_Name=var_k,
                )

    """
    TODO: Changes to eppy:
     - parse .idf comments differently or remove them to reduce file sizes
     - correctly show parameters of idfobject as .keys()
     - add expand objects feature
     - better object manipulation (e.g. self.popallidfobjects)
    """

    # functions for eppy PR
    def popallidfobjects(self, idf_obj_name):
        """
        pops all idf objects of any key name if object exists.
        extension of IDF.popidfobjects
        """
        if idf_obj_name in self.ep_idf.idfobjects:
            for i in range(len(self.ep_idf.idfobjects[idf_obj_name])):
                self.ep_idf.popidfobject(idf_obj_name, 0)

    def popifdobject_by_name(self, idf_objs, name):
        """"""
        for i, s_obj in enumerate(
            self.ep_idf.idfobjects["ScheduleTypeLimits"]
        ):
            if "temperature" in s_obj.Name.lower():
                self.ep_idf.popidfobject("ScheduleTypeLimits", i)

    def get_idf_version(self, ep_model):
        """Get model in standard format: x-x-x"""
        version = ep_model.idfobjects["version"].list2[0][1].replace(".", "-")
        if len(version) <= 3:
            # if only first two simver digits in .idf add a zero
            version += "-0"
        return version

    def check_valid_idf(self, idf_path, target_version=None):
        """"""
        is_valid = False
        if os.path.isfile(idf_path):
            # any text file can be read by eppy and produce a garbage model
            if IDF.getiddname() == None:
                IDF.setiddname(self.idd_path)

            ep_model = IDF(idf_path)
            # check version to see if valid .idf, eppy returns empty list if obj not found
            version = self.get_idf_version(ep_model)
            if target_version and (version == target_version):
                is_valid = True
            elif not target_version and version:
                is_valid = True

        return is_valid


# Private-ish methods
def fmu_variable_name_conversion(eplus_name):
    return eplus_name.replace(" ", "_").replace("-", "_")


def fix_idf_version_line(idf_path, ep_version):
    """
    Fix format of Version Identifier line in IDF file for EnergyPlusToFMU
    https://github.com/lbl-srg/EnergyPlusToFMU/issues/30#issuecomment-621353009
    """

    with open(idf_path, "r") as input:
        with open(idf_path + ".patch", "w") as output:
            for line in input:

                if line == "Version,\n":
                    output.write(
                        line.replace(
                            "\n", "{};\n".format(ep_version.replace("-", "."))
                        )
                    )
                elif "!- Version Identifier" not in line:
                    output.write(line)

    shutil.move(idf_path + ".patch", idf_path)
