import json
import requests
import boto3
from datetime import datetime
import re

def slugify(s):
  s = s.lower().strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '-', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s

def handler(event, context):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnlimit": "5"
    }
    s = requests.Session()
    r = s.get(url=url, params=params)
    data = r.json()
    title = data["query"]["random"][0]["title"]
    t = s.get(f"{url}?action=query&prop=revisions&titles={title}&rvslots=*&rvprop=content&formatversion=2")
    article = t.json()
    s3 = boto3.resource("s3")
    key = f"{(datetime.now()).strftime("%Y%m%d")}/{slugify(title)}.json"
    s3.put_object(Key=key, Body=json.dump(article), Bucket="parsons")

    return {
        "statusCode": 200,
        "title": title,
        "key": f"article saved to {key}"
    }