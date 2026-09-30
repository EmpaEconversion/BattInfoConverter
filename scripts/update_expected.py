"""Script to update xlsx and json in test folder based on templates.

Scan src/battinfoconverter_backend/templates for template files, converts to
xlsx and jsonld at test/data.
"""

import json
from pathlib import Path

from battinfoconverter_backend import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    dict_to_workbook,
    workbook_to_dict,
    xlsx_to_dict,
)

for template in Path("src/battinfoconverter_backend/templates").glob("*.json"):
    excel_path = Path(f"test/data/{template.stem}_excel_schema.xlsx")
    output_path = Path(f"test/data/{template.stem}_jsonld_result.json")

    data = json.loads(template.read_text(encoding="utf-8"))
    workbook = dict_to_workbook(data)
    unchanged = excel_path.exists() and workbook_to_dict(workbook) == xlsx_to_dict(excel_path)
    if unchanged:
        # Don't write file - would still change metadata and create diff
        print(f"{template.stem}: xlsx unchanged")
    else:
        workbook.save(excel_path)
        print(f"{template.stem}: xlsx updated")

    res = convert_excel_to_jsonld(excel_path)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)
