<!-- omit in toc -->
# Questionnaire Cloner

A Python-based tool for managing questionnaires between different tenants in the Credo AI system.
Easily download, upload, and transfer questionnaires along with their associated triggers and actions.

---
<!-- omit in toc -->
## 🗂️ Table of Contents
<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [1. Features ✨](#1-features-)
- [2. Requirements 🧰](#2-requirements-)
- [3. Installation ⚙️](#3-installation-️)
- [4. Usage 🚀](#4-usage-)
- [5. Project Structure 🗂️](#5-project-structure-️)
- [6. Contributing 🤝](#6-contributing-)
- [7. Support 📞](#7-support-)
- [8. References 📚](#8-references-)

<!-- TOC end -->

---

<!-- TOC --><a name="1-features-"></a>
## 1. Features ✨

- ***Download*** questionnaires from a source tenant
- ***Upload*** questionnaires to a target tenant
- ***Copy*** questionnaire structure, including:
  - Sections
  - Questions
  - Evidence types
  - Select options
  - Alert triggers
- ***Manage triggers and actions***:
  - Copy triggers between tenants
  - Map and maintain trigger relationships
  - Transfer associated actions
- ***Environment-based configuration***
- ***JWT token management***
- ***Error handling and logging***

---

<!-- TOC --><a name="2-requirements-"></a>
## 2. Requirements 🧰

- Python `3.x`
- Access to the Credo AI API (API tokens required)
- [Required Python packages](requirements.txt)

---

<!-- TOC --><a name="3-installation-"></a>
## 3. Installation ⚙️

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd resource_manager
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:

   Create a `.env` file with the following contents:

    ```dotenv
    OLD_API_TOKEN=your_old_api_token
    OLD_JWT_TOKEN=your_old_jwt_token
    OLD_TENANT=old_tenant_name
    OLD_BASE_PATH=https://api.credo.ai
    OLD_QUESTIONNAIRE_ID=your_questionnaire_id
    OLD_QUESTIONNAIRE_VERSION=version_number

    NEW_API_TOKEN=your_new_api_token
    NEW_JWT_TOKEN=your_new_jwt_token
    NEW_TENANT=new_tenant_name
    NEW_BASE_PATH=https://api.credo.ai
    ```

---

<!-- TOC --><a name="4-usage-"></a>
## 4. Usage 🚀

Run the following to copy **Custom Fields**, **Questionnaires**, **Triggers**, and **Actions**:

```bash
python main.py
```

---

<!-- TOC --><a name="5-project-structure-"></a>
## 5. Project Structure 🗂️

| File | Purpose |
|:---|:---|
| `download_questionnaire.py` | Download questionnaires from source tenant |
| `upload_questionnaire.py` | Upload questionnaires to target tenant |
| `triggers_actions.py` | Copy triggers and actions between tenants |
| `get_bearer_token.py` | Manage JWT token generation and authentication |
| `q_manager_utils.py` | Shared utilities and error handling |
| `write_to_json.py` | JSON file handling utilities |
| `upload_custom_fields.py` | Upload custom fields to target tenant |
| `download_custom_fields.py` | Download custom fields from source tenant |

---

<!-- TOC --><a name="6-contributing-"></a>
## 6. Contributing 🤝

1. Fork the repository
2. Create your feature branch:

    ```bash
    git checkout -b feature/amazing-feature
    ```

3. Commit your changes:

    ```bash
    git commit -m 'Add some amazing feature'
    ```

4. Push to your branch:

    ```bash
    git push origin feature/amazing-feature
    ```

5. Open a Pull Request

---

<!-- TOC --><a name="7-support-"></a>
## 7. Support 📞

For support, contact **support@credo.ai**.

---

<!-- TOC --><a name="8-references-"></a>
## 8. References 📚

- Credo AI API documentation
