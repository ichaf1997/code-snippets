import requests
import threading

global url_status
url_status = {}

def make_request(url):
    try:
        requests.get(url, timeout=3)
        metrics_status = '正常'
    except:
        metrics_status = '异常'
    url_status[url] = metrics_status

urls = [
    "https://www.google.com",
    "https://www.youtube.com",
    "https://www.baidu.com"
]


threads = []
for url in urls:
    thread = threading.Thread(target=make_request, args=(url,))
    thread.start()
    threads.append(thread)
for thread in threads:
    thread.join()

print(url_status)

# {'https://www.baidu.com': '正常', 'https://www.youtube.com': '正常', 'https://www.google.com': '正常'}