# Report Schema

TRUSTTRACE CV generates assurance reports as standard JSON.

## Root Object

| Field | Type | Description |
|---|---|---|
| `report_id` | string (UUID) | Unique identifier for the report |
| `timestamp` | string (ISO-8601) | Time of report generation |
| `target_name` | string | Name of the audited project or artifact bundle |
| `verdict` | string | Overall status: `PASS`, `ANOMALIES_DETECTED`, `FAIL`, `INCONCLUSIVE` |
| `severity_summary` | object | Counts of findings mapped to `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` |
| `coverage` | object | Statement of implemented checks and known limitations |
| `findings` | array | List of all individual findings (see Finding Object) |

## Finding Object

| Field | Type | Description |
|---|---|---|
| `check_id` | string | Unique security check code (e.g., `SEC-DS-001`) |
| `name` | string | Human-readable check name |
| `result` | string | Status: `PASS`, `ANOMALIES_DETECTED`, `FAIL`, `NOT_ASSESSED` |
| `severity` | string | `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `confidence` | string | `LOW`, `MEDIUM`, `HIGH`, `N/A` |
| `description` | string | Detailed explanation of what was checked |
| `evidence` | object | Extracted metadata or proof supporting the result |
| `recommended_action` | string | Suggested remediation steps for the analyst |
| `limitation` | string | Known edge cases or false positive risks for this check |

*(This structure is validated implicitly in `tests/test_report.py::TestGenerateReport`)*
