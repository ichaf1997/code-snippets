import argparse
import gitlab.exceptions
import logging
import sys
import os
import shutil
import gitlab
import re
import git
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union
)

# @dataclass
# class GitlabAuthentication:
#     gitlab_token: Optional[str]
#     gitlab_username: Optional[str]
#     gitlab_password: Optional[str]
#     gitlab_repo_url: Optional[str]
#     gitlab_api_version: Optional[str] = field(default_factory='v4')

def config_log(loglevel: int = 20):
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    logging.basicConfig(
        level=loglevel,
        format=(
            "[%(asctime)s] {%(filename)s:%(lineno)d} [%(levelname)s]"
            " %(message)s"
        ),
        handlers=[stdout_handler],
    )

# def extract_project_name(repo_url)-> str:
#     match = re.search(r'/([^/]+)\.git$', repo_url)
#     if match:
#         return match.group(1)
#     logger.error(f'unable extract project from repo_url {repo_url}')
#     sys.exit(1)

def copy_group(
        src_group_id: str,
        dst_group_name: str,
        ga: gitlab.Gitlab
):

    tmp_dir = os.path.join(os.path.dirname(__file__), '.tmp')
    try:
        shutil.rmtree(tmp_dir)
    except Exception as err:
        logger.warning(f'Failed to remove directory {tmp_dir}: {err}')
    os.makedirs(tmp_dir)

    def remote_callback(remote, url, username_from_url, allowed_types):
        return args.git_username, args.git_password

    def copy_subgroups_and_projects(src_grp, dst_grp):
        # 复制子组
        for subgroup in src_grp.subgroups.list():
            new_subgroup = ga.groups.create({
                'name': subgroup.name,
                'path': subgroup.path.lower().replace(' ', '-'),
                'parent_id': dst_grp.id,
                'description': subgroup.description,
                'visibility': 'private',
                'default_branch_protection': 0
            })
            logger.info(f'Create group {new_subgroup.name}\n {new_subgroup.attributes}')
            copy_subgroups_and_projects(ga.groups.get(subgroup.id), new_subgroup)
        
        # 复制项目
        for project in src_grp.projects.list():
            src_project = ga.projects.get(project.id)
            new_project_data = {
                'name': src_project.name,
                'path': src_project.path,
                'namespace_id': dst_grp.id,
                'description': src_project.description,
                'visibility': 'private'
            }
            new_project = ga.projects.create(new_project_data)
            logger.info(f'Create project {new_project.name}\n {new_project.attributes}')
            with git.Git().custom_environment(GIT_ASKPASS=remote_callback):
                repo_path = os.path.join(tmp_dir, src_project.name)
                git.Repo.clone_from(
                    url = src_project.http_url_to_repo, 
                    to_path = repo_path,
                    multi_options = [
                        "--config core.longpaths=true"
                    ],
                    allow_unsafe_options = True
                )
                repo = git.Repo(repo_path)
                origin = repo.remote()
                origin.set_url(new_project.http_url_to_repo)
                branch = repo.heads['dev']
                origin.push(
                    f'dev:master'
                )
                new_project.protectedbranches.create({
                    'name': 'master',
                    'push_access_level': 0,
                    'merge_access_level': 40,
                    'unprotect_access_level': 0
                })                
                logger.info(f'push repo {repo_path} to {new_project.http_url_to_repo} barnch -> master')                
                origin.push(
                    f'dev:develop'
                )
                new_project.protectedbranches.create({
                    'name': 'develop',
                    'push_access_level': 0,
                    'merge_access_level': 30,
                    'unprotect_access_level': 0
                })                   
                logger.info(f'push repo {repo_path} to {new_project.http_url_to_repo} barnch -> develop')
                origin.push(
                    f'dev:test'
                )
                new_project.protectedbranches.create({
                    'name': 'test',
                    'push_access_level': 0,
                    'merge_access_level': 30,
                    'unprotect_access_level': 0
                }) 
                logger.info(f'push repo {repo_path} to {new_project.http_url_to_repo} barnch -> test')
                origin.push(
                    f'dev:reyun'
                )
                logger.info(f'push repo {repo_path} to {new_project.http_url_to_repo} barnch -> reyun')

    try:
        src_group = ga.groups.get(src_group_id)
        logger.debug(f'Get source group id {src_group_id}\n {src_group.attributes}')
    except gitlab.exceptions.GitlabGetError as err:
        logger.error(f'Failed to get source group id: {src_group_id}({err})')
        return

    try:
        dst_group = ga.groups.create({
            'name': dst_group_name,
            'path': dst_group_name.lower().replace(' ', '-'),
            'description': f"Copy from {src_group.attributes.get('web_url')}",
            'visibility': 'private',
            'default_branch_protection': 0
        })
        logger.info(f'Create group {dst_group_name}\n {dst_group.attributes}')
    except gitlab.exceptions.GitlabCreateError as err:
        logger.error(f'Failed to create group: {dst_group_name}({err})')
        return
    
    copy_subgroups_and_projects(
        src_grp = src_group, 
        dst_grp = dst_group
    )

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Mirror GitLab groups')
    parser.add_argument('--src-group-id', type=str, help='Source GitLab group ID', required=True)
    parser.add_argument('--dst-group-name', type=str, help='Destination GitLab group name', required=True)
    parser.add_argument('--gitlab-token', type=str, help='GitLab private token', required=True)
    parser.add_argument('--gitlab-repo-url', type=str, help='GitLab API URL', required=True)
    parser.add_argument('--git-username', type=str, help='Git username', required=True)
    parser.add_argument('--git-password', type=str, help='Git password', required=True)
    parser.add_argument('--debug', action="store_true", help='Print Debug Message', default=False)
    args = parser.parse_args()

    if args.debug:
        config_log(0)
    else:
        config_log()

    logger = logging.getLogger(__name__)
    logger.debug(f'get arguments: {args.__dict__}')

    ga = gitlab.Gitlab(
        url = args.gitlab_repo_url,
        private_token = args.gitlab_token
    )

    copy_group(
        src_group_id = args.src_group_id,
        dst_group_name = args.dst_group_name,
        ga = ga
    )
