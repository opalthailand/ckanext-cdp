# ckanext-cdp

**ckanext-cdp** is a CKAN extension that adds a custom dataset field called **data_cdp**. This field allows users to indicate whether they consent to send their dataset to a CDP (Collaborative Data Platform) project. Based on the user’s selection, the extension automatically manages dataset collaborator privileges for a predefined user (user "`cdp_user`") by either granting editor rights or removing them.

## Requirements

This extension is designed and tested for **CKAN 2.9**.

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
| ------------ | ----------- |
| 2.9          | yes         |

## Installation

To install **ckanext-cdp**, follow these steps:

1. **Activate your CKAN Virtual Environment:**

   ```bash
   source /usr/lib/ckan/default/bin/activate
   ```

2. **Navigate to the CKAN Base Directory:**

   ```bash
   cd /usr/lib/ckan/default
   ```

3. **Install the Extension:**

   ```bash
   pip install -e 'git+https://github.com/opalthailand/ckanext-cdp.git#egg=ckanext-cdp'
   ```

4. **Configure CKAN:**

   Open the CKAN configuration file to enable the plugin:

   ```bash
   sudo vi /etc/ckan/default/ckan.ini
   ```

   Locate the `ckan.plugins` setting and add `cdp` right after `thai_gdc` to the list. For example:

   ```
   ckan.plugins = ... thai_gdc cdp ...
   ```

5. **Restart CKAN:**

   If CKAN is deployed on Ubuntu, reload the service:

   ```bash
   sudo supervisorctl reload
   ```

## Usage

Once installed and configured, the extension adds a new field called `data_cdp` to your CKAN datasets. Users can select whether they consent to send their dataset to a CDP project. Based on the selection, the extension will automatically grant or revoke editor privileges for a predefined user (`cdp_user`), ensuring that collaborator rights are managed seamlessly.
