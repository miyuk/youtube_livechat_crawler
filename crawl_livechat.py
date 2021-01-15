# -*- coding: utf-8 -*-

import os
from pathlib import Path
import json
import yaml
import pytchat
from datetime import datetime


def main():
    queue_dir_path = os.environ.get('QUEUE_DIR_PATH')
    comments_dir_path = os.environ.get('COMMENTS_DIR_PATH')

    for queue_file in Path(queue_dir_path).iterdir():
        queue = get_json(queue_file)
        channel_id = queue['channel_id']
        video_id = queue['video_id']

        output_path = Path(comments_dir_path).joinpath(
            f'{channel_id}/{video_id}.json')

        current_comments = get_json(output_path)
        current_comments = current_comments if current_comments else []
        print(f'curent comments count: {len(current_comments)}')

        print(f'get video comments: {video_id}')
        new_comments = get_comments(video_id)

        total_comments = current_comments
        current_comment_ids = [x['id'] for x in current_comments]
        for comment in new_comments:
            if comment['id'] not in current_comment_ids:
                total_comments.append(comment)
        print(
            f'add comments count: {len(total_comments) - len(current_comments)}')
        print(f'upload video comments: {video_id}')
        save_json(output_path, total_comments)
        queue_file.unlink(missing_ok=True)


# 時間切れの場合は、"continuation"も返す
def get_comments(video_id):
    video_comments = []
    chat = pytchat.create(video_id=video_id)
    while chat.is_alive():
        comments = json.loads(chat.get().json())
        video_comments.extend(comments)
        print(f'get comments count: {len(comments)}')
    print(f'total new comments count: {len(video_comments)}')

    return video_comments


def get_json(json_path):
    if not Path(json_path).exists():
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

        return data


def save_json(output_path, data):
    parent_dir = Path(output_path).parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

    return obj


if __name__ == '__main__':
    with open('.env.yaml', 'r') as f:
        env = yaml.safe_load(f)
        for k, v in env.items():
            if not isinstance(v, (list, dict)):
                os.environ[k] = str(v)

    main()
