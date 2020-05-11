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


@attr.s(kw_only=True)
class IDFPreprocessor(object):
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs.
    Example:
    ```python
    from BuildingControlSimulator.BuildingModels import IDFPreprocessor
    idf = IDFPreprocessor(
        idf_file=self.dummy_idf_file,
        weather_file=self.dummy_weather_file,
    )
    ```
    """

    # user must supply an idf file as either 1) full path, or 2) a file in self.idf_dir
    idf_file = attr.ib()

    init_temperature = attr.ib(type=float, default=21.0)
    init_control_type = attr.ib(type=int, default=2)
    debug = attr.ib(type=bool, default=False)
    timesteps = attr.ib(type=int, default=12)
    fmi_version = attr.ib(type=float, default=1.0)

    # first, terminate env vars, these will raise exceptions if undefined
    ep_version = attr.ib(default=os.environ["ENERGYPLUS_INSTALL_VERSION"])
    idf_dir = attr.ib(default=os.environ["IDF_DIR"])
    idd_path = attr.ib(default=os.environ["EPLUS_IDD"])
    # weather_dir = attr.ib(default=os.environ["WEATHER_DIR"])
    fmu_dir = attr.ib(default=os.environ["FMU_DIR"])
    eplustofmu_path = attr.ib(
        default=os.path.join(
            os.environ["EXT_DIR"], "EnergyPlusToFMU/Scripts/EnergyPlusToFMU.py"
        )
    )

    def __attrs_post_init__(self):
        """Initialize `IDFPreprocessor` with an IDF file and desired actions"""
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

        logger.info("IDFPreprocessor loading .idf file: {}".format(self.idf_file))
        self.ep_idf = IDF(self.idf_file)

        self.zone_outputs = []
        self.building_outputs = []

        # config
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

    @property
    def fmu_name(self):
        fmu_name = os.path.splitext(self.idf_prep_name)[0]
        # add automatic conversion rules for fmu naming
        idf_bad_chars = [" ", "-", "+", "."]
        for c in idf_bad_chars:
            fmu_name = fmu_name.replace(c, "_")

        if fmu_name[0].isdigit():
            fmu_name = "f_" + fmu_name

        fmu_name = fmu_name + ".fmu"

        return fmu_name

    @property
    def fmu_path(self):
        return os.path.join(self.fmu_dir, self.fmu_name)

    def output_keys(self):
        """
        """
        return self.building_outputs + self.zone_outputs

    def preprocess(
        self,
        init_control_type=1,
        init_temperature=21.0,
        timesteps_per_hour=60,
        preprocess_check=False,
    ):
        """add control signals to IDF before making FMU"""

        # check if preprocess idf already exists
        if preprocess_check and self.check_valid_idf(
            self.idf_prep_path, target_version=self.ep_version
        ):
            logger.info(f"Found correct preprocessed IDF: {self.idf_prep_path}")
            logger.info(f"IDF version: {self.ep_version}")
        else:
            logger.info(f"Making new preprocessed IDF: {self.idf_prep_path}")
            self.prep_ep_version(self.ep_version)
            self.prep_expand_objects()
            self.prep_timesteps(timesteps_per_hour)
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

            # Output:Variable,*,Facility Total HVAC Electric Demand Power,hourly; !- HVAC Average [W]
            zone_outputs = [
                "Zone Air Temperature",
                "Zone Thermostat Heating Setpoint Temperature",
                "Zone Thermostat Cooling Setpoint Temperature",
                "Zone Air System Sensible Heating Rate",
                "Zone Air System Sensible Cooling Rate",
                "Zone Total Internal Total Heating Rate",
                # "Zone Total Internal Latent Gain Rate",
                # "Zone Total Internal Convective Heating Rate",
                # "Zone Total Internal Radiant Heating Rate",
                # "Zone Total Internal Visible Radiation Heating Rate"
                # "Air System Electric Energy"
                # "Air System Gas Energy"
                # "Air System Fan Electric Energy"
                # "Air System Cooling Coil Chilled Water Energy"
                # "Air System Heating Coil Hot Water Energy"
                # "Air System DX Cooling Coil Electric Energy"
                # "Air System Heating Coil Gas Energy"
            ]
            building_outputs = {
                "Environment": [
                    "Site Outdoor Air Relative Humidity",
                    "Site Outdoor Air Drybulb Temperature",
                    # "Site Diffuse Solar Radiation Rate per Area",
                    # "Site Direct Solar Radiation Rate per Area"
                ],
                #  "Main Chiller": [
                #      "Chiller Electric Power",
                # ]
            }

            self.prep_ext_int_output(
                zone_outputs=zone_outputs, building_outputs=building_outputs
            )

            self.ep_idf.saveas(self.idf_prep_path)

        return self.idf_prep_path

    def make_fmu(self, weather):
        """make the fmu"""

        cmd = f"python2.7 {self.eplustofmu_path} -i {self.idd_path} -w {weather} -a {self.fmi_version} -d {self.idf_prep_path}"

        proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE)
        if not proc.stdout:
            raise ValueError(f"Empty STDOUT. Invalid EnergyPlusToFMU cmd={cmd}")

        # EnergyPlusToFMU puts fmu in cwd always, move out of cwd
        shutil.move(
            os.path.join(
                os.getcwd(),
                self.fmu_name.replace(
                    self.ep_version, self.ep_version.replace("-", "_")
                ),
            ),
            self.fmu_path,
        )
        # check FMI compliance
        # -h specifies the step size in seconds, -s is the stop time in seconds.
        # Stop time must be a multiple of 86400.
        # The step size needs to be the same as the .idf file specifies

        cmd = f'yes | {os.environ["EXT_DIR"]}/FMUComplianceChecker/fmuCheck.linux64 -h {self.timesteps} -s 172800 {self.fmu_path}'.split()
        # subprocess.run(cmd.split(), stdout=subprocess.PIPE)
        # if not proc.stdout:
        #     raise ValueError(f"Empty STDOUT. Invalid EnergyPlusToFMU cmd={cmd}")
        return self.fmu_path

    def prep_runtime(self):
        """
        Set runtime one full year without repeating.
        """
        self.popallidfobjects("RUNPERIOD")
        self.ep_idf.newidfobject(
            "RUNPERIOD",
            Name="FULLYEAR",
            Begin_Month=1,
            Begin_Day_of_Month=2,
            End_Month=12,
            End_Day_of_Month=31,
        )

    def prep_timesteps(self, timesteps_per_hour):
        """
        Changes time steps per hour to vale passed.
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
            "8-9-0": "Transition-V8-9-0-to-V9-0-1",
            "9-0-1": "Transition-V9-0-1-to-V9-1-0",
            "9-1-0": "Transition-V9-1-0-to-V9-2-0",
        }

        cur_version = self.get_idf_version(self.ep_idf)

        # check if current version above target
        if int(cur_version.replace("-", "")) > int(target_version.replace("-", "")):
            logger.error(
                f".idf current_version={cur_version} above target_version={target_version}"
            )
        elif cur_version == target_version:
            logger.info(f"Correct .idf version {cur_version}. Using {self.idf_file}")
        else:
            # first check for previous upgrade
            transition_fpath = self.idf_file.replace(".idf", f"_{target_version}.idf")
            if not os.path.isfile(transition_fpath):
                # upgrade .idf file repeatedly
                first_transition = True
                for i in range(len(conversion_dict)):
                    if cur_version != target_version:
                        transition_dir = os.path.join(
                            os.environ["EPLUS_DIR"], "PreProcess/IDFVersionUpdater"
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
                        subprocess.call(shlex.split(cmd), stdout=subprocess.PIPE)
                        os.chdir(original_wd)

                        cur_version = conversion_dict[cur_version][-5:]
                        if self.debug:
                            shutil.move(
                                self.idf_file + "new",
                                self.idf_file.replace(".idf", f"_{cur_version}.idf"),
                            )

                        if first_transition:
                            shutil.move(
                                self.idf_file + "old", self.idf_file + "original"
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

        # for i, s_obj in enumerate(self.ep_idf.idfobjects['ScheduleTypeLimits']):
        #     if "temperature" in s_obj.Name.lower():
        #         self.editted_temperature_schedule = True
        #         s_obj.Lower_Limit_Value = -100.0
        #         s_obj.Upper_Limit_Value = 200.0

        # if not self.editted_temperature_schedule:
        #     self.ep_idf.newidfobject(
        #         'ScheduleTypeLimits',
        #         Name="Temperature",
        #         Lower_Limit_Value=-100.0,
        #         Upper_Limit_Value=200.0,
        #         Numeric_Type="CONTINUOUS",
        #         Unit_Type="Temperature"
        #     )

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
        # create a control type schedule limits
        # 0 - Uncontrolled (No specification or default)
        # 1 - Single Heating Setpoint
        # 2 - Single Cooling SetPoint
        # 3 - Single Heating Cooling Setpoint
        # 4 - Dual Setpoint with Deadband (Heating and Cooling)
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

        # self.popallidfobjects("ThermostatSetpoint:SingleCooling")
        # # create new thermostat setpoint for heating
        # self.ep_idf.newidfobject(
        #     "ThermostatSetpoint:DualSetpoint",
        #     Name=cooling_stp_name,
        #     Setpoint_Temperature_Schedule_Name=cooling_stp_schedule_name
        # )

        # TODO: make equipment always available

    def prep_ext_int(self):
        """
        create external interface.
        """
        self.ep_idf.newidfobject(
            "EXTERNALINTERFACE", Name_of_External_Interface="FunctionalMockupUnitExport"
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

    def prep_ext_int_output(self, zone_outputs=[], building_outputs={}):
        """
        add external interface output variables
        Note: FMU input variables cannot be read directly and must be read through an
        OUTPUT:VARIABLE set in the .idf file.
        example input:
            zone_outputs = [
                "Zone Air Temperature",
                "Zone Thermostat Heating Setpoint Temperature",
                "Zone Air System Sensible Heating Rate"
            ]
            building_outputs = {
                "Environment": [
                    "Site Outdoor Air Drybulb Temperature",
                    "Site Outdoor Air Relative Humidity",
                    "Site Diffuse Solar Radiation Rate per Area",
                    "Site Direct Solar Radiation Rate per Area"
                ]
            }
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
        # add building_outputs

        for e in building_outputs.keys():
            for o in building_outputs[e]:
                nzo = "FMU_{}_{}".format(
                    e.replace(" ", "_").replace("-", "_"),
                    o.replace(" ", "_").replace("-", "_"),
                )

                self.ep_idf.newidfobject(
                    "Output:variable",
                    Key_Value=e,
                    Variable_Name=o,
                    Reporting_Frequency="timestep",
                )
                self.ep_idf.newidfobject(
                    "ExternalInterface:FunctionalMockupUnitExport:From:Variable",
                    OutputVariable_Index_Key_Name=e,
                    OutputVariable_Name=o,
                    FMU_Variable_Name=nzo,
                )
                self.building_outputs.append(nzo)

        # add zone_outputs
        # output IDF obj is broken out because the * key value can be used to select
        # all zones and is standard in E+ .idf files
        for o in zone_outputs:
            self.ep_idf.newidfobject(
                "Output:variable",
                Key_Value="*",
                Variable_Name=o,
                Reporting_Frequency="Timestep",
            )

        for z in self.ep_idf.idfobjects["Zone"]:
            for o in zone_outputs:

                zo = "FMU_{}_{}".format(
                    z.Name.replace(" ", "_").replace("-", "_"),
                    o.replace(" ", "_").replace("-", "_"),
                )
                self.ep_idf.newidfobject(
                    "ExternalInterface:FunctionalMockupUnitExport:From:Variable",
                    OutputVariable_Index_Key_Name=z.Name,
                    OutputVariable_Name=o,
                    FMU_Variable_Name=zo,
                )
                self.zone_outputs.append(zo)

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
        """
        """
        for i, s_obj in enumerate(self.ep_idf.idfobjects["ScheduleTypeLimits"]):
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
        """
        """
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
