#!/bin/env python

import argparse
import getpass
from src.client import Mattermost
import collections
import jinja2
from datetime import datetime
import os, shutil

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("team_name")
parser.add_argument("channel_name")
parser.add_argument("-u", "--username")
parser.add_argument("-p", "--password")
parser.add_argument("-o", "--outpath", help="outputpath", default="./out/")
args = parser.parse_args()
username = args.username or input("username: ")
password = args.password or getpass.getpass("password: ")

try:
    if not os.path.exists(args.outpath):
        os.makedirs(args.outpath)
except Exception as e:
    print("error creating outpath")
    print(e)
    exit(1)

try:
    m = Mattermost(args.url, username, password, args.team_name)
except Exception as e:
    print("error establishing connection")
    print(e)
    exit(1)

try:
    print("downloading posts...")
    posts = m.order_posts(m.download_files(m.get_posts(args.channel_name), args.outpath))
except Exception as e:
    print("error downloading posts")
    print(e)
    exit(1)

templateLoader = jinja2.FileSystemLoader(searchpath="./src")
env = jinja2.Environment(loader=templateLoader)

def unix2time(unix):
    return datetime.utcfromtimestamp(unix / 1000).strftime("%Y-%m-%d %H:%M:%S")

def userid2username(userid):
    return m.get_user(userid)["username"]

env.filters["unix2time"] = unix2time
env.filters["userid2username"] = userid2username
env.globals["now"] = datetime.utcnow

html = env.get_template("template.html").render(posts=posts.values(), team=args.team_name, channel=args.channel_name, server=args.url)
css = env.get_template("style.css").render()

with open(os.path.join(args.outpath, "index.html"), "w+") as f:
    f.write(html)
with open(os.path.join(args.outpath, "styles.css"), "w+") as f:
    f.write(css)
