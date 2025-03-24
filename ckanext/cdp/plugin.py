import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json
import pkg_resources
import codecs
from ckan import model
from ckan.logic.action.create import package_collaborator_create
from ckan.logic.action.delete import package_collaborator_delete

class CdpPlugin(plugins.SingletonPlugin):
    """
    A CKAN extension plugin that:
      - Configures custom templates and assets.
      - Sets a merged dataset schema which includes a custom field 'data_cdp'.
      - Modifies dataset creation/update behavior to add or remove a collaborator 
        (user 'cdp_user') based on the value of the 'data_cdp' field.
    """
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer implementation
    def update_config(self, config_):
        """
        Update CKAN configuration by:
          - Adding template, public, and asset directories.
          - Including extra template directories if provided.
          - Setting the scheming dataset schema to the merged schema file.
          - Allowing dataset collaborators.
        """
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets', 'ckanext-cdp')

        # Add all template directories from the config's extra_template_paths.
        for template_directory in config_.get('extra_template_paths', '').split(','):
            if template_directory:
                toolkit.add_template_directory(config_, template_directory)

        # Set the dataset schema to the merged schema file.
        config_['scheming.dataset_schemas'] = 'ckanext.cdp:ckan_dataset_cdp.json'
        config_['ckan.auth.allow_dataset_collaborators'] = 'true'

    # ITemplateHelpers implementation
    def get_helpers(self):
        """
        Return a dictionary of custom helper functions for use in templates.
        Currently, no additional helpers are provided.
        """
        return {
            # Add any helper functions here if needed.
        }

    # IDatasetForm implementation helper function
    def _modify_package_schema(self, schema):
        """
        Modify the dataset form schema by adding validation and conversion
        rules for the custom 'data_cdp' field.
        """
        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_validator('ignore_missing'),
                toolkit.get_converter('convert_to_extras')
            ]
        })
        return schema

    def create_package_schema(self):
        """
        Override the default package schema used during dataset creation.
        Calls the parent method and then applies modifications.
        """
        schema = super(CdpPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        """
        Override the default package schema used during dataset updates.
        Calls the parent method and then applies modifications.
        """
        schema = super(CdpPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        """
        Override the package schema used when displaying a dataset.
        Modifies the schema to convert data from extras and ignore missing values.
        """
        schema = super(CdpPlugin, self).show_package_schema()
        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')
            ]
        })
        return schema

    def is_fallback(self):
        """
        Indicate that this plugin is not a fallback for any dataset type.
        """
        return False

    def package_types(self):
        """
        Return a list of dataset types this plugin is applicable to.
        An empty list means it applies to all types.
        """
        return []

    def get_resource_form(self, package_type=None):
        """
        Return the resource form snippet path to be used for resource editing.
        """
        return 'scheming/package/snippets/resource_form.html'

    def get_package_types(self):
        """
        Return a list of package types that this plugin supports.
        """
        return []

    # IPackageController implementation
    def after_create(self, context, res_dict):
        """
        Callback executed after a dataset is created.
        
        If the custom field 'data_cdp' is set to 'yes', this function adds user 'cdp_user'
        as an editor collaborator to the dataset. If the field is 'no', it removes the collaborator.
        """
        user = model.User.get("cdp_user")
        user_id = user.id
        package_id = res_dict.get('id')

        if res_dict.get('data_cdp') == 'yes':
            data = {
                'id': package_id,
                'user_id': user_id,
                'capacity': 'editor'
            }
            result = package_collaborator_create(context, data)
        elif res_dict.get('data_cdp') == 'no':
            data = {
                'id': package_id,
                'user_id': user_id
            }
            result = package_collaborator_delete(context, data)
        
        return res_dict

    def after_update(self, context, pkg_dict):
        """
        Callback executed after a dataset is updated.
        
        Similar to after_create, it checks the 'data_cdp' field and adds or removes
        user 'cdp_user' as a collaborator accordingly.
        """
        user = model.User.get("cdp_user")
        user_id = user.id
        package_id = pkg_dict.get('id')

        if pkg_dict.get('data_cdp') == 'yes':
            data = {
                'id': package_id, 
                'user_id': user_id,
                'capacity': 'editor'
            }
            result = package_collaborator_create(context, data)
        elif pkg_dict.get('data_cdp') == 'no':
            data = {
                'id': package_id,
                'user_id': user_id
            }
            result = package_collaborator_delete(context, data)
        
        return pkg_dict