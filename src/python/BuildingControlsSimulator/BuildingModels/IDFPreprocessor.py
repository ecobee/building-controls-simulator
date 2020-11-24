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

from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)

DSOA_OBJ_BASE_NAME = "prep_dsoa_"


@attr.s(kw_only=True, init=True)
class IDFPreprocessor:
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs."""

    # user must supply an idf file as either 1) full path, or 2) a file in self.idf_dir
    idf_file = attr.ib()
    building_config = attr.ib(factory=dict)

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
        sim_config,
        datetime_channel,
        weather_channel,
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
            self.get_zone_info()
            # prepare idf file
            self.prep_remove_unused_objects()
            self.prep_ep_version(self.ep_version)
            self.prep_building()
            self.prep_simulation_control()
            self.prep_shadow_calculation()
            self.prep_runperiod(sim_config, datetime_channel)
            self.prep_timesteps(self.timesteps_per_hour)
            self.prep_algorithms()
            self.prep_ground_boundary_temp()
            self.prep_ext_int()
            self.prep_insulation()
            self.prep_hvac(datetime_channel, weather_channel)
            self.prep_windows()
            self.prep_ventilation_infiltation()
            self.prep_thermal_mass()

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

    def expand_zones(self, zone_or_zone_list):
        if zone_or_zone_list in self.zone_lists.keys():
            return self.zone_lists[zone_or_zone_list]
        else:
            return [zone_or_zone_list]

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
            _zone
            for obj in self.ep_idf.idfobjects["ZoneHVAC:EquipmentConnections"]
            for _zone in self.expand_zones(obj.Zone_Name)
        ]

        vent_design_zones = [
            _zone
            for obj in self.ep_idf.idfobjects["ZoneVentilation:DesignFlowRate"]
            for _zone in self.expand_zones(obj.Zone_or_ZoneList_Name)
        ]

        sizing_zones = [
            _zone
            for obj in self.ep_idf.idfobjects["sizing:Zone"]
            for _zone in self.expand_zones(obj.Zone_or_ZoneList_Name)
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
            _zone
            for obj in self.ep_idf.idfobjects["people"]
            for _zone in self.expand_zones(obj.Zone_or_ZoneList_Name)
        ]

        if any([z not in self.conditioned_zones for z in self.occupied_zones]):
            logger.error(
                f"IDF file: {self.idf_file} contains occupied zones that"
                " do not appear to be conditioned."
            )

    def prep_remove_unused_objects(self):
        self.popallidfobjects("Site:Location")

    def prep_building(self):
        self.popallidfobjects("Building")
        self.ep_idf.newidfobject(
            "Building",
            Name="prep_building_name",
            North_Axis=0,
            Terrain="Suburbs",
            Loads_Convergence_Tolerance_Value=0.3,
            Temperature_Convergence_Tolerance_Value=0.3,
            Solar_Distribution="MinimalShadowing",
            Maximum_Number_of_Warmup_Days=20,
            Minimum_Number_of_Warmup_Days=2,
        )

    def prep_algorithms(self):
        """
        See Simulation Parameters group:
        https://bigladdersoftware.com/epx/docs/9-4/input-output-reference/group-simulation-parameters.html#hvacystemrootfindingalgorithm
        """
        self.popallidfobjects("SurfaceConvectionAlgorithm:Inside")
        self.ep_idf.newidfobject(
            "SurfaceConvectionAlgorithm:Inside", Algorithm="TARP"
        )

        self.popallidfobjects("SurfaceConvectionAlgorithm:Outside")
        self.ep_idf.newidfobject(
            "SurfaceConvectionAlgorithm:Outside", Algorithm="DOE-2"
        )

        self.popallidfobjects("HeatBalanceAlgorithm")
        self.ep_idf.newidfobject(
            "HeatBalanceAlgorithm", Algorithm="ConductionTransferFunction"
        )

    def prep_shadow_calculation(self):
        self.popallidfobjects("ShadowCalculation")
        self.ep_idf.newidfobject(
            "ShadowCalculation",
            Shading_Calculation_Method="PolygonClipping",
            Shading_Calculation_Update_Frequency_Method="Periodic",
            Shading_Calculation_Update_Frequency=20,
            Maximum_Figures_in_Shadow_Overlap_Calculations=200,
            Polygon_Clipping_Algorithm="SutherlandHodgman",
            Pixel_Counting_Resolution=128,
            Sky_Diffuse_Modeling_Algorithm="SimpleSkyDiffuseModeling",
            Output_External_Shading_Calculation_Results="No",
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
            Do_Plant_Sizing_Calculation="Yes",
            Run_Simulation_for_Sizing_Periods="Yes",
            Run_Simulation_for_Weather_File_Run_Periods="Yes",
            Do_HVAC_Sizing_Simulation_for_Sizing_Periods="No",
            Maximum_Number_of_HVAC_Sizing_Simulation_Passes=2,
        )

    def prep_hvac(self, datetime_channel, weather_channel):
        # TODO: set HVAC equipment from config

        if "hvac" not in self.building_config.keys():
            return

        hvac_config = self.building_config["hvac"]

        # auto sizing parameters
        self.popallidfobjects("SizingPeriod:DesignDay")
        self.popallidfobjects("Sizing:Parameters")
        self.popallidfobjects("Sizing:Zone")
        # TODO: add generated parameters for system sizing
        # self.popallidfobjects("Sizing:System")

        # set global sizing factors for over/undersizing
        self.ep_idf.newidfobject(
            "Sizing:Parameters",
            Heating_Sizing_Factor=hvac_config.get(
                "heating_sizing_factor", 1.0
            ),
            Cooling_Sizing_Factor=hvac_config.get(
                "cooling_sizing_factor", 1.0
            ),
        )
        for zone_name in self.occupied_zones:

            self.ep_idf.newidfobject(
                "Sizing:Zone",
                Zone_or_ZoneList_Name=zone_name,
                Zone_Cooling_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                Zone_Cooling_Design_Supply_Air_Temperature=12,
                Zone_Heating_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                Zone_Heating_Design_Supply_Air_Temperature=50,
                Zone_Cooling_Design_Supply_Air_Humidity_Ratio=0.008,
                Zone_Heating_Design_Supply_Air_Humidity_Ratio=0.008,
                Design_Specification_Outdoor_Air_Object_Name=DSOA_OBJ_BASE_NAME
                + zone_name,
                Cooling_Design_Air_Flow_Method="DesignDay",
                Cooling_Minimum_Air_Flow_per_Zone_Floor_Area=0.000762,
                Heating_Design_Air_Flow_Method="DesignDay",
                Heating_Maximum_Air_Flow_per_Zone_Floor_Area=0.002032,
                Heating_Maximum_Air_Flow=0.1415762,
                Heating_Maximum_Air_Flow_Fraction=0.3,
                Account_for_Dedicated_Outdoor_Air_System="No",
                Dedicated_Outdoor_Air_System_Control_Strategy="NeutralSupplyAir",
                Dedicated_Outdoor_Air_Low_Setpoint_Temperature_for_Design="autosize",
                Dedicated_Outdoor_Air_High_Setpoint_Temperature_for_Design="autosize",
            )

        # use epw data for climate to set deisgn day values
        winter_rec = weather_channel.fill_epw_data[
            weather_channel.fill_epw_data.temp_air
            == weather_channel.fill_epw_data.temp_air.min()
        ].iloc[0]

        self.ep_idf.newidfobject(
            "SizingPeriod:DesignDay",
            Name="winter_design_day",
            Month=winter_rec["month"],
            Day_of_Month=winter_rec["day"],
            Day_Type="WinterDesignDay",
            Maximum_DryBulb_Temperature=winter_rec["temp_air"],
            Daily_DryBulb_Temperature_Range=0,
            DryBulb_Temperature_Range_Modifier_Type="DefaultMultipliers",
            Humidity_Condition_Type="DewPoint",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb=winter_rec["temp_dew"],
            Barometric_Pressure=winter_rec["atmospheric_pressure"],
            Wind_Speed=winter_rec["wind_speed"],
            Wind_Direction=winter_rec["wind_direction"],
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="No",
            Solar_Model_Indicator="ASHRAEClearSky",
            Sky_Clearness=0.0,
        )

        summer_rec = weather_channel.fill_epw_data[
            weather_channel.fill_epw_data.temp_air
            == weather_channel.fill_epw_data.temp_air.max()
        ].iloc[0]

        self.ep_idf.newidfobject(
            "SizingPeriod:DesignDay",
            Name="summer_design_day",
            Month=summer_rec["month"],
            Day_of_Month=summer_rec["day"],
            Day_Type="SummerDesignDay",
            Maximum_DryBulb_Temperature=summer_rec["temp_air"],
            Daily_DryBulb_Temperature_Range=0,
            DryBulb_Temperature_Range_Modifier_Type="DefaultMultipliers",
            Humidity_Condition_Type="DewPoint",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb=summer_rec["temp_dew"],
            Barometric_Pressure=summer_rec["atmospheric_pressure"],
            Wind_Speed=summer_rec["wind_speed"],
            Wind_Direction=summer_rec["wind_direction"],
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="No",
            Solar_Model_Indicator="ASHRAEClearSky",
            Sky_Clearness=1.0,
        )

    def prep_windows(self):

        if "windows" not in self.building_config.keys():
            return

        window_config = self.building_config["windows"]
        # TODO: window_to_wall ratio

        # set WindowMaterial:SimpleGlazingSystem obj and connect to windows

        window_name = "prep_window_material"
        self.ep_idf.newidfobject(
            "WindowMaterial:SimpleGlazingSystem",
            Name=window_name,
            UFactor=window_config["u_factor"],
            Solar_Heat_Gain_Coefficient=window_config["solar_heat_gain"],
            Visible_Transmittance=window_config["visible_transmittance"],
        )

        cons_name = "prep_window_construction"
        self.ep_idf.newidfobject(
            "Construction", Name=cons_name, Outside_Layer=window_name
        )

        for window in self.ep_idf.idfobjects["Window"]:
            window.Construction_Name = cons_name

    def prep_thermal_mass(self):
        """Add thermal mass evenly distributed in occupied zones."""

        if "thermal_mass" not in self.building_config.keys():
            return

        # remove any lingering thermal mass
        self.popallidfobjects("InternalMass")

        # use wood thermal properties
        thickness = 0.25  # kg
        density = 600.0  # kg/m^3
        specific_heat = 1700  # J/kg*K
        conductivity = 0.12

        equivalent_area = self.building_config["thermal_mass"] / (
            thickness * density * specific_heat
        )

        # make material to avoid collisions
        mat_name = "prep_thermal_mass_material"
        self.ep_idf.newidfobject(
            "Material",
            Name=mat_name,
            Roughness="MediumSmooth",
            Thickness=thickness,
            Conductivity=conductivity,
            Density=density,
            Specific_Heat=specific_heat,
        )

        # make construction
        cons_name = "prep_thermal_mass_construction"
        self.ep_idf.newidfobject(
            "Construction", Name=cons_name, Outside_Layer=mat_name
        )

        for zone in self.occupied_zones:
            self.ep_idf.newidfobject(
                "InternalMass",
                Name="prep_thermal_mass_obj",
                Construction_Name=cons_name,
                Zone_or_ZoneList_Name=zone,
                Surface_Area=equivalent_area / len(self.occupied_zones),
            )

    def prep_insulation(self):
        """
        Specify insulation values in R-si for all exterior constructions of building
        envelope using building config.

        Building config like:
        {
            "insulation_r_si": {
                "Exterior Roof": 1.5,
                "Interior Ceiling": 6.5,
                "Interior Floor": 1.5,
                "Exterior Wall": 5.2,
                "Exterior Floor": 4.5,
            }
        }

        """
        if "insulation_r_si" not in self.building_config.keys():
            return

        insulation_config = self.building_config["insulation_r_si"]

        cons = [
            cons
            for cons in self.ep_idf.idfobjects["Construction"]
            if cons.Name in insulation_config.keys()
        ]

        # use equivalent of EPS insulation: k = 0.035 (W/m^2⋅K) and
        k_eps = 0.035

        for con in cons:
            diff_r_si = insulation_config[con.Name] - con.rvalue
            mat_name = f"{con.Name}_prep_insulation_material"
            layers = [con.Outside_Layer]
            for layer_idx in range(2, 10):
                _layer = getattr(con, f"Layer_{layer_idx}")
                if _layer:
                    layers.append(_layer)
                else:
                    break

            # if removing insulation, replace insulation layer
            # if adding insulation add new layer
            # note: must generate new materials per construction to avoid
            # name collisions and re-changing materials
            if diff_r_si < 0:
                mats = []
                for layer in layers:
                    mats.append(
                        next(
                            mat
                            for mat in self.ep_idf.idfobjects["Material"]
                            if mat.Name == layer
                        )
                    )

                # find material layer with max R-si value in current construction
                r_values = [mat.rvalue for mat in mats]
                mat_idx = r_values.index(max(r_values))

                # take this material and replace it with EPS meet desired R
                if r_values[mat_idx] + diff_r_si > 0:
                    self.ep_idf.newidfobject(
                        "Material",
                        Name=mat_name,
                        Roughness="Rough",
                        Thickness=(r_values[mat_idx] + diff_r_si) * k_eps,
                        Conductivity=k_eps,
                        Density=30.0,
                        Specific_Heat=1300,
                    )
                    if mat_idx == 0:
                        setattr(con, "Outside_Layer", mat_name)
                    else:
                        setattr(con, f"Layer_{mat_idx+1}", mat_name)
                else:
                    raise NotImplementedError(
                        f"insulation_config[{con.Name}]={insulation_config[con.Name]}. "
                        + f"Reducing insulation beyond max R layer not implemented."
                    )
            else:
                # add additional layer on inside containing difference in R-si
                # generate material of exact thickness required
                self.ep_idf.newidfobject(
                    "Material",
                    Name=mat_name,
                    Roughness="Rough",
                    Thickness=diff_r_si * k_eps,
                    Conductivity=k_eps,
                    Density=30.0,
                    Specific_Heat=1300,
                )

                setattr(con, f"Layer_{len(layers)+1}", mat_name)

    def prep_ventilation_infiltation(self):
        """Use ASHRAE Standard 62.2 method for calculating infiltration and
        ventilation requirement.

        All areas in m^2, flows in L/s.

        # Q_total requirement

        (4-1b): Q_total = 0.15*A_floor + 3.5*(N_br + 1)
        A_floor = floor area of conditioned/occupied space (includes heated basements)
        N_br = number bedrooms (proxy for number of occupants)

        (4-2): Q_fan = Q_total - phi(Q_inf * A_ext)
        phi = Q_inf/Q_tot, or 1 for balanced ventilation systems
        A_ext = 1 for detached dwelling, otherwise ratio of exterior not attached

        (4-3): Q_inf = 0.052 * Q50 * wsf * (H/H_r)^z
        Q50 = Air Change per Hour at 50pa pressurization (ACH50)
        (ACH50 defined in ASTM E1827 or ANSI/RESNET/ICC Standard 380)
        wsf = weather and shielding factor in Appendix B for site location
        H = above grade height of pressure boundary
        H_r = reference height (2.5m)
        z = 0.4 for Effective Annual Average Infiltration Rate

        see: ASHRAE Standard 62.2 Section 4. Dwelling-Unit Ventilation
        https://ashrae.iwrapper.com/ASHRAE_PREVIEW_ONLY_STANDARDS/STD_62.2_2019

        ZoneInfiltration:DesignFlowRate requires:
        Constant_Term_Coefficient
        Temperature_Term_Coefficient
        Velocity_Term_Coefficient
        Velocity_Squared_Term_Coefficient

        BLAST (one of the EnergyPlus predecessors) used the following values as
        defaults:
        Constant_Term_Coefficient = 0.606
        Temperature_Term_Coefficient = 0.03636
        Velocity_Term_Coefficient = 0.1177
        Velocity_Squared_Term_Coefficient = 0.0
        These coefficients produce a value
        of 1.0 at 0C deltaT and 3.35 m/s (7.5 mph) windspeed, which corresponds
        to a typical summer condition. At a winter condition of 40C deltaT and
        6 m/s (13.4 mph) windspeed, these coefficients would increase the
        infiltration rate by a factor of 2.75.

        In DOE-2 (the other EnergyPlus predecessor), the air change method
        defaults are (adjusted to SI units):
        Constant_Term_Coefficient = 0.0
        Temperature_Term_Coefficient = 0.224
        Velocity_Term_Coefficient = 0.0
        Velocity_Squared_Term_Coefficient = 0.0.
        With these coefficients, the summer conditions above would give a factor of
        0.75, and the winter conditions would give 1.34. A windspeed of 4.47 m/s
        (10 mph) gives a factor of 1.0.

        These coefficients can be estimated based on Sherman and Grimsrud (1980)
        model.

        q_inf = sqrt(q_s^2 + q_w^2) (47)

        ## stack infiltration airflow
        q_s = c * C_s * abs(T_in - T_out)^n
        c = flow coefficient
        C_s = stack coefficient
        n = pressure coefficient (0.67)

        a simple value for c * C_s = 0.05 * 0.07 = 0.0035

        ## wind infiltration airlfow
        q_w = c * C_w * (s*U)^(2*n) (wind airflow)

        c = flow coefficient
        C_s = wind coefficient
        s = shelter coefficient
        U = G * U_met
        G = wind speed multiplier
        n = pressure coefficient (0.67)
        Note: The pressure coefficient (n) and flow coefficient (c) are
        determined empirically and comes from the geometry of the
        infiltration cracks, see equation (40).
        The value of n generally is between 0.6 and 0.7.
        The value of c generally is between 0.050 and 0.100 m3 / (s*Pa^n)

        a simple value for c * C_w = 0.05 * 0.15 = 0.0075

        assuming q_s ~= q_w then: q_inf = q_s/sqrt(2) + q_w/sqrt(2)
        therefore adding the coefficeint 1/sqrt(2) to each independently
        allows for a lower bound estimate of each in super position.

        The following formulas can then be using to estimate
        Velocity_Term_Coefficient
        Temperature_Term_Coefficient = 0.0035 * 1/sqrt(2) = 0.0025
        Velocity_Squared_Term_Coefficient = 0.0075 * 1/sqrt(2) = 0.0053

        assuming averge velocity is 7 m/s:
        Velocity_Term_Coefficient = 0.0371

        Therefore:
        Constant_Term_Coefficient = 0.606
        Temperature_Term_Coefficient = 0.0025
        Velocity_Term_Coefficient = 0.0371
        Velocity_Squared_Term_Coefficient = 0.0

        # TODO: alternate method:
        Sherman and Grimsrud (1980) model
        EnergyPLus implements using ZoneInfiltration:EffectiveLeakageArea
        Can specify using ELA_4, which can be computed from NL value, or ACH50
        using equations from ASHRAE Fundamentals Handbook 2017.

        # TODO: alternate method:
        Enhanced Model: Infiltration method from Walker and Wilson (1993)
        from ASHRAE Fundamentals Handbook 2017, Chapter 16.25
        Equation (47), (49) and (50)

        q_inf = sqrt(q_s^2 + q_w^2) (47)

        See: EnergyPlus Group Airflow
        https://bigladdersoftware.com/epx/docs/9-4/input-output-reference/group-airflow.html
        """

        if "infilration_ventilation" not in self.building_config.keys():
            return

        vent_objs = [
            "ZoneInfiltration:DesignFlowRate",
            "ZoneInfiltration:EffectiveLeakageArea",
            "ZoneInfiltration:FlowCoefficient",
            "ZoneVentilation:DesignFlowRate",
            "ZoneVentilation:WindandStackOpenArea",
        ]

        vent_design_zones = []
        for vent_obj in vent_objs:
            vent_design_zones = set(vent_design_zones) | set(
                [
                    _zone
                    for obj in self.ep_idf.idfobjects[
                        "ZoneVentilation:DesignFlowRate"
                    ]
                    for _zone in self.expand_zones(obj.Zone_or_ZoneList_Name)
                ]
            )
            self.popallidfobjects(vent_obj)

        occupied_zones = [
            _zone
            for _zone in self.ep_idf.idfobjects["Zone"]
            if _zone.Name in self.occupied_zones
        ]

        # Z = 0.0 is considered to be ground level
        z_ground = 0.0
        z_coords = []
        volume_total = 0.0
        zone_volumes = {}
        a_floor = 0.0
        for _zone in self.ep_idf.idfobjects["Zone"]:
            if _zone.Name in self.occupied_zones:
                zone_floor_area = 0
                zone_x_coords = []
                zone_y_coords = []
                zone_z_coords = []
                for _surf in _zone.zonesurfaces:

                    zone_x_coords = zone_x_coords + [
                        xyz[0] for xyz in _surf.coords
                    ]
                    zone_y_coords = zone_y_coords + [
                        xyz[1] for xyz in _surf.coords
                    ]
                    zone_z_coords = zone_z_coords + [
                        xyz[2] for xyz in _surf.coords
                    ]
                    if _surf.Surface_Type == "Floor":
                        # zone may have multiple floors
                        zone_floor_area += _surf.area

                zone_length = max(zone_x_coords) - min(zone_x_coords)
                zone_width = max(zone_y_coords) - min(zone_y_coords)
                zone_height = max(zone_z_coords) - min(zone_z_coords)
                # accumulation variables
                z_coords = z_coords + zone_z_coords
                a_floor += zone_floor_area
                zone_volumes[_zone.Name] = (
                    zone_length * zone_width * zone_height
                )
                volume_total += zone_volumes[_zone.Name]

        height_above_ground = max(z_coords) - max(min(z_coords), z_ground)

        # we assume that the number of bedrooms are equal to number of people
        n_br = sum(
            [
                people_obj.Number_of_People
                for people_obj in self.ep_idf.idfobjects["People"]
            ]
        )

        # equation 4-1b
        req_q_total = 0.15 * a_floor + 3.5 * (n_br + 1)

        # equation 4-3
        # q50 is expressed in L/s
        q50 = (
            volume_total
            * self.building_config["infilration_ventilation"]["ach50"]
            * (1000 / 3600)
        )
        q_inf = (
            0.052
            * q50
            * self.building_config["infilration_ventilation"]["wsf"]
            * pow((height_above_ground / 2.5), 0.4)
        )

        # equation 4-2
        # assume unbalanced ventilation
        phi = q_inf / req_q_total
        if "a_ext" in self.building_config.keys():
            a_ext = self.building_config["infilration_ventilation"]["a_ext"]
        else:
            # assume detached
            a_ext = 1.0

        q_fan = req_q_total - phi * (q_inf * a_ext)

        for zone_name in vent_design_zones:
            self.ep_idf.newidfobject(
                "ZoneInfiltration:DesignFlowRate",
                Name="BCS_infiltration",
                Zone_or_ZoneList_Name=zone_name,
                Schedule_Name="always_avail",
                Design_Flow_Rate_Calculation_Method="Flow/Zone",
                Design_Flow_Rate=q_inf
                * (zone_volumes[zone_name] / volume_total)
                / 1000.0,
                Constant_Term_Coefficient=0.606,
                Temperature_Term_Coefficient=0.0025,
                Velocity_Term_Coefficient=0.0371,
                Velocity_Squared_Term_Coefficient=0.0,
            )

            # set sizing params for infiltration
            self.popallidfobjects("DesignSpecification:OutdoorAir")
            self.ep_idf.newidfobject(
                "DesignSpecification:OutdoorAir",
                Name=DSOA_OBJ_BASE_NAME + zone_name,
                Outdoor_Air_Method="Flow/Zone",
                Outdoor_Air_Flow_per_Zone=q_inf
                * (zone_volumes[zone_name] / volume_total)
                / 1000.0,
            )

        # Exception to 4.1.2:
        # if q_fan is less than 7 L/s no mechanical ventilation is required
        if q_fan > 7.0:
            # add mechanical ventilation using ACH method for all vented zones
            logger.warn(
                "UNTESTED: Using IDFPreprocessor inserted mechanical ventilation."
            )
            # self.ep_idf.newidfobject("ZoneList", "BCS_vent_zones", list(vent_design_zones)[0])
            for zone_name in vent_design_zones:
                self.ep_idf.newidfobject(
                    "ZoneVentilation:DesignFlowRate",
                    Name="BCS_mech_ventilation",
                    Zone_or_ZoneList_Name=zone_name,
                    Schedule_Name="always_avail",
                    Design_Flow_Rate_Calculation_Method="Flow/Zone",
                    Design_Flow_Rate=q_fan
                    * (zone_volumes[zone_name] / volume_total)
                    / 1000.0,
                    Ventilation_Type="Exhaust",
                )

    def prep_runperiod(self, sim_config, datetime_channel):
        """This is not used for FMU export of energyplus
        https://simulationresearch.lbl.gov/fmu/EnergyPlus/export/userGuide/usage.html
        """
        # When using EnergyPlusToFMU the start and end day of RUNPERIOD
        # object is ignored and replaced by the start and stop time
        # provided by the master algorithm which imports the EnergyPlus FMU.
        # However, the entry Day of Week for Start Day will be used.

        # To best make use of this the RUNPERIOD will be set appropriately in
        # coordination with the available data, simulation control,
        # and weather file.
        self.popallidfobjects("RunPeriod")
        # convert to local time for setting RunPeriod
        start_utc = min(datetime_channel.data[STATES.DATE_TIME]).tz_convert(
            datetime_channel.timezone
        )
        end_utc = max(datetime_channel.data[STATES.DATE_TIME]).tz_convert(
            datetime_channel.timezone
        )
        if start_utc.year != end_utc.year:
            # EnergyPlusToFMU seems to have a bug that cause .idf file to be read
            # into eplus with the start of the year as the beginning of the RunPeriod
            raise NotImplementedError(
                "Simulations crossing yearline are not fully supported."
            )

        if self.ep_version in ["8-9-0", "9-0-1", "9-1-0"]:
            self.ep_idf.newidfobject(
                "RunPeriod",
                Name="simulation_runperiod",
                Begin_Month=start_utc.month,
                Begin_Day_of_Month=start_utc.day,
                End_Month=end_utc.month,
                End_Day_of_Month=end_utc.day,
                Day_of_Week_for_Start_Day=start_utc.day_name(),
                Use_Weather_File_Holidays_and_Special_Days="Yes",
                Use_Weather_File_Daylight_Saving_Period="No",
                Apply_Weekend_Holiday_Rule="No",
                Use_Weather_File_Rain_Indicators="Yes",
                Use_Weather_File_Snow_Indicators="Yes",
            )
        elif self.ep_version in ["9-2-0", "9-3-0", "9-4-0"]:
            self.ep_idf.newidfobject(
                "RunPeriod",
                Name="simulation_runperiod",
                Begin_Month=start_utc.month,
                Begin_Day_of_Month=start_utc.day,
                Begin_Year=start_utc.year,
                End_Month=end_utc.month,
                End_Day_of_Month=end_utc.day,
                End_Year=end_utc.year,
                Day_of_Week_for_Start_Day=start_utc.day_name(),
                Use_Weather_File_Holidays_and_Special_Days="Yes",
                Use_Weather_File_Daylight_Saving_Period="No",
                Apply_Weekend_Holiday_Rule="No",
                Use_Weather_File_Rain_Indicators="Yes",
                Use_Weather_File_Snow_Indicators="Yes",
                Treat_Weather_as_Actual="Yes",
            )

    def prep_timesteps(self, timesteps_per_hour):
        """
        Set timesteps for model.
        """
        self.popallidfobjects("Timestep")
        self.ep_idf.newidfobject(
            "Timestep", Number_of_Timesteps_per_Hour=timesteps_per_hour
        )

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
            "9-3-0": "Transition-V9-3-0-to-V9-4-0",
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

    def prep_ground_boundary_temp(self):
        obj_name = "surfPropOthSdCoefGroundBoundaryTemp"
        self.ep_idf.newidfobject(
            "SurfaceProperty:OtherSideCoefficients",
            Name=obj_name,
            Combined_ConvectiveRadiative_Film_Coefficient=0.0,
            Constant_Temperature=0.0,
            Constant_Temperature_Coefficient=0.0,
            External_DryBulb_Temperature_Coefficient=0.0,
            Ground_Temperature_Coefficient=0.2,
            Wind_Speed_Coefficient=0.0,
            Zone_Air_Temperature_Coefficient=0.8,
            Sinusoidal_Variation_of_Constant_Temperature_Coefficient="No",
            Period_of_Sinusoidal_Variation=24,
            Previous_Other_Side_Temperature_Coefficient=0.0,
        )

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

        # overwrite ZoneControl:Thermostat control objects
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

        # add diagnostics
        self.popallidfobjects("Output:Diagnostics")
        self.ep_idf.newidfobject(
            "Output:Diagnostics",
            Key_1="DisplayAllWarnings",
            Key_2="DisplayExtrawarnings",
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
