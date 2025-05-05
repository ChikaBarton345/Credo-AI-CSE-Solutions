from pathlib import Path

from custom_fields_manager import CustomFieldsManager
from env_manager import EnvManager
from questionnaire_manager import QuestionnaireManager
from trigger_manager import TriggerManager
from utils import export_to_json, setup_logger

LOGGER = setup_logger(Path(__file__).stem)


def main():
    """Orchestrate migration of custom fields, questionnaires, triggers, and actions."""

    # Step 1: Upload custom fields from source tenant to destination tenant.
    em = EnvManager()
    LOGGER.info(f"[DATA MIGRATION START] {em.src.tenant} -> {em.dest.tenant}")
    cfm = CustomFieldsManager(em)
    custom_fields = cfm.get_custom_fields()
    export_to_json(custom_fields, "src-custom-fields.json")
    upload_stats = cfm.upload_custom_fields(custom_fields)
    export_to_json(upload_stats, "custom-field-upload-stats.json")

    # Step 2: Upload questionnaire from source tenant to destination tenant.
    qm = QuestionnaireManager(em)
    questionnaire = qm.get_qnaire()
    qattrs = questionnaire.get("data", {}).get("attributes", {})
    qid = qattrs.get("key")
    qver = qattrs.get("version")
    export_to_json(questionnaire, f"src-questionnaire-id-{qid}-ver-{qver}.json")
    q_copy_result = qm.upload_qnaire_copy(questionnaire)
    export_to_json(q_copy_result, "questionnaire-copy-result.json")

    # Step 3: Copy source triggers and actions to the destination tenant.
    tm = TriggerManager(em, q_copy_result)
    triggers = tm.get_triggers()
    trigger_mapping, all_old_triggers = tm.create_triggers(triggers)
    actions = tm.actions.get_actions()
    created_actions = tm.actions.create_actions(
        actions, trigger_mapping, all_old_triggers
    )
    LOGGER.info(
        f"[DATA MIGRATION END] {len(trigger_mapping)} triggers and"
        f" {len(created_actions)} actions created."
    )


if __name__ == "__main__":
    main()
