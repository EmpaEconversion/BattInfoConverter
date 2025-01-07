"""
This module handle the interface of the web app. 
"""
import streamlit as st
import json
import os
from io import BytesIO
import json_convert as js_conv 


markdown_content = """ 
BattINFO converter helps you ontologize the metadata of your coin cell batteries based on the [BattINFO ontology](https://github.com/BIG-MAP/BattINFO).
Ontologizing your metadata significantly enhances the interoperability of your data across various digital platforms and research groups.
To learn more about ontologizing your metadata, we invite you to visit our page on [ontologizing metadata](https://github.com/ord-premise/interoperability-guidelines/tree/main).
While there are many benefits of this process, it can be a daunting task in practice. With this in mind,
we developed the open-source [BattINFO converter](https://github.com/EmpaEconversion/BattInfoConverter) web application designed to streamline and expedite this intricate task, making it more manageable for you and your team.  

BattINFO converter converts an Excel file collecting the metadata of a coin cell battery from the user into a fully ontologized JSON-LD file,
which can be published as supporting information with your scientific publication or in open-access data repositories such as [Zenodo](https://zenodo.org).
Example Excel metadata files for a coin cell battery are provided. We plan to add more Excel metadata files for other cell types in the future. 
For additional infor-mation on how to fill the Excel file, please click the respective link on the left.  

BattINFO converter web application was developed by Dr. Nukorn Plainpan and Prof. Dr. Corsin Battaglia at [Empa](https://www.empa.ch/), the Swiss Federal Laboratories
for Materials Science and Technology in the Laboratory [Materials for Energy Conversion](https://www.empa.ch/web/s501). We acknowledge stimulating discussions and support from
Dr. Simon Clark, SINTEF. BattINFO converter also  acknowledges support from the European Union’s Horizon research and innovation program under
grant agreements No. 957189 ([BIG-MAP](https://www.big-map.eu/) project), No. 957213 ([Battery2030+](https://battery2030.eu/) coordination and support action 2),
and No. 101104022 ([Battery2030+](https://battery2030.eu/) coordination and support action 3), 
the Swiss State Sec-retariat for Education, Research, and Innovation, 
and the Open Research Data program of the ETH Board (project [PREMISE](https://ord-premise.org/), Open and Reproducible Materials Science Research). 

"""

image_url = 'https://raw.githubusercontent.com/NukP/xls_convert/fix_oslo2/BattInfoCOnverter.png'

def main():
    st.image(image_url)
    
    st.markdown(f"__App Version: {js_conv.APP_VERSION}__")
    
    uploaded_file = st.file_uploader("__Upload your metadata Excel file here__", type=['xlsx', 'xlsm'])
    
    if uploaded_file is not None:
        # Extract the base name of the file (without the extension)
        base_name = os.path.splitext(uploaded_file.name)[0]
        
        # Convert the uploaded Excel file to JSON-LD
        jsonld_output = js_conv.convert_excel_to_jsonld(uploaded_file)
        jsonld_str = json.dumps(jsonld_output, indent=4)

        # Download button
        to_download = BytesIO(jsonld_str.encode())
        output_file_name = f"BattINFO_converter_{base_name}.json"  
        st.download_button(label="Download JSON-LD",
                        data=to_download,
                        file_name=output_file_name,
                        mime="application/json")
        
        # Convert JSON-LD output to a string to display in text area (for preview)
        st.text_area("JSON-LD Output", jsonld_str, height=1000)
    
    st.markdown(markdown_content, unsafe_allow_html=True)
    st.image('https://raw.githubusercontent.com/NukP/xls_convert/fix_oslo2/sponsor.png', width=700)

if __name__ == "__main__":
    main()

