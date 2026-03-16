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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from mstr.requests.rest.exceptions import SessionException

from .utils import check_valid_session

if TYPE_CHECKING:
    from mstr.requests.rest.protocols import MSTRSessionProtocol


class ProjectsMixin:
    """Mixin providing MicroStrategy project-related helpers."""

    @check_valid_session
    def get_projects(self: MSTRSessionProtocol) -> list[dict[str, Any]]:
        """Fetch the list of projects via ``GET /projects``.

        Returns:
            A list of project dicts as returned by the REST API.
        """
        response = self.get("projects").json()
        return cast(list[dict[str, Any]], response)

    def load_projects(self) -> None:
        """Fetch projects and populate :attr:`projects_by_name` / :attr:`projects_by_id` look-ups.

        After calling this method you can resolve project names to IDs
        with :meth:`get_project_id`.
        """
        response = self.get_projects()
        projects_by_name = dict()
        projects_by_id = dict()
        for project in response:
            projects_by_name[project["name"]] = project["id"]
            projects_by_id[project["id"]] = project["name"]
        self.projects_by_name = projects_by_name
        self.projects_by_id = projects_by_id

    def get_project_id(self, project_name: str) -> str | None:
        """Return the project ID for *project_name*, or ``None`` if not found.

        :meth:`load_projects` must be called first.

        Args:
            project_name: The display name of the project.

        Raises:
            SessionException: If :meth:`load_projects` has not been called.
        """
        try:
            return self.projects_by_name.get(project_name, None)
        except AttributeError:
            raise SessionException(
                "Call load_projects() before get_project_id()"
            )
