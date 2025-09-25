from dataclasses import dataclass, field
import pandas as pd
import auxiliary as aux 
import datetime
from pandas import DataFrame
import numpy as np
from excel_tools import read_excel_preserve_decimals as read_excel
from json_template import SNIPPTED_RATED_CAPACITY_POSITIVE_ELECTRODE, SNIPPTED_RATED_CAPACITY_NEGATIVE_ELECTRODE


APP_VERSION = "1.3.0"


@dataclass
class ExcelContainer:
    excel_file: str
    data: dict = field(init=False)

    def __post_init__(self):
        # use the helper in place of pd.read_excel so decimal precision is kept
        self.data = {
            "schema":            read_excel(self.excel_file, sheet_name="Schema"),
            "unit_map":          read_excel(self.excel_file, sheet_name="Ontology - Unit"),
            "context_toplevel":  read_excel(self.excel_file, sheet_name="@context-TopLevel"),
            "context_connector": read_excel(self.excel_file, sheet_name="@context-Connector"),
            "unique_id":         read_excel(self.excel_file, sheet_name="Unique ID"),
        }

def get_information_value(df: DataFrame, row_to_look: str, col_to_look: str = "Value", col_to_match: str = "Metadata") -> str | None:
    """
    Retrieves the value from a specified column where a different column matches a given value.

    Parameters:
    df (DataFrame): The DataFrame to search within.
    row_to_look (str): The value to match within the column specified by col_to_match.
    col_to_look (str): The name of the column from which to retrieve the value. Default is "Key".
    col_to_match (str): The name of the column to search for row_to_look. Default is "Item".

    Returns:
    str | None: The value from the column col_to_look if a match is found; otherwise, None.
    """
    if row_to_look.endswith(' '):  # Check if the string ends with a space
        row_to_look = row_to_look.rstrip(' ')  # Remove only trailing spaces
    result = df.query(f"{col_to_match} == @row_to_look")[col_to_look]
    return result.iloc[0] if not result.empty else None


def create_jsonld_with_conditions(data_container: ExcelContainer) -> dict:
    """
    Creates a JSON-LD structure based on the provided data container containing schema and context information.

    This function extracts necessary information from the schema and context sheets of the provided
    `ExcelContainer` to generate a JSON-LD object. It performs validation on required fields, handles
    ontology links, and structures data in compliance with the EMMO domain for battery context.

    Args:
        data_container (ExcelContainer): A datalcass container with data extracted from the input Excel schema required for generating JSON-LD,
            including schema, context, and unique identifiers.

    Returns:
        dict: A JSON-LD dictionary representing the structured information derived from the input data.

    Raises:
        ValueError: If required fields are missing or have invalid data in the schema or unique ID sheets.
    """
    schema = data_container.data['schema']
    context_toplevel = data_container.data['context_toplevel']
    context_connector = data_container.data['context_connector']

    #Harvest the information for the required section of the schemas
    ls_info_to_harvest = [
    "Cell type", 
    "Cell ID", 
    "Date of cell assembly", 
    "Institution/company",
    "Scientist/technician/operator" 
    ]

    dict_harvested_info = {}

    #Harvest the required value from the schema sheet. 
    for field in ls_info_to_harvest:
        if get_information_value(df=schema, row_to_look=field) is np.nan:
            raise ValueError(f"Missing information in the schema, please fill in the field '{field}'")
        else:
            dict_harvested_info[field] = get_information_value(df=schema, row_to_look=field)

    #Harvest unique ID value for the required value from the schema sheet.
    ls_id_info_to_harvest = [ "Institution/company", "Scientist/technician/operator"]
    dict_harvest_id = {}
    for id in ls_id_info_to_harvest:
        try:
            dict_harvest_id[id] = get_information_value(df=data_container.data['unique_id'],
                                                        row_to_look=dict_harvested_info[id],
                                                        col_to_look = "ID",
                                                        col_to_match="Item")
            if dict_harvest_id[id] is None:
                raise ValueError(f"Missing unique ID for the field '{id}'")
        except:
            raise ValueError(f"Missing unique ID for the field '{id}'")

    jsonld = {
        "@context": ["https://w3id.org/emmo/domain/battery/context", {}],
        "@type": dict_harvested_info['Cell type'],
        "schema:version": get_information_value(df=schema, row_to_look='BattINFO CoinCellSchema version'),
        "schema:productID": dict_harvested_info['Cell ID'],
        "schema:dateCreated": dict_harvested_info['Date of cell assembly'],
        "schema:creator": {
                            "@type": "schema:Person",
                            "@id": dict_harvest_id['Scientist/technician/operator'],
                            "schema:name": dict_harvested_info['Scientist/technician/operator']
                            },
        "schema:manufacturer": {
                            "@type": "schema:Organization",
                            "@id": dict_harvest_id['Institution/company'],
                            "schema:name": dict_harvested_info['Institution/company']
                            },
        "rdfs:comment": []
    }

    for _, row in context_toplevel.iterrows():
        jsonld["@context"][1][row['Item']] = row['Key']

    jsonld["rdfs:comment"].append(f"BattINFO Converter version: {APP_VERSION}")
    jsonld["rdfs:comment"].append(f"Software credit: This JSON-LD was created using BattINFO converter (https://battinfoconverter.streamlit.app/) version: {APP_VERSION} and the coin cell battery schema version: {jsonld['schema:version']}, this web application was developed at Empa, Swiss Federal Laboratories for Materials Science and Technology in the Laboratory Materials for Energy Conversion")

    for _, row in schema.iterrows():
        if pd.isna(row['Value']) or row['Ontology link'] == 'NotOntologize':
            continue
        if row['Ontology link'] == 'Comment':
            if row['Unit'] == 'No Unit':
                jsonld["rdfs:comment"].append(f"{row['Metadata']}: {row['Value']}")
            else:
                jsonld["rdfs:comment"].append(f"{row['Metadata']}: {row['Value']} {row['Unit']}")
            continue

        ontology_path = row['Ontology link'].split('-')

        # Default behavior for other entries
        if pd.isna(row['Unit']):
            raise ValueError(
                f"The value '{row['Value']}' is filled in the wrong row, please check the schema"
            )
        aux.add_to_structure(jsonld, ontology_path, row['Value'], row['Unit'], data_container)
    return jsonld


def assit_format_json_rated_capacity(json_dict: dict) -> dict:
    """
    Assit formating rated capacity part to follow the newly purposed structure.

    In a discussion with BattINFO ontology team (Simon Clark), certain structure on how to properly define rated capacity is recommended.
    Nevertheless, this structure is too complicated to be implement directly in the Excel template. To achieve that many specific functions may have to be implemented.
    Since this is likely very specific to our definition of coin cell and less likely to be used by other users not using our template, we decide to just have a specific function
    to handle this structure directly from a pre-defined structure. In addition, the new template would make sence only if the users input all of the pre-defined value in the Excel template file,
    otherwise the original structure is better to preserve the information. So, we decide this function in the way that it will only kick-in to modify the resulting JSON-LD file only if all
    the required field is input. 
    ** This version remians a beta version for this function. Further discussion on what to do / how to proceed when the user input different reference electrode  (yes,no) remians to be discussed. 

    Args:
        json_dict (dict): The JSON dictionary to format.

    Returns:
        dict: The modified JSON dictionary with the rated capacity section formatted according to the new structure.
    """
    try:
        ##Positive electrode
        #Extract the values
        pos_1 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        pos_2 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentCharging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"]
        pos_3 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantVoltageCharging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"]
        pos_4 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantVoltageCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        pos_5 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentDischarging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        pos_6 = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentDischarging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"]
        
        #Load the template with pre-defined place holder 
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = SNIPPTED_RATED_CAPACITY_POSITIVE_ELECTRODE
        
        #Re-assign the values
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = pos_1
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = pos_2
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = pos_3
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = pos_4
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasNext"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = pos_5
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasNext"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = pos_6

        ##Negative electrode
        #Extract the values
        neg_1 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentDischarging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        neg_2 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentDischarging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"]
        neg_3 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantVoltageCharging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"]
        neg_4 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantVoltageCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        neg_5 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"]
        neg_6 = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]["ConstantCurrentCharging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"]


        #Load the template with pre-defined place holder 
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = SNIPPTED_RATED_CAPACITY_NEGATIVE_ELECTRODE

        #Re-assign the values
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = neg_1
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = neg_2
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = neg_3
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = neg_4
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasNext"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"] = neg_5
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasMeasurementParameter"]["hasTask"]["hasNext"]["hasNext"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"] = neg_6
        
        json_output = json_dict
    #If the try claus failed (likely due to not all pre-defined values required for the formatting the rated capacity strcuture is given, simply return the original json_dict)
    except: 
        json_output = json_dict
    return json_output

def convert_excel_to_jsonld(excel_file: ExcelContainer, debug_mode:bool = True) -> dict:
    """
    Converts an Excel file into a JSON-LD representation.

    This function initializes a new session for converting an Excel file, processes the data
    using the `ExcelContainer` class, and generates a complete JSON-LD object. It uses the `create_jsonld_with_conditions`
    function to construct a structured section of the JSON-LD and incorporates it into the final output.

    Args:
        excel_file (ExcelContainer): An instance of the `ExcelContainer` dataclass encapsulating the Excel file to be converted.
        debug_mode (bool): Flag to enable or disable debug mode. Default is True.

    Returns:
        dict: A JSON-LD dictionary representing the entire structured information derived from the Excel file.

    Raises:
        ValueError: If any required fields in the Excel file are missing or contain invalid data.
    """
    if debug_mode:
        print('*********************************************************')
        print(f"Initialize new session of Excel file conversion, started at {datetime.datetime.now()}")
        print('*********************************************************')
    data_container = ExcelContainer(excel_file) 

    # Generate JSON-LD using the data container
    jsonld_output = create_jsonld_with_conditions(data_container)
    jsonld_output = assit_format_json_rated_capacity(jsonld_output) # Simply comment this line out if assit_format is not prefereed. 
    return jsonld_output
