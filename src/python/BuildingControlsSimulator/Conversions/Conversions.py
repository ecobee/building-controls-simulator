# created by Tom Stesco tom.s@ecobee.com

import pandas as pd
import numpy as np


class Conversions:
    @staticmethod
    def F2C(temp_F):
        return (temp_F - 32) * 5 / 9

    @staticmethod
    def C2F(temp_C):
        return (temp_C * 9 / 5) + 32

    @staticmethod
    def C2Fx10(temp_C):
        return Conversions.C2F(temp_C) * 10

    @staticmethod
    def saturation_vapor_pressure(temperature):
        """
        The formula used is that from [Bolton1980] for T in degrees Celsius:
        """
        return 6.112 * np.exp(17.67 * temperature / (temperature + 243.5))

    @staticmethod
    def relative_humidity_from_dewpoint(temperature, dewpoint):
        """ Return RH in % [0-100]"""
        return (
            Conversions.saturation_vapor_pressure(dewpoint)
            / Conversions.saturation_vapor_pressure(temperature)
        ) * 100

    @staticmethod
    def relative_humidity_to_dewpoint(temp_air, relative_humidity):
        """
        Magnus formula with Arden Buck constants to calculate dew point.

        see:
        https://en.wikipedia.org/wiki/Dew_point
        https://doi.org/10.1175/1520-0450(1981)020%3C1527:NEFCVP%3E2.0.CO;2

        Buck, Arden L.
        "New equations for computing vapor pressure and enhancement factor."
        Journal of applied meteorology 20.12 (1981): 1527-1532.

        :param temp_air: Temperature in Celsius.
        :type temp_air: float or np.array of floats
        :param relative_humidity: Relative humidity in % [0-100]
        :type relative_humidity: float or np.array of floats

        :return dew_point: The dew point temperature in Celcius.
        """
        b = 18.678
        c = 257.14
        d = 234.5
        exp_arg = (b - (temp_air / d)) * (temp_air / (c + temp_air))
        gamma = np.log((relative_humidity / 100) * np.exp(exp_arg))
        return (c * gamma) / (b - gamma)

    @staticmethod
    def numpy_down_cast_default_value_dtype(dtype):
        """Default values for numpy/pandas dtypes. These are used when setting
        initial values for input and output data. This mostly chooses sane defaults
        that allows for not using nullable dtypes that consume much more memory.
        Checks for these coded default values should be done before using simulation
        output data.
        """
        if dtype in ["bool", "boolean"]:
            return (False, "bool")
        elif dtype in ["float32", "Float32"]:
            return (-9999.0, "float32")
        elif dtype in ["int64", "Int64"]:
            return (-99999, "int64")
        elif dtype in ["int32", "Int32"]:
            return (-9999, "int32")
        elif dtype in ["int16", "Int16"]:
            return (-999, "int16")
        elif dtype in ["int8", "Int8"]:
            return (-99, "int8")
        elif dtype in ["category", "Category"]:
            # 32 byte unicode str
            return ("", "<U32")
        elif dtype in ["datetime64[ns, utc]"]:
            return (np.datetime64("2000-01-01"), "datetime64")
        else:
            raise ValueError(f"Unsupported dtype={dtype}")
