__version__ = "0.0.1"

import sys

# Self-reference: app name "kya_hr" == module name "KYA HR" (scrubbed: "kya_hr")
# Frappe resolves imports as {app}.{module}.{doctype_type}.{name}.{name}
# → kya_hr.kya_hr.doctype.xxx.xxx / kya_hr.kya_hr.web_form.xxx.xxx
# Without this, Python can't find kya_hr.kya_hr as a subpackage.
sys.modules.setdefault(__name__ + ".kya_hr", sys.modules[__name__])
