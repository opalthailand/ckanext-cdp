# -*- coding: utf-8 -*-
import json
import pkg_resources
import ckan.plugins.toolkit as toolkit
import codecs

def load_original_schema():
    """
    Load the original CKAN dataset schema from the thai_gdc extension.
    This file (ckan_dataset.json) is expected to reside in the thai_gdc package.
    """
    schema_path = pkg_resources.resource_filename('ckanext.thai_gdc', 'ckan_dataset.json')
    with codecs.open(schema_path, encoding='utf-8') as f:
        original_schema = json.load(f)
    return original_schema

def merge_custom_field(schema):
    """
    Merge a custom field into the given schema.
    
    The custom field 'data_cdp' is added to the dataset_fields with:
      - Localized labels (in English and Thai)
      - Predefined choices (yes/no)
      - Custom form and display snippets for CKAN Scheming
      - A list of data types for additional context (if needed)
      - Validators to convert the field to extras and ignore missing values
    """
    custom_field = {
        "field_name": "data_cdp",
        "label": {
            "en": "Send data to CDP",
            "th": "ยินยอมให้ส่งชุดข้อมูลไปใช้ในโครงการ CDP หรือไม่"
        },
        "choices": [
            {"value": "yes", "label": "ใช่"},
            {"value": "no", "label": "ไม่ใช่"}
        ],
        "form_snippet": "data_cdp.html",
        "display_snippet": "select.html",
        "form_data_type": [
            "ข้อมูลระเบียน", 
            "ข้อมูลสถิติ", 
            "ข้อมูลภูมิสารสนเทศเชิงพื้นที่", 
            "ข้อมูลหลากหลายประเภท", 
            "ข้อมูลประเภทอื่นๆ"
        ],
        "validators":  "convert_to_extras ignore_missing"
    }
    if 'dataset_fields' in schema:
        if not any(field.get("field_name") == "data_cdp" for field in schema['dataset_fields']):
            schema['dataset_fields'].append(custom_field)
    else:
        schema['dataset_fields'] = [custom_field]
    return schema

def serialize_schema(data):
    """
    Recursively serialize the schema data.
    
    This function converts dictionaries, lists, callables, and strings to a form
    that is safe to serialize as JSON. Callables are replaced by their name.
    """
    if isinstance(data, dict):
        return {serialize_schema(key): serialize_schema(value) for key, value in data.iteritems()}
    elif isinstance(data, list):
        return [serialize_schema(item) for item in data]
    elif callable(data):
        return data.__name__
    elif isinstance(data, str):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data
    else:
        return data

def save_merged_schema():
    """
    Create the merged schema by:
      - Loading the original schema from the thai_gdc extension.
      - Merging the custom 'data_cdp' field into it.
      - Serializing the merged schema.
      - Saving the result as 'ckan_dataset_cdp.json' in the cdp extension directory.
    
    Returns the merged schema as a Python dictionary.
    """
    original_schema = load_original_schema()
    merged_schema = merge_custom_field(original_schema)
    merged_schema = serialize_schema(merged_schema)
    cdp_schema_path = pkg_resources.resource_filename('ckanext.cdp', 'ckan_dataset_cdp.json')
    with codecs.open(cdp_schema_path, 'w', encoding='utf-8') as f:
        json.dump(merged_schema, f, indent=4, ensure_ascii=False)
    return merged_schema