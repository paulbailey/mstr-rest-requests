from .utils import check_valid_session


class CubesMixin:

    @check_valid_session
    def post_cubes(self, project_id, cube_id):
        return self.post_cubes('cubes/{}'.format(cube_id), project_id=project_id)

    # "Friendly" method aliases

    def publish_cube(self, project_id, cube_id):
        return self.post_cubes(project_id, cube_id)
