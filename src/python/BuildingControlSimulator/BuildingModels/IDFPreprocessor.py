# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor

@attr.s
class IDFPreprocessor(object):
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs.

    Example:
    ```python
    src.IDFPreprocessor.()

    ```

    """
    def __init__(self,
        idf_name=None,
        idf_path=None,
        weather_name=None,
        weather_path=None,
        timesteps=12):
        """Initialize `IDFPreprocessor` with an IDF file and desired actions"""
        self.ep_version = os.environ["ENERGYPLUS_INSTALL_VERSION"]
        self.idf_dir = os.environ["IDF_DIR"]
        self.fmu_dir = os.environ["FMU_DIR"]
        self.idd_path = os.environ["EPLUS_IDD"]
        self.weather_dir = os.environ["WEATHER_DIR"]
        self.eplustofmu_path = os.path.join(
            os.environ["EXT_DIR"],
            "EnergyPlusToFMU/Scripts/EnergyPlusToFMU.py"
        )
        self.timesteps = timesteps

        if idf_path:
            # TODO add path checking
            self.idf_path = idf_path
        elif idf_name:
            for r, d, f in os.walk(self.idf_dir):
                for fname in f:
                    if fname == idf_name:
                        self.idf_path = os.path.join(self.idf_dir, idf_name)
        else:
            raise ValueError(f"""Must supply valid IDF file, 
                idf_path={weather_path} and idf_name={weather_name}""")

        if weather_path:
            # TODO add path checking
            self.weather_path = weather_path
        elif weather_name:
            for r, d, f in os.walk(self.weather_dir):
                for fname in f:
                    if fname == weather_name:
                        self.weather_path = os.path.join(self.weather_dir, weather_name)
        else:
            raise ValueError(f"""Must supply valid weather file, 
                weather_path={weather_path} and weather_name={weather_name}""")

        self.idf_name = os.path.basename(self.idf_path)
        idx = self.idf_name.index(".idf")
        self.idf_prep_name = self.idf_name[:idx] + "_prep" + self.idf_name[idx:]
        self.idf_prep_dir = os.path.join(self.idf_dir, "preprocessed")
        self.idf_prep_path = os.path.join(self.idf_prep_dir, self.idf_prep_name)

        self.fmu_name = self.idf_prep_name.replace(".idf", ".fmu").replace("-", "_")
        if self.fmu_name[0].isdigit():
            self.fmu_name = "f_" + self.fmu_name

        self.fmu_path = os.path.join(self.fmu_dir, self.fmu_name)


        modeleditor.IDF.setiddname(self.idd_path)
        print("IDFPreprocessor loading .idf file: {}".format(self.idf_path))
        self.ep_idf = modeleditor.IDF(self.idf_path)

        self.zone_outputs = []
        self.building_outputs = []
        # config
        self.FMU_control_cooling_stp_name = "FMU_T_cooling_stp"
        self.FMU_control_heating_stp_name = "FMU_T_heating_stp"
        self.FMU_control_type_name = "FMU_T_control_type"


    def preprocess(self):
        """add control signals to IDF before making FMU"""

        self.prep_ep_version(self.ep_version.split("-"))
        self.prep_timesteps(self.timesteps)
        self.prep_runtime()
        self.prep_ext_int()
        # set the intial temperature via the initial setpoint which will be tracked 
        # in the warmup simulation
        self.prep_onoff_setpt_control(
            FMU_control_type_name_init=1,
            FMU_control_heating_stp_name_init=21.0,
            FMU_control_cooling_stp_name_init=25.0
        )
        # create per zone outputs depending on HVAC system type
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
        ]
        building_outputs = {
            "Environment": [
                "Site Outdoor Air Relative Humidity",
                "Site Outdoor Air Drybulb Temperature",
                # "Site Diffuse Solar Radiation Rate per Area",
                # "Site Direct Solar Radiation Rate per Area"
            ],
        }

        self.prep_ext_int_output(
            zone_outputs=zone_outputs,
            building_outputs=building_outputs)

        self.ep_idf.saveas(self.idf_prep_path)

        return self.idf_prep_path


    def make_fmu(self):
        """make the fmu"""

        cmd = f'python2.7 {self.eplustofmu_path} -i {self.idd_path} -w {self.weather_path} -d {self.idf_prep_path}'
        
        proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE)
        if not proc.stdout:
            raise ValueError(f"Empty STDOUT. Invalid EnergyPlusToFMU cmd={cmd}")


        # EnergyPlusToFMU puts fmu in cwd always, move out of cwd
        shutil.move(
            os.path.join(os.getcwd(), self.fmu_name.replace(
                self.ep_version, self.ep_version.replace("-", "_"))
            ),
            self.fmu_path
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
        '''
        Set runtime one full year without repeating.
        '''
        self.popallidfobjects('RUNPERIOD'.upper())
        self.ep_idf.newidfobject(
            'RUNPERIOD',
            Name="FULLYEAR",
            Begin_Month=1,
            Begin_Day_of_Month=2,
            End_Month=12,
            End_Day_of_Month=31
        )

    def prep_timesteps(self, timesteps_per_hour):
        '''
        Changes time steps per hour to vale passed.
        '''
        self.ep_idf.idfobjects[
            'TIMESTEP'.upper()][0].Number_of_Timesteps_per_Hour = timesteps_per_hour

    def prep_ep_version(self, target_version):
        '''
        Checks if curent ep idf version is same as target version.
        If not equal upgrades to target version (or downgrades?)
        '''
        cur_version = self.ep_idf.idfobjects['version'.upper()].list2[0][1].split(".")
        if len(cur_version) < 3:
            cur_version.append('0')
        if cur_version != target_version:
            print(f"WARNING: idf file cur_version={cur_version}, target_version={target_version}")
            # TODO make transition shell script
            # subprocess.call(
            #     shlex.split('{} {} {}'.format(
            #         os.path.join(os.environ["BASH_DIR"], prep_transition.sh),
            #         cur_version,
            #         target_version)
            #     )
            # )

    def prep_onoff_setpt_control(self,
            FMU_control_type_name_init,
            FMU_control_heating_stp_name_init,
            FMU_control_cooling_stp_name_init):
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
        cooling_stp_schedule_name = "CONST_cooling_stp_schedule"
        heating_stp_schedule_name = "CONST_heating_stp_schedule"

        # create a temperature schedule limits
        self.popifdobject_by_name("ScheduleTypeLimits", "temperature")
        self.ep_idf.newidfobject(
            'ScheduleTypeLimits'.upper(),
            Name="Temperature",
            Lower_Limit_Value=-100.0,
            Upper_Limit_Value=200.0,
            Numeric_Type="CONTINUOUS",
            Unit_Type="Temperature"
        )

        # for i, s_obj in enumerate(self.ep_idf.idfobjects['ScheduleTypeLimits'.upper()]): 
        #     if "temperature" in s_obj.Name.lower():
        #         self.editted_temperature_schedule = True
        #         s_obj.Lower_Limit_Value = -100.0
        #         s_obj.Upper_Limit_Value = 200.0

        # if not self.editted_temperature_schedule:
        #     self.ep_idf.newidfobject(
        #         'ScheduleTypeLimits'.upper(),
        #         Name="Temperature",
        #         Lower_Limit_Value=-100.0,
        #         Upper_Limit_Value=200.0,
        #         Numeric_Type="CONTINUOUS",
        #         Unit_Type="Temperature"
        #     )

        # create FMU heating setpoint schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
            Schedule_Name=heating_stp_schedule_name,
            Schedule_Type_Limits_Names="Temperature",
            FMU_Variable_Name=self.FMU_control_heating_stp_name,
            Initial_Value=FMU_control_heating_stp_name_init
        )

        # create FMU cooling setpoint schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
            Schedule_Name=cooling_stp_schedule_name,
            Schedule_Type_Limits_Names="Temperature",
            FMU_Variable_Name=self.FMU_control_cooling_stp_name,
            Initial_Value=FMU_control_cooling_stp_name_init
        )
        # create a control type schedule limits
        # 0 - Uncontrolled (No specification or default)
        # 1 - Single Heating Setpoint
        # 2 - Single Cooling SetPoint
        # 3 - Single Heating Cooling Setpoint
        # 4 - Dual Setpoint with Deadband (Heating and Cooling)
        if not [s_obj for s_obj in self.ep_idf.idfobjects['ScheduleTypeLimits'.upper()] 
                if "Control Type" in s_obj.Name]:
            self.ep_idf.newidfobject(
                'ScheduleTypeLimits'.upper(),
                Name="Control Type",
                Lower_Limit_Value=0.0,
                Upper_Limit_Value=4.0,
                Numeric_Type="DISCRETE"
            )
        # create thermostat control type schedule variable
        self.ep_idf.newidfobject(
            "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
            Schedule_Name=control_schedule_type_name,
            Schedule_Type_Limits_Names="Control Type",
            FMU_Variable_Name=self.FMU_control_type_name,
            Initial_Value=FMU_control_type_name_init
        )
        
        # over write ZoneControl:Thermostat control objects
        for tstat in self.ep_idf.idfobjects['zonecontrol:thermostat'.upper()]:

            tstat.Control_Type_Schedule_Name = control_schedule_type_name
            tstat.Control_1_Object_Type = "ThermostatSetpoint:SingleHeating"
            tstat.Control_1_Name = heating_stp_name
            tstat.Control_2_Object_Type = "ThermostatSetpoint:SingleCooling"
            tstat.Control_2_Name = cooling_stp_name

        self.popallidfobjects("ThermostatSetpoint:SingleHeating")
        # create new thermostat setpoint for cooling
        self.ep_idf.newidfobject(
            "ThermostatSetpoint:SingleHeating".upper(),
            Name=heating_stp_name,
            Setpoint_Temperature_Schedule_Name=heating_stp_schedule_name
        )

        self.popallidfobjects("ThermostatSetpoint:SingleCooling")
        # create new thermostat setpoint for heating
        self.ep_idf.newidfobject(
            "ThermostatSetpoint:SingleCooling".upper(),
            Name=cooling_stp_name,
            Setpoint_Temperature_Schedule_Name=cooling_stp_schedule_name
        )

        # TODO: make equipment always available

    def prep_ext_int(self):
        '''
        create external interface.
        '''
        self.ep_idf.newidfobject(
            "EXTERNALINTERFACE",
            Name_of_External_Interface="FunctionalMockupUnitExport"
        )

    def get_heating_equipment(self):
        '''
        return E+ groups of heating equipment
        '''
        ep_idf_keys = list(self.ep_idf.idfobjects.keys())
        # check for air loop
        air_loop_group = "AirLoopHVAC".upper()
        if air_loop_group in ep_idf_keys:
            for g in self.ep_idf.idfobjects[air_loop_group]:
                amln = g.Availability_Manager_List_Name
        pass

    def get_heating_sched(self):
        '''
        get heating system groups schedules that need to be linked with FMU control
        schedule
        '''
        ep_idf_keys = list(self.ep_idf.idfobjects.keys())
        # check for air loop
        air_loop_group = "AirLoopHVAC".upper()
        if air_loop_group in ep_idf_keys:
            for g in self.ep_idf.idfobjects[air_loop_group]:
                amln = g.Availability_Manager_List_Name
        pass

    def prep_ext_int_output(self, zone_outputs=[], building_outputs={}):
        '''
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
        '''
        # overwrite all output variables
        self.popallidfobjects('Output:variable'.upper())
        self.popallidfobjects('Output:Meter:MeterFileOnly'.upper())
        # add building_outputs
        for e in building_outputs.keys():
            for o in building_outputs[e]:
                nzo = "FMU_{}_{}".format(
                    e.replace(" ","_").replace("-", "_"),
                    o.replace(" ", "_").replace("-", "_")
                )
                
                self.ep_idf.newidfobject(
                    'Output:variable'.upper(),
                    Key_Value=e,
                    Variable_Name=o,
                    Reporting_Frequency="timestep"
                )
                self.ep_idf.newidfobject(
                    "ExternalInterface:FunctionalMockupUnitExport:From:Variable".upper(),
                    OutputVariable_Index_Key_Name=e,
                    OutputVariable_Name=o,
                    FMU_Variable_Name=nzo
                )
                self.building_outputs.append(nzo)
        # add zone_outputs
        # output IDF obj is broken out because the * key value can be used to select
        # all zones and is standard in E+ .idf files
        for o in zone_outputs:
            self.ep_idf.newidfobject(
                'Output:variable'.upper(),
                Key_Value="*",
                Variable_Name=o,
                Reporting_Frequency="Timestep"
            )

        for z in self.ep_idf.idfobjects['Zone'.upper()]:
            for o in zone_outputs:

                zo = "FMU_{}_{}".format(
                    z.Name.replace(" ","_").replace("-", "_"),
                    o.replace(" ", "_").replace("-", "_")
                )
                self.ep_idf.newidfobject(
                    "ExternalInterface:FunctionalMockupUnitExport:From:Variable".upper(),
                    OutputVariable_Index_Key_Name=z.Name,
                    OutputVariable_Name=o,
                    FMU_Variable_Name=zo
                )
                self.zone_outputs.append(zo)
    '''
    TODO: Changes to eppy:
     - parse .idf comments differently or remove them
     - correctly show parameters of idfobject as .keys()
     - add expand objects feature
     - better object manipulation (e.g. self.popallidfobjects)
    '''

    # functions for eppy PR
    def popallidfobjects(self, idf_obj_name):
        '''
        pops all idf objects of any key name if object exists.
        extension of eppy.modeleditor.IDF.popidfobjects
        '''        
        if idf_obj_name in self.ep_idf.idfobjects:
            for i in range(len(self.ep_idf.idfobjects[idf_obj_name])):
                self.ep_idf.popidfobject(idf_obj_name, 0)

    def popifdobject_by_name(self, idf_objs, name):
        """
        """
        for i, s_obj in enumerate(self.ep_idf.idfobjects['ScheduleTypeLimits'.upper()]): 
            if "temperature" in s_obj.Name.lower():
                self.ep_idf.popidfobject('ScheduleTypeLimits', i)
