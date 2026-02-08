"""
This module contains template for certain parts that are too complicated to be instructed using Excel template.
"""

SNIPPTED_RATED_CAPACITY_POSITIVE_ELECTRODE = {
    "@type": "BatteryTest",
    "hasTestObject": {
        "ElectrochemicalCell": {
            "@type": "ElectrochemicalCell",
            "hasNegativeElectrode": {
                "@type": "Graphite"
            }
          }
        },
        "hasMeasurementParameter": {
            "@type": [
                "ConstantCurrentConstantVoltageCycling"
            ],
            "rdfs:label": "GeneratedBatteryTestProcedure",
            "rdfs:comment": "A description of a generated battery testing procedure",
            "hasTask": {
                "@type": "Charging",
                "hasInput": [
                    {
                        "@type": "ElectricCurrentDensity" ,
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": "<<<<POS_1-original=0.1>>>>"
                        },
                        "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                    },
                    {
                        "@type": [
                            "UpperVoltageLimit",
                            "TerminationQuantity" 
                        ],
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": "<<<<POS_2-original=4.2>>>>"
                        },
                        "hasMeasurementUnit": "emmo:Volt"
                    }
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": "<<<<POS_3-original=4.2>>>>"
                            },
                            "hasMeasurementUnit": "emmo:Volt"
                        },
                        {
                            "@type": [
                                "LowerCurrentDensityLimit",
                                "TerminationQuantity" 
                            ],
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": "<<<<POS_4-original=0.01>>>>"
                            },
                            "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                        }
                    ],
                    "hasNext": {
                        "@type": "Discharging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity" ,
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": "<<<<POS_5-original=0.1>>>>"
                                },
                                "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                            },
                            {
                                "@type": [
                                    "LowerVoltageLimit",
                                    "TerminationQuantity" 
                                ],
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": "<<<<POS_6-original=3.0>>>>"
                                },
                                "hasMeasurementUnit": "emmo:Volt"
                            }
                        ]
                }
            }
        }
    }
}

SNIPPTED_RATED_CAPACITY_NEGATIVE_ELECTRODE = {
    "@type": "BatteryTest",
    "hasTestObject": {
        "ElectrochemicalHalfCell": {
            "@type": "ElectrochemicalHalfCell",
            "hasReferenceElectrode": {
                "@type": "LithiumElectrode"
                }
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
                        "@type": "ElectricCurrentDensity" ,
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": "<<<<NEG_1-original=0.1>>>"
                        },
                        "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                    },
                    {
                        "@type": [
                            "LowerVoltageLimit",
                            "TerminationQuantity" 
                        ],
                        "hasNumericalPart": {
                            "@type": "emmo:RealData",
                            "hasNumberValue": "<<<<NEG_2-original=0.01>>>"
                        },
                        "hasMeasurementUnit": "emmo:Volt"
                    }
                ],
                "hasNext": {
                    "@type": "VoltageHold",
                    "hasInput": [
                        {
                            "@type": "Voltage",
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": "<<<<NEG_3-original=0.01>>>"        
                            },
                            "hasMeasurementUnit": "emmo:Volt"
                        },
                        {
                            "@type": [
                                "LowerCurrentDensityLimit",
                                "TerminationQuantity" 
                            ],
                            "hasNumericalPart": {
                                "@type": "emmo:RealData",
                                "hasNumberValue": "<<<<NEG_4-original=0.01>>>"
                            },
                            "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                        }
                    ],
                    "hasNext": {
                        "@type": "Charging",
                        "hasInput": [
                            {
                                "@type": "ElectricCurrentDensity" ,
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": "<<<<NEG_5-original=0.1>>>"
                                },
                                "hasMeasurementUnit": "emmo:MilliAmperePerSquareCentiMetre"
                            },
                            {
                                "@type": [
                                    "LowerVoltageLimit",
                                    "TerminationQuantity" 
                                ],
                                "hasNumericalPart": {
                                    "@type": "emmo:RealData",
                                    "hasNumberValue": "<<<<NEG_6-original=1.0>>>"
                                },
                                "hasMeasurementUnit": "emmo:Volt"
                            }
                        ]
                }
            }
        }
    }
}

