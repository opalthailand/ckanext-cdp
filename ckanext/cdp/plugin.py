# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
# *** เพิ่ม import สำหรับ actions ที่จำเป็น ***
from ckan import model # Import model เพื่อใช้หา User
from ckan.logic.action.create import package_collaborator_create
from ckan.logic.action.delete import package_collaborator_delete


def custom_package_collaborator_create(context, data_dict):
    """
    Custom authorization function for package_collaborator_create.
    Now allows any logged-in user to add a collaborator.
    Additionally, we set 'ignore_auth' in the context so that the package
    can be read without triggering standard permission checks.
    """
    user = context.get('user')
    if not user:
        raise toolkit.NotAuthorized("User not logged in.")
    # Copy the context and set ignore_auth to True to bypass package read authorization
    new_context = context.copy()
    new_context['ignore_auth'] = True
    return package_collaborator_create(new_context, data_dict)

class CdpPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    # เพิ่ม implements IDatasetForm
    plugins.implements(plugins.IDatasetForm)
    # เพิ่ม implements IPackageController
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic','cdp')

        # เพิ่มบรรทัดนี้เพื่อเปิดใช้งาน Collaborators
        config_['ckan.auth.allow_dataset_collaborators'] = 'true'
        # ตั้งค่าให้ Scheming ใช้ dataset schema ใหม่ที่ merge แล้ว
        config_['scheming.dataset_schemas'] = 'ckanext.cdp:ckan_dataset_cdp.json'

    # IDatasetForm implementation helper function
    def _modify_package_schema(self, schema):
        """
        ปรับเปลี่ยน dataset form schema โดยเพิ่มกฎ validation/conversion
        สำหรับฟิลด์ 'data_cdp' ที่เรากำหนดเอง
        """
        # ตรวจสอบว่า dataset_fields มีอยู่จริงก่อน update
        if 'dataset_fields' not in schema:
             schema['dataset_fields'] = {} # สร้าง dict ว่างถ้ายังไม่มี

        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_validator('ignore_missing'), # ไม่บังคับกรอก
                toolkit.get_converter('convert_to_extras') # แปลงไปเก็บใน extras field
            ]
        })
        return schema
    
    # IAuthFunctions implementation: override package_collaborator_create
    def get_auth_functions(self):
        return {
            'package_collaborator_create': custom_package_collaborator_create,
        }

    # Implement methods ของ IDatasetForm 
    def create_package_schema(self):
        """
        Override schema ที่ใช้ตอนสร้าง dataset
        """
        schema = super(CdpPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        """
        Override schema ที่ใช้ตอนแก้ไข dataset
        """
        schema = super(CdpPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        """
        Override schema ที่ใช้ตอนแสดงผล dataset
        ต้องแปลงค่าจาก extras กลับมาแสดง
        """
        schema = super(CdpPlugin, self).show_package_schema()
        schema['dataset_fields'].update({
            'data_cdp': [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')
            ]
        })
        return schema

    # --- Methods อื่นๆ ของ IDatasetForm ---
    def is_fallback(self):
        """
        ระบุว่า plugin นี้ไม่ใช่ fallback สำหรับ dataset type ใดๆ
        """
        # ต้อง return False เพื่อให้ scheming ทำงานกับ type 'dataset' ปกติ
        return False

    def package_types(self):
        """
        ระบุ dataset types ที่ plugin นี้จะทำงานด้วย
        ถ้า return list ว่าง หมายถึงทำงานกับทุก type ที่ scheming จัดการ
        """
        # ให้ scheming จัดการ type ตาม schema ที่เรากำหนด
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
        as an editor collaborator to the dataset.
        """
        # ดึงข้อมูล user object จากชื่อ 'cdp_user' และดึง package ID จาก dictionary ผลลัพธ์ของการสร้าง dataset
        user = model.User.get("cdp_user")
        user_id = user.id
        package_id = res_dict.get('id')

        # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_create
        data_create = {
            'id': package_id,      # ID ของ dataset ที่จะเพิ่ม collaborator
            'user_id': user_id,    # ID ของ user ที่จะเพิ่มเป็น collaborator
            'capacity': 'editor'   # ระดับสิทธิ์ของ collaborator
        }

        # Add collaborator using our custom auth function above
        custom_package_collaborator_create(context.copy(), data_create)
                
        # เรียก action เพื่อเพิ่ม collaborator เข้าไปใน dataset; ผลลัพธ์จะถูกเก็บใน result_create
        result_create = package_collaborator_create(context.copy(), data_create)

        # ตรวจสอบว่าค่า res_dict.get('data_cdp') ไม่ใช่ 'yes'
        if res_dict.get('data_cdp') != 'yes':
            # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_delete
            data_delete = {
                'id': package_id,      # ID ของ dataset ที่จะลบ collaborator ออก
                'user_id': user_id     # ID ของ user ที่จะถูกลบออกจากการเป็น collaborator
            }
            # เรียก action เพื่อลบ collaborator ออกจาก dataset; ผลลัพธ์จะถูกเก็บใน result_delete
            result_delete = package_collaborator_delete(context.copy(), data_delete)

        # คืนค่า dictionary ผลลัพธ์ของการสร้าง dataset กลับไป
        return res_dict

    def after_update(self, context, pkg_dict):
        """
        Callback executed after a dataset is updated.

        Similar to after_create, it checks the 'data_cdp' field and adds or removes
        user 'cdp_user' as a collaborator accordingly.
        """
        # ดึงข้อมูล user object จากชื่อ 'cdp_user' และดึง package ID จาก dictionary ผลลัพธ์ของการสร้าง dataset
        user = model.User.get("cdp_user")
        user_id = user.id
        package_id = pkg_dict.get('id')

        # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_create
        data_create = {
            'id': package_id,      # ID ของ dataset ที่จะเพิ่ม collaborator
            'user_id': user_id,    # ID ของ user ที่จะเพิ่มเป็น collaborator
            'capacity': 'editor'   # ระดับสิทธิ์ของ collaborator
        }

        # Add collaborator using our custom auth function above
        custom_package_collaborator_create(context.copy(), data_create)

        # เรียก action เพื่อเพิ่ม collaborator เข้าไปใน dataset; ผลลัพธ์จะถูกเก็บใน result_create
        result_create = package_collaborator_create(context, data_create)

        # ตรวจสอบว่าค่า pkg_dict.get('data_cdp') ไม่ใช่ 'yes'
        if pkg_dict.get('data_cdp') != 'yes':
            # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_delete
            data_delete = {
                'id': package_id,      # ID ของ dataset ที่จะลบ collaborator ออก
                'user_id': user_id     # ID ของ user ที่จะถูกลบออกจากการเป็น collaborator
            }
            # เรียก action เพื่อลบ collaborator ออกจาก dataset; ผลลัพธ์จะถูกเก็บใน result_delete
            result_delete = package_collaborator_delete(context, data_delete)

        # คืนค่า dictionary ข้อมูล dataset ที่อัปเดตแล้วกลับไป
        return pkg_dict