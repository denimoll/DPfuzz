"""Generate fuzzing reports in various formats."""
import copy
import json
import os

from docxtpl import DocxTemplate


def create_report(report, report_format):
    """
    Save a report dict to the 'report/' directory.
    Supported formats: 'json', 'docx', 'txt'.
    """
    report_dir = "report"
    os.makedirs(report_dir, exist_ok=True)

    if report_format == "json":
        with open(os.path.join(report_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

    elif report_format == "docx":
        report_copy = copy.deepcopy(report)
        for key in list(report.keys()):
            report_copy[key.lower().replace(" ", "_")] = report[key]
        doc = DocxTemplate("template.docx")
        doc.render(report_copy)
        doc.save(os.path.join(report_dir, "report.docx"))

    elif report_format == "txt":
        errors = report.get("Errors", [])
        with open(os.path.join(report_dir, "report.txt"), "w", encoding="utf-8") as f:
            f.write("Result of fuzzing:\n")
            for key, value in report.items():
                if key != "Errors":
                    f.write("%s : %s\n" % (key, value))
            f.write("\nErrors:\n")
            for num, item in enumerate(errors):
                f.write("#%s\n" % num)
                for pair in item.items():
                    f.write("%s\n" % str(pair))

    return True
