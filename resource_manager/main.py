
# from upload_questionnaires import QuestionnaireManager
from upload_custom_fields import CustomFieldsUploader
from triggers_actions import TriggersAndActions
from download_questionnaire import Questionnaire as Questionnaire_download
from upload_questionnaire import Questionnaire as Questionnaire_upload

def main():
    # Main function to orchestrate the migration of custom fields and triggers/actions
    # from the old tenant to the new tenant. This includes:
    # 1. Uploading custom fields from old tenant to new tenant
    # 2. Creating triggers and actions in the new tenant
    custom_fields_uploader = CustomFieldsUploader()
    custom_fields_uploader.run()

    old_questionnaire= Questionnaire_download()
    original_questionnaire = old_questionnaire.get_questionnaire()  

    questionnaire_upload = Questionnaire_upload()
    questionnaires = questionnaire_upload.run() 
    
    triggers_and_actions = TriggersAndActions(original_questionnaire, questionnaires)
    triggers_and_actions.run()

if __name__ == "__main__":
    main()