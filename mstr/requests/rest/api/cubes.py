# -*- coding: utf-8 -*-
# Copyright 2020 Paul Bailey
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from .utils import check_valid_session


class CubesMixin:
    @check_valid_session
    def post_cubes(self, project_id: str, cube_id: str):
        return self.post_cubes("cubes/{}".format(cube_id), project_id=project_id)

    # "Friendly" method aliases

    def publish_cube(self, project_id: str, cube_id: str):
        return self.post_cubes(project_id, cube_id)
