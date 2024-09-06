import gitlab
import argparse
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import gitlab.exceptions


def initGitlab(
    url: Optional[str] = None,
    private_token: Optional[str] = None,
    ssl_verify: Optional[bool] = False
) -> gitlab.Gitlab:
    """
    Initialize a GitLab instance with params.
    """
    return gitlab.Gitlab(url, private_token, ssl_verify)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitLab Group mirrorer")
    parser.add_argument("--url", help="GitLab instance URL", required=True)
    parser.add_argument("--private-token", help="Private token for authentication", required=True)
    parser.add_argument("--ssl-verify", help="SSL verification (True/False or path to CA certificate)", action='store_true', default=False)
    parser.add_argument("--source-group-id", help="Source GitLab group ID", required=True)
    parser.add_argument("--destination-group-name", help="Destination GitLab group Name(if not exist, create automatically)", required=True)

    args = parser.parse_args()

    gl = initGitlab(args.url, args.private_token, args.ssl_verify)

    try:
        source_group = gl.groups.get(args.source_group_id)
        # for p in source_group.projects.list(get_all=True, include_subgroups=True):
        #     print(p.attributes)
         
    except gitlab.exceptions.GitlabGetError as err:
        print(f"Failed to get source group id: {args.source_group_id}\n {err}")
        exit(1)
    
    # Create Destination Root group
    try:
        root_group = gl.groups.create(
            {
                "name": args.destination_group_name,
                "path": args.destination_group_name,
                "visibility": "private" if source_group.visibility == "internal" else "public",
                "description": f"Mirror of {source_group.attributes['name']}"  # Source group description will be used as description for mirror group
            }
        )
    except gitlab.exceptions.GitlabCreateError as err:
        print(f"Failed to create dst group name: {args.destination_group_name}\n {err}")
        exit(1)
    # Create Destination Sub groups
    root_group_id = root_group.attributes['id']
    for sg in source_group.subgroups.list():
        try:
            gl.groups.create({
                "name": sg.attributes['name'],
                "path": f"{root_group.attributes['path']}/{sg.attributes['name']}",
                "parent_id": root_group_id,
                "visibility": "private" if sg.attributes['visibility'] == "internal" else "public",
                "description": sg.attributes['description']  # Source subgroup description will be used as description for mirror subgroup
            })
            gl.projects.create({
                "name": sg.attributes['name'],
                "namespace_id": root_group_id,
                "path_with_namespace": f"{root_group.attributes['path']}/{sg.attributes['name']}",
                "description": sg.attributes['description'],
                "visibility": "private" if sg.attributes['visibility'] == "internal" else "public",
                "issues_enabled": sg.attributes['issues_enabled'],
                "merge_requests_enabled": sg.attributes['merge_requests_enabled'],
                "wiki_enabled": sg.attributes['wiki_enabled'],
                "snippets_enabled": sg.attributes['snippets_enabled'],
                "shared_runners_enabled": sg.attributes['shared_runners_enabled'],
                "allow_merge_on_green_enabled": sg.attributes['allow_merge_on_green_enabled'],
                "auto_cancel_pending_pushes": sg.attributes['auto_
            })
        except gitlab.exceptions.GitlabCreateError as err:
            print(f"Failed to create subgroup: {sg.attributes['name']}\n {err}")
            exit(1)
        


    # print(gl.groups.get(args.source_group_id).subgroups.list())
    # print(len(gl.groups.get(args.source_group_id).subgroups.list()))

    # for group in gl.groups.list(all=True):
    #     if group.attributes['name']