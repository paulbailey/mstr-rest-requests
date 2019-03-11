from .utils import check_valid_session


class ObjectTypes:
    REPORT = 3
    FOLDER = 8


class Object:
    def __init__(self, response):
        obj_json = response.json()

        ancestors = obj_json.get('ancestors', [])
        self.name = obj_json.get('name', 'NAME N/A')

        path_list = sorted(ancestors, key=lambda x: x['level'], reverse=True)
        self.path = '/'.join(list(map(lambda x: x['name'], path_list)))

    def full_name(self):
        return '{}/{}'.format(self.path, self.name)


class ObjectsMixin:

    @check_valid_session
    def get_objects(self, project_id, object_id, object_type=ObjectTypes.REPORT):
        return self.get('objects/{}?type={}'.format(object_id, object_type), project_id=project_id)

    # "Friendly" method aliases
    def get_object_metadata(self, project_id, object_id, object_type):
        return self.get_object_metadata(project_id, object_id, object_type)

    def get_object_details(self, project_id, object_id, object_type):
        obj_json = self.get_objects(project_id, object_id, object_type).json()

        ancestors = obj_json.get('ancestors', [])
        name = obj_json.get('name', 'NAME N/A')

        path_list = sorted(ancestors, key=lambda x: x['level'], reverse=True)
        path = '/'.join(list(map(lambda x: x['name'], path_list)))

        return {
            'name': name,
            'path': path,
            'full': '{}/{}'.format(path, name)
        }
