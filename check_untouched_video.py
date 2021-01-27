# -*- coding: utf-8 -*-

import os
from pathlib import Path
import json
import yaml


def main():
    videos_dir_path = os.environ.get('VIDEOS_DIR_PATH')
    comments_dir_path = os.environ.get('COMMENTS_DIR_PATH')
    queue_dir_path = os.environ.get('QUEUE_DIR_PATH')
    ignore_videos_file_path = os.environ.get('IGNORE_VIDEOS_FILE_PATH')
    videos_dir = Path(videos_dir_path)
    for videos_file in videos_dir.iterdir():
        channel_id = videos_file.stem

        ignore_videos = get_json(ignore_videos_file_path)
        ignore_video_ids = [x['videoId']
                            for x in ignore_videos] if ignore_videos else []

        channel_videos = get_json(videos_file)
        channel_comments_dir = Path(comments_dir_path).joinpath(channel_id)
        channel_comments_dir.mkdir(parents=True, exist_ok=True)

        already_completed_video_ids = []
        for channel_comments_file in channel_comments_dir.iterdir():
            video_id = channel_comments_file.stem
            already_completed_video_ids.append(video_id)

        print(f'total videos: {len(channel_videos)}')
        print(f'already checked videos: {len(already_completed_video_ids)}')

        for video in channel_videos:
            video_id = video['videoId']
            print(f'check videoId: {video_id}')
            if video_id in already_completed_video_ids:
                print(f'already completed video: {video_id}')
                continue

            if video_id in ignore_video_ids:
                print(f'ignore video: {video_id}')
                continue

            queue_path = Path(queue_dir_path).joinpath(f'{video_id}.json')
            if not queue_path.exists():
                print(f'add video crawl queue: {video_id}')
                message = {
                    'channelId': channel_id,
                    'videoId': video_id
                }
                save_json(queue_path, message)
            else:
                print(f'queue already exists: {video_id}')


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


if __name__ == '__main__':
    with open('.env.yaml', 'r') as f:
        env = yaml.safe_load(f)
        for k, v in env.items():
            if not isinstance(v, (list, dict)):
                os.environ[k] = str(v)

    main()
