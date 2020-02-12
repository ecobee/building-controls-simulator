#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com
from eppy import modeleditor
import os
import numpy as np
from matplotlib import pyplot as plt
import argparse
import subprocess
import shlex
from code import interact


def prep_runtime(ep_idf):
    '''
    Set runtime one full year without repeating.
    '''
    popallidfobjects(ep_idf, 'RUNPERIOD'.upper())
    ep_idf.newidfobject(
        'RUNPERIOD',
        Name="FULLYEAR",
        Begin_Month=1,
        Begin_Day_of_Month=1,
        End_Month=12,
        End_Day_of_Month=31
    )

def prep_timesteps(ep_idf, timesteps_per_hour):
    '''
    Changes time steps per hour to vale passed.
    '''
    ep_idf.idfobjects[
        'TIMESTEP'.upper()][0].Number_of_Timesteps_per_Hour = timesteps_per_hour

def prep_ep_version(ep_idf, target_version):
    '''
    Checks if curent ep idf version is same as target version.
    If not equal upgrades to target version (or downgrades?)
    '''
    cur_version = ep_idf.idfobjects['version'.upper()].list2[0][1].split(".")
    if len(cur_version) < 3:
        cur_version.append('0')
    cur_version = tuple(cur_version)
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

def prep_onoff_setpt_control(
        ep_idf, 
        FMU_control_type_var_init=1,
        FMU_control_heating_var_init=20.0,
        FMU_control_cooling_var_init=27.0):
    '''
    add external interface
    add external interface schedules for heatng and cooling setpoints
    add external interface schedule for HVAC control mode
    add HVAC setpoint schedule linked to external setpoint variable

    '''
    print("Adding on-off set point control")
    # config
    FMU_control_cooling_var = "FMU_T_cooling_stp"
    FMU_control_heating_var = "FMU_T_heating_stp"
    FMU_control_type_var = "FMU_T_control_type"

    # FMU_stp_control_schedule_name = "FMU_stp_control_schedule"
    control_schedule_type_name = "CONST_control_type_schedule"
    heating_stp_name = "CONST_heating_stp"
    cooling_stp_name = "CONST_cooling_stp"
    cooling_stp_schedule_name = "CONST_cooling_stp_schedule"
    heating_stp_schedule_name = "CONST_heating_stp_schedule"

    # create a temperature schedule limits
    if not [s_obj for s_obj in ep_idf.idfobjects['ScheduleTypeLimits'.upper()] 
            if "Temperature" in s_obj.Name]:
        ep_idf.newidfobject(
            'ScheduleTypeLimits'.upper(),
            Name="Temperature",
            Lower_Limit_Value=-99.0,
            Upper_Limit_Value=200.0,
            Numeric_Type="CONTINUOUS",
            Unit_Type="Temperature"
        )

    # create FMU heating setpoint schedule variable
    ep_idf.newidfobject(
        "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
        Schedule_Name=heating_stp_schedule_name,
        Schedule_Type_Limits_Names="Temperature",
        FMU_Variable_Name=FMU_control_heating_var,
        Initial_Value=FMU_control_heating_var_init
    )

    # create FMU cooling setpoint schedule variable
    ep_idf.newidfobject(
        "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
        Schedule_Name=cooling_stp_schedule_name,
        Schedule_Type_Limits_Names="Temperature",
        FMU_Variable_Name=FMU_control_cooling_var,
        Initial_Value=FMU_control_cooling_var_init
    )
    # create a control type schedule limits
    # 0 - Uncontrolled (No specification or default)
    # 1 - Single Heating Setpoint
    # 2 - Single Cooling SetPoint
    # 3 - Single Heating Cooling Setpoint
    # 4 - Dual Setpoint with Deadband (Heating and Cooling)
    if not [s_obj for s_obj in ep_idf.idfobjects['ScheduleTypeLimits'.upper()] 
            if "Control Type" in s_obj.Name]:
        ep_idf.newidfobject(
            'ScheduleTypeLimits'.upper(),
            Name="Control Type",
            Lower_Limit_Value=0.0,
            Upper_Limit_Value=4.0,
            Numeric_Type="DISCRETE"
        )
    # create thermostat control type schedule variable
    ep_idf.newidfobject(
        "ExternalInterface:FunctionalMockupUnitExport:To:Schedule".upper(),
        Schedule_Name=control_schedule_type_name,
        Schedule_Type_Limits_Names="Control Type",
        FMU_Variable_Name=FMU_control_type_var,
        Initial_Value=FMU_control_type_var_init
    )
    
    # over write ZoneControl:Thermostat control objects
    for tstat in ep_idf.idfobjects['zonecontrol:thermostat'.upper()]:
        tstat.Control_Type_Schedule_Name = control_schedule_type_name
        tstat.Control_1_Object_Type = "ThermostatSetpoint:SingleHeating"
        tstat.Control_1_Name = heating_stp_name
        tstat.Control_2_Object_Type = "ThermostatSetpoint:SingleCooling"
        tstat.Control_2_Name = cooling_stp_name

    # create new thermostat setpoint for cooling
    ep_idf.newidfobject(
        "ThermostatSetpoint:SingleHeating".upper(),
        Name=heating_stp_name,
        Setpoint_Temperature_Schedule_Name=heating_stp_schedule_name
    )

    # create new thermostat setpoint for heating
    ep_idf.newidfobject(
        "ThermostatSetpoint:SingleCooling".upper(),
        Name=cooling_stp_name,
        Setpoint_Temperature_Schedule_Name=cooling_stp_schedule_name
    )

    # TODO: make equipment always available

def prep_ext_int(ep_idf):
    '''
    create external interface.
    '''
    ep_idf.newidfobject(
        "EXTERNALINTERFACE",
        Name_of_External_Interface="FunctionalMockupUnitExport"
    )

def get_heating_equipment(ep_idf):
    '''
    return E+ groups of heating equipment
    '''
    ep_idf_keys = list(ep_idf.idfobjects.keys())
    # check for air loop
    air_loop_group = "AirLoopHVAC".upper()
    if air_loop_group in ep_idf_keys:
        for g in ep_idf.idfobjects[air_loop_group]:
            amln = g.Availability_Manager_List_Name
    pass

def get_heating_sched(ep_idf):
    '''
    get heating system groups schedules that need to be linked with FMU control
    schedule
    '''
    ep_idf_keys = list(ep_idf.idfobjects.keys())
    # check for air loop
    air_loop_group = "AirLoopHVAC".upper()
    if air_loop_group in ep_idf_keys:
        for g in ep_idf.idfobjects[air_loop_group]:
            amln = g.Availability_Manager_List_Name
    pass

def prep_ext_int_output(ep_idf, zone_outputs=[], non_zone_outputs={}):
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
        non_zone_outputs = {
            "Environment": [
                "Site Outdoor Air Drybulb Temperature",
                "Site Outdoor Air Relative Humidity",
                "Site Diffuse Solar Radiation Rate per Area",
                "Site Direct Solar Radiation Rate per Area"
            ]
        }
    '''
    print("Adding external interface outputs")
    # overwrite all output variables
    popallidfobjects(ep_idf, 'Output:variable'.upper())
    popallidfobjects(ep_idf, 'Output:Meter:MeterFileOnly'.upper())
    # add non_zone_outputs
    for e in non_zone_outputs.keys():
        for o in non_zone_outputs[e]:
            ep_idf.newidfobject(
                'Output:variable'.upper(),
                Key_Value=e,
                Variable_Name=o,
                Reporting_Frequency="timestep"
            )
            ep_idf.newidfobject(
                "ExternalInterface:FunctionalMockupUnitExport:From:Variable".upper(),
                OutputVariable_Index_Key_Name=e,
                OutputVariable_Name=o,
                FMU_Variable_Name="FMU_{}_{}".format(
                    e.replace(" ","_"),
                    o.replace(" ", "_"))
            )
    # add zone_outputs
    # output IDF obj is broken out because the * key value can be used to select
    # all zones and is standard in E+ .idf files
    for o in zone_outputs:
        ep_idf.newidfobject(
            'Output:variable'.upper(),
            Key_Value="*",
            Variable_Name=o,
            Reporting_Frequency="Timestep"
        )
    for z in ep_idf.idfobjects['Zone'.upper()]:
        for o in zone_outputs:
            ep_idf.newidfobject(
                "ExternalInterface:FunctionalMockupUnitExport:From:Variable".upper(),
                OutputVariable_Index_Key_Name=z.Name,
                OutputVariable_Name=o,
                FMU_Variable_Name="FMU_{}_{}".format(
                    z.Name.replace(" ","_"),
                    o.replace(" ", "_"))
            )
'''
TODO: Changes to eppy:
 - parse .idf comments differently or remove them
 - correctly show parameters of idfobject as .keys()
 - add expand objects feature
 - better object manipulation (e.g. popallidfobjects)
'''

# functions for eppy PR
def popallidfobjects(ep_idf, idf_obj_name):
    '''
    pops all idf objects of any key name if object exists.
    extension of eppy.modeleditor.IDF.popidfobjects
    '''
    if idf_obj_name in ep_idf.idfobjects:
        for i in range(len(ep_idf.idfobjects[idf_obj_name])):
            ep_idf.popidfobject(idf_obj_name, 0)

if __name__ == "__main__":
    print("="*80)
    print("EnergyPlus Control preprocessor")
    print("="*80)
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, nargs="?",
                    help="input EnergyPlus .idf file to preprocess")
    parser.add_argument("-o", "--output", type=str, nargs="?",
                    help="ouput EnergyPlus .idf file")
    parser.add_argument("-t", "--timesteps", type=str, nargs="?",
                    help="time steps per hour")
    args = parser.parse_args()
    # config .idf file paths
    print("Runtime dir: {}".format(os.getcwd()))
    if args.input:
        idf_in_fname = args.input
        print("Input argument: {}".format(idf_in_fname))
    else:
        raise AttributeError((
            "Missing EnergyPlus input data file (idf) "
            "e.g. -i ../idf/ep_idf_file.idf"
            ))
    if args.output:
        idf_out_fname = args.output
        if not os.path.exists(os.path.dirname(idf_out_fname)):
            raise AttributeError((
            "Supplied output file name: {} "
            "is in a directory that does not exist."
            ).format(idf_out_fname))
    else:
        # default output fname, broken out from parser
        idf_out_fname = os.path.join(
            os.path.dirname(idf_in_fname),
            "test_output.idf"
        )
    # timesteps are required
    print("Timesteps per hour: {}".format(args.timesteps))
    ts = int(args.timesteps)
    if ts > 60:
        raise AttributeError((
        "Timesteps per hour of: {} is greater than maximum value of 60 seconds"
        ).format(ts))
    if ts < 6:
        raise AttributeError((
        "Timesteps per hour of: {} is less than minimum value of 6 seconds"
        ).format(ts))

    # set file paths
    idf_in_path = os.path.join(os.getcwd(), idf_in_fname)
    idf_out_path = os.path.join(os.getcwd(), idf_out_fname)
    # set E+ IDD
    idd_path = os.path.join(
        os.environ["EPLUS_DIR"], 
        f"PreProcess/IDFVersionUpdater/V{os.environ["ENERGYPLUS_INSTALL_VERSION"]}-Energy+.idd"
    )
    modeleditor.IDF.setiddname(idd_path)
    print("Running with IDD: {}".format(modeleditor.IDF.iddname))

    # load .idf with eppy
    print("loading .idf file: {}".format(idf_in_path))
    ep_idf = modeleditor.IDF(idf_in_path)
    prep_ep_version(ep_idf, ("9","2","0"))
    prep_timesteps(ep_idf, ts)
    prep_runtime(ep_idf)
    prep_ext_int(ep_idf)
    # set the intial temperature via the initial setpoint which will be tracked 
    # in the warmup simulation
    prep_onoff_setpt_control(
        ep_idf,
        FMU_control_type_var_init=2,
        FMU_control_heating_var_init=21.0,
        FMU_control_cooling_var_init=15.0
    )
    # create per zone outputs depending on HVAC system type
    zone_outputs = [
        "Zone Air Temperature",
        "Zone Thermostat Heating Setpoint Temperature",
        "Zone Thermostat Cooling Setpoint Temperature",
        "Zone Air System Sensible Heating Rate",
        "Zone Air System Sensible Cooling Rate",
        "Zone Total Internal Total Heating Rate",
        "Zone Total Internal Latent Gain Rate",
        "Zone Total Internal Convective Heating Rate",
        "Zone Total Internal Radiant Heating Rate",
        "Zone Total Internal Visible Radiation Heating Rate"
    ]
    non_zone_outputs = {
        "Environment": [
            "Site Outdoor Air Relative Humidity",
            "Site Outdoor Air Drybulb Temperature",
            "Site Diffuse Solar Radiation Rate per Area",
            "Site Direct Solar Radiation Rate per Area"
        ],
    }
    prep_ext_int_output(
        ep_idf,
        zone_outputs=zone_outputs,
        non_zone_outputs=non_zone_outputs)
    ep_idf.saveas(idf_out_fname)
    print("Output: {}".format(idf_out_path))
