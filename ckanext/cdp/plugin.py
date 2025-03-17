import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json
import pkg_resources
import codecs
from ckan import model
from ckan.logic.action.create import package_collaborator_create
from ckan.logic.action.delete import package_collaborator_delete


class CdpPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets', 'ckanext-cdp')

        # Add all template directories to Jinja environment.
        for template_directory in config_.get('extra_template_paths', '').split(','):
            if template_directory:
                toolkit.add_template_directory(config_, template_directory)

        # Set the dataset schema to the merged schema file.
        config_['scheming.dataset_schemas'] = 'ckanext.cdp:ckan_dataset_cdp.json'
        config_['ckan.auth.allow_dataset_collaborators'] = 'true'


    # ITemplateHelpers
    def get_helpers(self):
        return {
            # Add any helper functions here
        }

    # IDatasetForm
    def _modify_package_schema(self, schema):
        # Add our custom resource field from cdp_schema.py
        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_validator('ignore_missing'),
                toolkit.get_converter('convert_to_extras')
            ]
        })
        return schema

    def create_package_schema(self):
        schema = super(CdpPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(CdpPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(CdpPlugin, self).show_package_schema()
        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')
            ]
        })
        return schema

    def is_fallback(self):
        return False

    def package_types(self):
        return []

    def get_resource_form(self, package_type=None):
        return 'scheming/package/snippets/resource_form.html'

    def get_package_types(self):
        return []

    # IPackageController
    def after_create(self, context, res_dict):
        user = model.User.get("user2")
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
        user = model.User.get("user2")
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

