"""Templates for sections that are too complicated for the Excel ontology link."""


def half_cell_chg_cap(
    ref_electrode_type: str,
    charge_current_density: float,
    upper_voltage_limit: float,
    upper_voltage_hold: float,
    cutoff_current: float,
    discharge_current_density: float,
    lower_voltage_limit: float,
) -> dict:
    """Convert rated capacity vs graphite counter electrode to new format."""
    return {
        "@type": "BatteryTest",
        "hasTestObject": {
            "ElectrochemicalCell": {
                "@type": "ElectrochemicalCell",
                "hasReferenceElectrode": {"@type": ref_electrode_type},
            }
        },
        "hasMeasurementParameter": {
            "@type": ["ConstantCurrentConstantVoltageCycling"],
            "rdfs:label": "GeneratedBatteryTestProcedure",
            "rdfs:comment": "A description of a generated battery testing procedure",
            "hasTask": {
                "@type": "Charging",
                "hasInput": [
                    {
                        "@type": "ElectricCurrentDensity",
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": charge_current_density,
                        },
                        "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                    },
                    {
                        "@type": ["UpperVoltageLimit", "TerminationQuantity"],
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": upper_voltage_limit,
                        },
                        "hasMeasurementUnit": "emmo:Volt",
                    },
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": upper_voltage_hold,
                            },
                            "hasMeasurementUnit": "emmo:Volt",
                        },
                        {
                            "@type": ["LowerCurrentDensityLimit", "TerminationQuantity"],
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": cutoff_current,
                            },
                            "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                        },
                    ],
                    "hasNext": {
                        "@type": "Discharging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity",
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": discharge_current_density,
                                },
                                "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                            },
                            {
                                "@type": ["LowerVoltageLimit", "TerminationQuantity"],
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": lower_voltage_limit,
                                },
                                "hasMeasurementUnit": "emmo:Volt",
                            },
                        ],
                    },
                },
            },
        },
    }


def half_cell_dchg_cap(
    ref_electrode_type: str,
    discharge_current_density: float,
    lower_voltage_limit: float,
    lower_voltage_hold: float,
    cutoff_current: float,
    charge_current_density: float,
    upper_voltage_limit: float,
) -> dict:
    """Convert rated capacity vs Lithium electrode to new format."""
    return {
        "@type": "BatteryTest",
        "hasTestObject": {
            "ElectrochemicalHalfCell": {
                "@type": "ElectrochemicalHalfCell",
                "hasReferenceElectrode": {"@type": ref_electrode_type},
            }
        },
        "hasMeasurementParameter": {
            "@type": [
                "ConstantCurrentConstantVoltageCycling",
            ],
            "rdfs:label": "GeneratedBatteryTestProcedure",
            "rdfs:comment": "A description of a generated battery testing procedure",
            "hasTask": {
                "@type": "Discharging",
                "hasInput": [
                    {
                        "@type": "ElectricCurrentDensity",
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": discharge_current_density,
                        },
                        "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                    },
                    {
                        "@type": ["LowerVoltageLimit", "TerminationQuantity"],
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": lower_voltage_limit,
                        },
                        "hasMeasurementUnit": "emmo:Volt",
                    },
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": lower_voltage_hold,
                            },
                            "hasMeasurementUnit": "emmo:Volt",
                        },
                        {
                            "@type": ["LowerCurrentDensityLimit", "TerminationQuantity"],
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": cutoff_current,
                            },
                            "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                        },
                    ],
                    "hasNext": {
                        "@type": "Charging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity",
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": charge_current_density,
                                },
                                "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre",
                            },
                            {
                                "@type": ["UpperVoltageLimit", "TerminationQuantity"],
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": upper_voltage_limit,
                                },
                                "hasMeasurementUnit": "emmo:Volt",
                            },
                        ],
                    },
                },
            },
        },
    }
