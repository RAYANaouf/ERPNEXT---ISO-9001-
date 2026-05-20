import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_to_date

class SystemBrainInstruction(Document):
    pass

def execute_cron_jobs():
    """
    Fonction appelée par le Scheduler.
    Vérifie la période de l'instruction avant de créer un rapport.
    """
    # 1. On récupère les instructions actives avec leur période
    instructions = frappe.get_all(
        "System Brain Instruction",
        filters={"cron_job": 1},
        fields=["name", "instruction", "period", "period_type"]
    )

    for ins in instructions:
        # 2. On cherche le TOUT DERNIER rapport créé pour cette instruction
        last_report = frappe.get_all(
            "System Brain Instruction Report",
            filters={"system_brain_instruction": ins["name"]},
            fields=["creation"],
            order_by="creation desc",
            limit=1
        )

        should_execute = False

        if not last_report:
            # S'il n'y a jamais eu de rapport pour cette instruction, on l'exécute !
            should_execute = True
        else:
            # 3. CALCUL DU TEMPS : On récupère la date de création du dernier rapport
            dernier_rapport_date = last_report[0]["creation"]
            
            # On traduit le "Period Type" d'ERPNext pour Python (Hour -> hours, Day -> days, etc.)
            unit_mapping = {
                "Hour": "hours",
                "Day": "days",
                "Week": "weeks",
                "Month": "months"
            }
            
            unit = unit_mapping.get(ins["period_type"], "days")
            kwargs = {unit: frappe.utils.cint(ins["period"])}
            
            # Date théorique de la prochaine exécution = Date dernier rapport + Période
            prochaine_execution = add_to_date(dernier_rapport_date, **kwargs)

            # Si l'heure actuelle du serveur a dépassé la date théorique, on valide l'exécution
            if now_datetime() >= prochaine_execution:
                should_execute = True

        # 4. Création du rapport uniquement si le temps est écoulé
        if should_execute:
            texte_preuve = f"--- CONTROLE DE ROUTINE ---\nDate : {now_datetime().strftime('%d-%m-%Y %H:%M')}\nConsigne : {ins['instruction']}"
            
            frappe.get_doc({
                "doctype": "System Brain Instruction Report",
                "system_brain_instruction": ins["name"],
                "report": texte_preuve
            }).insert(ignore_permissions=True)
            
            frappe.db.commit()
            frappe.logger().info(f"Scheduler : Nouveau rapport généré pour {ins['name']}")