<!-- omit in toc -->
# Resource Cloner

A Python-based tool for managing questionnaires between different tenants in the Credo AI system.
Easily download, upload, and transfer questionnaires along with their associated triggers and actions.

---

<!-- omit in toc -->
## 🗂️ Table of Contents

[TOC]

---

## 1. Features ✨

- ***Download*** questionnaires from a source tenant.
- ***Upload*** questionnaires to a target tenant.
- ***Copy*** questionnaire structure, including:
  - Sections
  - Questions
  - Evidence types
  - Select options
  - Alert triggers
- ***Manage triggers and actions***. You can:
  - Copy triggers between tenants.
  - Map and maintain trigger relationships.
  - Transfer associated actions.
- ***Secure*** credentials stored in a ***.env*** file.
- ***JWT token management***.
- ***Logging*** and error handling.

---

## 2. Requirements 🧰

- Python `3.9.x`
- Access to the Credo AI API (API tokens required)
- [Required Python packages](requirements.txt)

---

## 3. Installation ⚙️

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd resource_cloner
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:

   Create a `.env` file by filling out the `.env.template`. Please take careful note of the base paths and not only just tenant names.

    ```dotenv
    SRC_API_TOKEN=SOURCE_TENANT_API_KEY
    SRC_JWT_TOKEN=SOURCE_TENANT_JWT
    SRC_TENANT=credoaics
    SRC_BASE_PATH=https://api.credo.ai
    SRC_QUESTIONNAIRE_ID=DEFAULT
    SRC_QUESTIONNAIRE_VERSION=2

    DEST_API_TOKEN=DEST_TENANT_API_TOKEN
    DEST_JWT_TOKEN=DEST_TENANT_JWT
    DEST_TENANT=credoai
    DEST_BASE_PATH=https://api.credo-qa.com
    ```

---

## 4. Usage 🚀

***To copy Custom Fields, Questionnaires, Triggers, and Actions***, run:

```bash
python resource_cloner.py
```

---

## 5. Project Structure 🗂️

| File | Purpose |
|:---|:---|
| `env_manager.py` | Manage JWT token generation and authentication. |
| `custom_field_manager.py` | Down/upload custom fields. |
| `questionnaire_manager.py` | Down/upload questionnaires. |
| `trigger_manager.py` | Copy triggers (and assoc. actions) between tenants. |
| `utils.py` | Useful utilities |
| `logging_config.py` | Set central logging config. |

---

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

## 7. Support 📞

For support, contact **support@credo.ai**.

---

## 8. References 📚

- Credo AI API documentation
