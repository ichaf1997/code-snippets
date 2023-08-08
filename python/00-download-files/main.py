import requests
from pathlib import Path

def download_ifnot_exist(self, url: str, output: Path) -> bool:
    """下载文件

    Args:
        url (str): 链接地址
        output (Path): 输出路径
    """

    try:
        with requests.get(url, stream=True) as rsp:
            content_size = int(rsp.headers['content-length'])
            if os.path.exists(output) and content_size == os.path.getsize(output):
                logger.info(f'file: {output} exist, Ignored')
                return True
            if rsp.status_code == 200:
                logger.debug(
                    f"file name: {output} file size: {content_size/1048576:.2f}MB")
                with open(file=output, mode='wb') as f:
                    for data in rsp.iter_content(chunk_size=4096):
                        f.write(data)
                    logger.info(f'download completed. [{url}]')
    except Exception as err:
        logger.error(err)
        return False
    return True