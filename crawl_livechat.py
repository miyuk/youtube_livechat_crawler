# -*- coding: utf-8 -*-

import os
from pathlib import Path
import json
import yaml
import pytchat
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor


def main():
    queue_dir_path = os.environ.get('QUEUE_DIR_PATH')
    comments_dir_path = os.environ.get('COMMENTS_DIR_PATH')
    ignore_videos_file_path = os.environ.get('IGNORE_VIDEOS_FILE_PATH')

    max_crawlers = int(os.environ.get('MAX_CRAWLERS'))

    with ProcessPoolExecutor(max_workers=max_crawlers) as executor:
        try:
            queue_files = Path(queue_dir_path).iterdir()
            results = executor.map(execute_queue, queue_files)
            for result in results:
                print(f'finish queue: {result}')

        except (KeyboardInterrupt, SystemExit) as e:
            if executor:
                executor.shutdown(wait=False, cancel_futures=True)
            raise e

        except Exception as e:
            raise e


def execute_queue(queue_file):
    print(f'start queue: {queue_file}')
    comments_dir_path = os.environ.get('COMMENTS_DIR_PATH')

    queue = get_json(queue_file)
    channel_id = queue['channelId']
    video_id = queue['videoId']

    output_path = Path(comments_dir_path).joinpath(
        f'{channel_id}/{video_id}.json')
    current_comments = get_json(output_path)
    current_comments = current_comments if current_comments else []
    print(f'curent comments count: {len(current_comments)}')

    print(f'get video comments: {video_id}')
    new_comments = get_comments(video_id)

    # new_commentsがNoneの場合、取得エラーのためスキップ
    if new_comments is None:
        queue_file.unlink(missing_ok=True)
        return queue_file

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

    return queue_file


def get_comments(video_id):
    ignore_videos_file_path = os.environ.get('IGNORE_VIDEOS_FILE_PATH')

    video_comments = []
    chat = pytchat.create(video_id=video_id, force_replay=True)
    while chat.is_alive():
        comments = json.loads(chat.get().json())
        video_comments.extend(comments)
        print(f'{video_id} get comments count: {len(comments)}')

    try:
        chat.raise_for_status()
    except pytchat.ChatDataFinished:
        print("chat data finished")
    except Exception as e:
        print(f'{type(e).__name__}: {str(e)}')
        ignore_videos = get_json(ignore_videos_file_path)
        ignore_videos = ignore_videos if ignore_videos else []

        if video_id not in [x['videoId'] for x in ignore_videos]:
            print(f'add ignore videos list: {video_id}')
            data = {
                'videoId': video_id,
                'ignoreReason': f'{type(e).__name__}: {str(e)}'
            }
            ignore_videos.append(data)
            save_json(ignore_videos_file_path, ignore_videos)
        return None

    print(f'{video_id} total new comments count: {len(video_comments)}')

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
