REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reportInfo": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "reportType": {"type": "string"},
                "date": {"type": "string"},
                "patientInfo": {"type": "string"},
            },
            "required": ["reportType", "date", "patientInfo"],
        },
        "overallSummary": {"type": "string"},
        "keyFindings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "parameter": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                    "referenceRange": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["normal", "high", "low", "abnormal", "unclear"],
                    },
                    "simpleExplanation": {"type": "string"},
                },
                "required": [
                    "parameter", "value", "unit", "referenceRange", "status",
                    "simpleExplanation",
                ],
            },
        },
        "importantObservations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "originalFinding": {"type": "string"},
                    "simpleExplanation": {"type": "string"},
                    "significance": {"type": "string"},
                },
                "required": [
                    "title", "originalFinding", "simpleExplanation", "significance",
                ],
            },
        },
        "medicalTerms": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "term": {"type": "string"},
                    "meaning": {"type": "string"},
                },
                "required": ["term", "meaning"],
            },
        },
        "questionsForDoctor": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "reportInfo", "overallSummary", "keyFindings", "importantObservations",
        "medicalTerms", "questionsForDoctor", "limitations",
    ],
}


def validate_report(payload):
    if not isinstance(payload, dict):
        raise ValueError("The report response must be a JSON object.")

    expected = set(REPORT_SCHEMA["required"])
    if set(payload) != expected:
        raise ValueError("The report response is missing required fields or contains unexpected fields.")

    report_info = payload["reportInfo"]
    if not isinstance(report_info, dict) or set(report_info) != {"reportType", "date", "patientInfo"}:
        raise ValueError("The report information section is malformed.")
    for value in report_info.values():
        _require_string(value)

    _require_string(payload["overallSummary"])
    for list_name in ("keyFindings", "importantObservations", "medicalTerms", "questionsForDoctor", "limitations"):
        if not isinstance(payload[list_name], list) or len(payload[list_name]) > 100:
            raise ValueError(f"The {list_name} section is malformed.")

    for finding in payload["keyFindings"]:
        _require_object_strings(finding, {
            "parameter", "value", "unit", "referenceRange", "status", "simpleExplanation",
        })
        if finding["status"] not in {"normal", "high", "low", "abnormal", "unclear"}:
            raise ValueError("A finding has an unsupported status.")

    for observation in payload["importantObservations"]:
        _require_object_strings(observation, {
            "title", "originalFinding", "simpleExplanation", "significance",
        })
    for term in payload["medicalTerms"]:
        _require_object_strings(term, {"term", "meaning"})
    for question in payload["questionsForDoctor"]:
        _require_string(question)
    for limitation in payload["limitations"]:
        _require_string(limitation)

    return payload


def _require_object_strings(value, required_keys):
    if not isinstance(value, dict) or set(value) != required_keys:
        raise ValueError("A report section contains a malformed item.")
    for item in value.values():
        _require_string(item)


def _require_string(value):
    if not isinstance(value, str) or len(value) > 12_000:
        raise ValueError("A report field must be a string within the supported size.")