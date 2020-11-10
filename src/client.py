import os
import requests
import json
import collections
import jinja2


class Mattermost:
    def __init__(self, baseurl, username, password, team_name):
        url = baseurl + "/api/v4/users/login"

        payload = {"login_id": username, "password": password}
        headers = {"content-type": "application/json"}
        s = requests.Session()
        r = s.post(url, data=json.dumps(payload), headers=headers)
        self.auth_token = r.headers.get("Token")
        self.baseurl = baseurl
        self.head = {"Authorization": "Bearer " + self.auth_token}
        self.users = {}
        self.team_id = self._get_team_id(team_name)

    def _get_team_id(self, team_name):
        url = self.baseurl + "/api/v4/teams/search"
        payload = {"term": team_name}
        response = requests.post(url, headers=self.head, json=payload)
        info = response.json()
        team_id = info[0]["id"]
        return team_id

    def _get_channel_id(self, channel_name):
        url = self.baseurl + "/api/v4/teams/" + self.team_id + "/channels/search"
        payload = {"term": channel_name}
        response = requests.post(url, headers=self.head, json=payload)
        info = response.json()
        channel_id = info[0]["id"]
        return channel_id

    def _get_posts(self, channel_id):
        url = self.baseurl + "/api/v4/channels/" + channel_id + "/posts"
        response = requests.get(url, headers=self.head).json()
        order = response["order"]
        posts = response["posts"]
        while response["order"]:
            url = self.baseurl + "/api/v4/channels/" + channel_id + "/posts?before=" + order[-1]
            response = requests.get(url, headers=self.head).json()
            order += response["order"]
            posts.update(response["posts"])

        return {"order": order, "posts": posts}

    def get_posts(self, channel_name):
        channel_id = self._get_channel_id(channel_name)
        return self._get_posts(channel_id)

    def get_user(self, user_id):
        if user_id not in self.users:
            try:
                url = self.baseurl + "/api/v4/users/" + user_id
                response = requests.get(url, headers=self.head).json()
                self.users[response["id"]] = response
            except Exception as e:
                return None
        return self.users[user_id]

    def download_file(self, fileid, path="."):
        url = self.baseurl + "/api/v4/files/" + fileid + "/info"
        response = requests.get(url, headers=self.head)
        info = response.json()
        filename = info["name"]
        attachmentspath = os.path.join(path, 'attachments')
        if not os.path.exists(attachmentspath):
             os.makedirs(attachmentspath)
        filepath = os.path.join('attachments', filename)
        filesavepath = os.path.join(path, filepath)
        if not os.path.exists(filesavepath):
            url = self.baseurl + "/api/v4/files/" + fileid
            response = requests.get(url, headers=self.head)
            open(filesavepath, "wb").write(response.content)
        return {**info, "path": filepath}

    def download_files(self, posts, path="."):
        posts, order = posts["posts"], posts["order"]
        for p in posts.values():
            if "metadata" in p and "files" in p["metadata"]:
                p["metadata"]["files"] = [self.download_file(file["id"], path) for file in p["metadata"]["files"]]
        return {"order": order, "posts": posts}

    def order_posts(self, posts):
        posts, order = posts["posts"], posts["order"]
        for reply in filter(lambda x: not x["parent_id"] == "", posts.values()):
            parent = posts[reply["parent_id"]]
            parent["reply_count"] += 1
            if not "replies" in parent:
                parent["replies"] = [reply]
            else:
                parent["replies"].append(reply)
                parent["replies"].sort(key=lambda x: x["create_at"])
        posts = dict(filter(lambda x: x[1]["parent_id"] == "", posts.items()))
        postids = list(filter(lambda x: x in posts, order[::-1]))
        return collections.OrderedDict((k, posts[k]) for k in postids)
