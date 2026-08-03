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
                            "@type": "RealData",
                            "hasNumberValue": charge_current_density,
                        },
                        "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                    },
                    {
                        "@type": ["UpperVoltageLimit", "TerminationQuantity"],
                        "hasNumericalPart": {
                            "@type": "RealData",
                            "hasNumberValue": upper_voltage_limit,
                        },
                        "hasMeasurementUnit": "Volt",
                    },
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "RealData",
                                "hasNumberValue": upper_voltage_hold,
                            },
                            "hasMeasurementUnit": "Volt",
                        },
                        {
                            "@type": ["LowerCurrentDensityLimit", "TerminationQuantity"],
                            "hasNumericalPart": {
                                "@type": "RealData",
                                "hasNumberValue": cutoff_current,
                            },
                            "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                        },
                    ],
                    "hasNext": {
                        "@type": "Discharging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity",
                                "hasNumericalPart": {
                                    "@type": "RealData",
                                    "hasNumberValue": discharge_current_density,
                                },
                                "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                            },
                            {
                                "@type": ["LowerVoltageLimit", "TerminationQuantity"],
                                "hasNumericalPart": {
                                    "@type": "RealData",
                                    "hasNumberValue": lower_voltage_limit,
                                },
                                "hasMeasurementUnit": "Volt",
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
                            "@type": "RealData",
                            "hasNumberValue": discharge_current_density,
                        },
                        "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                    },
                    {
                        "@type": ["LowerVoltageLimit", "TerminationQuantity"],
                        "hasNumericalPart": {
                            "@type": "RealData",
                            "hasNumberValue": lower_voltage_limit,
                        },
                        "hasMeasurementUnit": "Volt",
                    },
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "RealData",
                                "hasNumberValue": lower_voltage_hold,
                            },
                            "hasMeasurementUnit": "Volt",
                        },
                        {
                            "@type": ["LowerCurrentDensityLimit", "TerminationQuantity"],
                            "hasNumericalPart": {
                                "@type": "RealData",
                                "hasNumberValue": cutoff_current,
                            },
                            "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                        },
                    ],
                    "hasNext": {
                        "@type": "Charging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity",
                                "hasNumericalPart": {
                                    "@type": "RealData",
                                    "hasNumberValue": charge_current_density,
                                },
                                "hasMeasurementUnit": "MilliAmperePerSquareCentiMetre",
                            },
                            {
                                "@type": ["UpperVoltageLimit", "TerminationQuantity"],
                                "hasNumericalPart": {
                                    "@type": "RealData",
                                    "hasNumberValue": upper_voltage_limit,
                                },
                                "hasMeasurementUnit": "Volt",
                            },
                        ],
                    },
                },
            },
        },
    }
