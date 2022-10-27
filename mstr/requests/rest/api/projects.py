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


class ProjectsMixin:
    @check_valid_session
    def get_projects(self):
        response = self.get("projects").json()
        return response

    def load_projects(self):
        response = self.get_projects()
        projects_by_name = dict()
        projects_by_id = dict()
        for project in response:
            projects_by_name[project["name"]] = project["id"]
            projects_by_id[project["id"]] = project["name"]
        self.projects_by_name = projects_by_name
        self.projects_by_id = projects_by_id

    def get_project_id(self, project_name):
        return self.projects_by_name.get(project_name, None)
