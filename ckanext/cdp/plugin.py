# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model # Import model เพื่อใช้หา User

from ckan.types.logic import ActionResult
import ckan.lib.dictization.model_dictize as model_dictize
from ckan.types import Context, DataDict, ErrorDict, Schema
import ckan.logic as logic
import datetime
import logging
from typing import Any
from flask_babel import gettext as flask_ugettext

log = logging.getLogger(__name__)
ValidationError = logic.ValidationError
NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust

def ugettext(*args: Any, **kwargs: Any) -> str:
    return flask_ugettext(*args, **kwargs)

_ = ugettext

def package_collaborator_create_any(
        context: Context,
        data_dict: DataDict) -> ActionResult.PackageCollaboratorCreate:
    '''Allow anyone to make a user a collaborator in a dataset.
    '''

    model = context['model']

    package_id, user_id, capacity = _get_or_bust(
        data_dict,
        ['id', 'user_id', 'capacity']
    )

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Dataset not found'))

    user = model.User.get(user_id)
    if not user:
        raise NotFound(_('User not found'))

    # Check if collaborator already exists
    collaborator = model.Session.query(model.PackageMember). \
        filter(model.PackageMember.package_id == package.id). \
        filter(model.PackageMember.user_id == user.id).one_or_none()
    if not collaborator:
        collaborator = model.PackageMember(
            package_id=package.id,
            user_id=user.id)
    collaborator.capacity = capacity
    collaborator.modified = datetime.datetime.utcnow()
    model.Session.add(collaborator)
    model.repo.commit()

    log.info('User {} added as collaborator in package {} ({})'.format(
        user.name, package.id, capacity))

    return model_dictize.member_dictize(collaborator, context)


def package_collaborator_delete_any(context: Context, data_dict: DataDict) -> ActionResult.PackageCollaboratorDelete:
    '''Allow anoy to remove a collaborator from a dataset.
    '''

    model = context['model']

    package_id, user_id = _get_or_bust(
        data_dict,
        ['id', 'user_id']
    )

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Package not found'))

    user = model.User.get(user_id)
    if not user:
        raise NotFound(_('User not found'))

    collaborator = model.Session.query(model.PackageMember).\
        filter(model.PackageMember.package_id == package.id).\
        filter(model.PackageMember.user_id == user.id).one_or_none()
    if not collaborator:
        raise NotFound(
            'User {} is not a collaborator on this package'.format(user_id))

    model.Session.delete(collaborator)
    model.repo.commit()

    log.info('User {} removed as collaborator from package {}'.format(
        user_id, package.id))
    

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

    # --- Implement methods ของ IDatasetForm ---
    # เราต้อง override method เหล่านี้เพื่อเรียก _modify_package_schema
    # และเพื่อให้แน่ใจว่า scheming ใช้ schema ที่ถูกต้อง

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
        # เรียก action เพื่อเพิ่ม collaborator เข้าไปใน dataset; ผลลัพธ์จะถูกเก็บใน result_create
        result_create = package_collaborator_create_any(context.copy(), data_create)

        # ตรวจสอบว่าค่า res_dict.get('data_cdp') ไม่ใช่ 'yes'
        if res_dict.get('data_cdp') != 'yes':
            # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_delete
            data_delete = {
                'id': package_id,      # ID ของ dataset ที่จะลบ collaborator ออก
                'user_id': user_id     # ID ของ user ที่จะถูกลบออกจากการเป็น collaborator
            }
            # เรียก action เพื่อลบ collaborator ออกจาก dataset; ผลลัพธ์จะถูกเก็บใน result_delete
            result_delete = package_collaborator_delete_any(context.copy(), data_delete)

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
        # เรียก action เพื่อเพิ่ม collaborator เข้าไปใน dataset; ผลลัพธ์จะถูกเก็บใน result_create
        result_create = package_collaborator_create_any(context, data_create)

        # ตรวจสอบว่าค่า pkg_dict.get('data_cdp') ไม่ใช่ 'yes'
        if pkg_dict.get('data_cdp') != 'yes':
            # เตรียมข้อมูล dictionary สำหรับใช้กับ action package_collaborator_delete
            data_delete = {
                'id': package_id,      # ID ของ dataset ที่จะลบ collaborator ออก
                'user_id': user_id     # ID ของ user ที่จะถูกลบออกจากการเป็น collaborator
            }
            # เรียก action เพื่อลบ collaborator ออกจาก dataset; ผลลัพธ์จะถูกเก็บใน result_delete
            result_delete = package_collaborator_delete_any(context, data_delete)

        # คืนค่า dictionary ข้อมูล dataset ที่อัปเดตแล้วกลับไป
        return pkg_dict