#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author         : yanyongyu
@Date           : 2021-03-09 15:15:02
@LastEditors    : yanyongyu
@LastEditTime   : 2021-03-14 11:03:44
@Description    : None
@GitHub         : https://github.com/yanyongyu
"""
__author__ = "yanyongyu"

import re
import base64
from typing import Dict

from nonebot import on_regex
from httpx import HTTPStatusError
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, MessageEvent, MessageSegment, GroupMessageEvent

from src.libs.utils import only_group
from ... import github_config as config
from ...libs.issue import get_issue, issue_to_image
from ...libs.redis import get_group_bind_repo

# allow using api without token
try:
    from ...libs.auth import get_user_token
except ImportError:
    get_user_token = None

ISSUE_REGEX = r"^#(?P<number>\d+)$"
REPO_REGEX: str = r"^(?P<owner>[a-zA-Z0-9][a-zA-Z0-9\-]*)/(?P<repo>[a-zA-Z0-9_\-]+)$"
REPO_ISSUE_REGEX = r"^(?P<owner>[a-zA-Z0-9][a-zA-Z0-9\-]*)/(?P<repo>[a-zA-Z0-9_\-]+)#(?P<number>\d+)$"

issue = on_regex(REPO_ISSUE_REGEX, priority=config.github_command_priority)
issue.__doc__ = """
^owner/repo#number$
获取指定仓库 issue / pr
"""


@issue.handle()
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    group: Dict[str, str] = state["_matched_dict"]
    owner = group["owner"]
    repo = group["repo"]
    number = int(group["number"])
    token = None
    if get_user_token:
        token = await get_user_token(event.get_user_id())
    try:
        issue_ = await get_issue(owner, repo, number, token)
    except HTTPStatusError:
        await issue.finish(f"Issue #{number} not found for repo {owner}/{repo}")
        return
    img = await issue_to_image(issue_)
    if img:
        await issue.finish(
            MessageSegment.image(f"base64://{base64.b64encode(img).decode()}"))


issue_short = on_regex(ISSUE_REGEX,
                       rule=only_group,
                       priority=config.github_command_priority)
issue_short.__doc__ = """
^#number$
获取指定仓库 issue / pr (需通过 /bind 将群与仓库绑定后使用)
"""


@issue_short.handle()
async def handle_short(bot: Bot, event: GroupMessageEvent, state: T_State):
    group = state["_matched_dict"]
    number = int(group["number"])
    full_name = get_group_bind_repo(event.group_id)
    if not full_name:
        await issue_short.finish("此群尚未与仓库绑定！")
        return
    match = re.match(REPO_REGEX, full_name)
    if not match:
        await issue_short.finish("绑定的仓库名不合法！请重新尝试绑定~")
    owner = match.group("owner")
    repo = match.group("repo")

    token = None
    if get_user_token:
        token = await get_user_token(event.get_user_id())
    try:
        issue_ = await get_issue(owner, repo, number, token)
    except HTTPStatusError:
        await issue.finish(f"Issue #{number} not found for repo {owner}/{repo}")
        return
    img = await issue_to_image(issue_)
    if img:
        await issue.finish(
            MessageSegment.image(f"base64://{base64.b64encode(img).decode()}"))