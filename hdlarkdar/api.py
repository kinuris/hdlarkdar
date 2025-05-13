import frappe
import json

@frappe.whitelist()
def sync_deals():
    request_body = frappe.request.data

    if not request_body:
        frappe.response.status_code = 400
        frappe.response.message = "Request body is empty"
        return
    try:
        json_data = json.loads(request_body)
    except Exception as e:
        frappe.response.status_code = 400
        frappe.response.message = f"Invalid JSON: {e}"
        return

    if not isinstance(json_data, dict):
        frappe.response.status_code = 400
        frappe.response.message = "Request data must be a JSON object."
        return

    created_count = 0
    updated_count = 0

    for item in json_data.get("items", []):
        fields = item.get("fields", {})

        if not fields:
            continue

        record_id = fields.get("Record ID | Deals") 

        # Sanitize the Deal Name 
        fields["HDDealName"] = fields.get("HDDealName").replace("<", "←").replace(">", "→")[:140]

        try:
            if frappe.db.exists("Servio Registry Deal", {"record_id": record_id}):
                doc = frappe.get_doc("Servio Registry Deal", {"record_id": record_id})
                updated_count += 1
            else:
                duplicate = frappe.db.exists("Servio Registry Deal", {"deal_name": fields.get("HDDealName")})
                if duplicate:
                    continue

                doc = frappe.new_doc('Servio Registry Deal')
                doc.record_id = record_id
                created_count += 1
            
            doc.company = fields.get("Company")
            doc.status = fields.get("Status")
            doc.deal_name = fields.get("HDDealName")

            doc.save(ignore_permissions=True)

            if doc.name != doc.deal_name:
                frappe.rename_doc("Servio Registry Deal", doc.name, doc.deal_name)

        except Exception as e:
            frappe.log_error(f"Error processing record_id {record_id}: {e}", "HDLarkDar Sync Error")

    frappe.db.commit()

    return {
        "created": created_count,
        "updated": updated_count
    }