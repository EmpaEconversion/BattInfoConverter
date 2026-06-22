"""Script to update xlsx and json in test folder based on templates.

Running this script will scan src/battinfoconverter_backend/templates for
template files, convert to xlsx and jsonld at test/data.

Read and check that the results are sensible before committing.
"""

import json
from pathlib import Path

from battinfoconverter_backend import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import json_to_xlsx

for template in Path("src/battinfoconverter_backend/templates").glob("*.json"):
    print(f"Converting {template}")
    excel_path = Path(f"test/data/{template.stem}_excel_schema.xlsx")
    output_path = Path(f"test/data/{template.stem}_jsonld_result.json")

    json_to_xlsx(
        template,
        excel_path,
    )
    res = convert_excel_to_jsonld(
        excel_path,
    )
    with output_path.open("w") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)
