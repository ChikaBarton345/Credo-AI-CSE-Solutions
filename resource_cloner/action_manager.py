import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import dotenv_values, load_dotenv
from download_questionnaire import QuestionnaireDownloader
from get_bearer_token import TokenManager
from q_manager_utils import APIError, TriggersActionsError
from upload_questionnaire import QuestionnaireUploader
from utils import JSONData, JSONDict, JSONList

from questionnaire_manager import QuestionnaireManager

class ActionManager:
    def __init__(self, parent: QuestionnaireManager):
        self.parent = parent
        self.em = parent.em
        self.src_headers = parent.src_headers
        self.dest_headers = parent.dest_headers