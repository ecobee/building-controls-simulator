# created by Tom Stesco tom.s@ecobee.com

import pandas as pd
import numpy as np


class Conversions:
    @staticmethod
    def F2C(temp_F):
        return (temp_F - 32) * 5 / 9

    @staticmethod
    def saturation_vapor_pressure(temperature):
        """
        The formula used is that from [Bolton1980] for T in degrees Celsius:
        """
        return 6.112 * np.exp(17.67 * temperature / (temperature + 243.5))

    @staticmethod
    def relative_humidity_from_dewpoint(temperature, dewpoint):
        return Conversions.saturation_vapor_pressure(
            dewpoint
        ) / Conversions.saturation_vapor_pressure(temperature)

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
