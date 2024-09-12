import argparse
import requests
import logging
import sys
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

@dataclass
class Group:
    name: Optional[str]
    path: Optional[str]
    description: Optional[str] = field(default_factory=None)
    visibility: Optional[str] = field(default_factory='private')
    parent_id: Optional[int] = field(default_factory=None)
    default_branch_protection: Optional[int] = field(default_factory=2)

@dataclass
class Project:
    name: Optional[str]
    path: Optional[str]
    namespace_id: Optional[int]
    description: Optional[str] = field(default_factory=None)
    visibility: Optional[str] = field(default_factory='private')

@dataclass
class Metadata:
    groups: Optional[List[Group]] = field(default_factory=list)
    projects: Optional[List[Project]] = field(default_factory=list)

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

def GenerateMetadata(SRC_GROUP_ID: str,
                     DST_GROUP_NAME,
                     GITLAB_TOKEN,
                     GITLAB_REPO_URL,
                     GITLAB_API_VERSION = "v4"
                     ) -> Metadata:
    
    metadata = Metadata()
    logger.debug(metadata)

    # response = requests.get(
    #     url = f'{GITLAB_REPO_URL}/api/{GITLAB_API_VERSION}/groups/{SRC_GROUP_ID}',
    #     headers = {
    #         'Private-Token': GITLAB_TOKEN
    #     }
    # )
    # if len(response.json()) == 1:
    #     logger.error(f'Get source group {SRC_GROUP_ID} failed. Response: {response.text}')
    #     return metadata
    # return metadata
    # try:
    #     response.json()[0]
    # except:
    #     logger.error(f'Get subgroups failed. Response: {response.text}')
    #     return []
    # return response.json()

def WalkGroups(group_id: str,
               GITLAB_REPO_URL,
               GITLAB_API_VERSION,
               GITLAB_TOKEN,
               SRC_GROUP_ID,
               ):
    response = requests.get(
        url = f'{GITLAB_REPO_URL}/api/{GITLAB_API_VERSION}/groups/{SRC_GROUP_ID}',
        headers = {
            'Private-Token': GITLAB_TOKEN
        }
    )  

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Mirror GitLab groups')
    parser.add_argument('--src-group-id', type=str, help='Source GitLab group ID', required=True)
    parser.add_argument('--dst-group-name', type=str, help='Destination GitLab group name', required=True)
    parser.add_argument('--gitlab-token', type=str, help='GitLab private token', required=True)
    parser.add_argument('--gitlab-repo-url', type=str, help='GitLab API URL', required=True)
    parser.add_argument('--gitlab-api-version', type=str, help='GitLab API version', default='v4')
    parser.add_argument('--debug', action="store_true", help='Print Debug Message', default=False)
    args = parser.parse_args()

    if args.debug:
        config_log(0)
    else:
        config_log()

    logger = logging.getLogger(__name__)
    logger.debug(f'get arguments: {args.__dict__}')

    metadata = GenerateMetadata(
        SRC_GROUP_ID = args.src_group_id,
        DST_GROUP_NAME = args.dst_group_name,
        GITLAB_TOKEN = args.gitlab_token,
        GITLAB_REPO_URL = args.gitlab_repo_url,
        GITLAB_API_VERSION = args.gitlab_api_version
    )

    # logger.debug(f"Metadata: {metadata}")
