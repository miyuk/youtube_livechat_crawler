# -*- coding: utf-8 -*-

import os
from pathlib import Path
import json
import yaml
from elasticsearch import Elasticsearch
from datetime import datetime
import re


def main():
    comments_dir_path = os.environ.get('COMMENTS_DIR_PATH')
    videos_dir_path = os.environ.get('VIDEOS_DIR_PATH')
    es_host = json.loads(os.environ.get('ES_HOST'))
    es_port = int(os.environ.get('ES_PORT'))
    es_comment_index = os.environ.get('ES_COMMENT_INDEX')
    es_comment_settings_path = os.environ.get(
        'ES_COMMENT_MAPPING_SETTINGS_PATH')

    comment_mapping_settings = get_json(es_comment_settings_path)

    version = datetime.now().strftime('%Y%m%d%H%M%S')
    index_with_version = f'{es_comment_index}_{version}'
    es = Elasticsearch(es_host, port=es_port)
    if not es.indices.exists(index=index_with_version):
        es.indices.create(index=index_with_version,
                          body=comment_mapping_settings)

    if es.indices.exists_alias(es_comment_index):
        alias_indicies = es.indices.get_alias(es_comment_index)

        for index in alias_indicies:
            es.indices.delete_alias(index=index, name=es_comment_index)

        es.indices.put_alias(index=index_with_version, name=es_comment_index)

    for channel_dir in Path(comments_dir_path).iterdir():
        channel_id = channel_dir.name
        videos_file = Path(videos_dir_path).joinpath(f'{channel_id}.json')
        videos = get_json(videos_file)

        for comments_file in channel_dir.iterdir():
            video_id = comments_file.stem
            print(f'upload video: {video_id}')
            comments = get_json(comments_file)
            video_info = [x for x in videos if x['videoId'] == video_id]
            video_info = video_info[0] if video_info else None

            if not video_info:
                print(f'video_info({video_id}) is not founded')
                break

            for i, comment in enumerate(comments):
                comment['videoId'] = video_info['videoId']
                comment['videoTitle'] = video_info['videoTitle']
                comment['channelId'] = video_info['channelId']
                comment['channelTitle'] = video_info['channelTitle']
                comment['publishedAt'] = video_info['publishedAt']
                comment['duration'] = video_info['duration']
                comment['message'] = re.sub(r':[^:]+:', '', comment['message'])
                comment['message'] = re.sub(
                    u'[^\U00000000-\U0000d7ff\U0000e000-\U0000ffff]', '', comment['message'], flags=re.UNICODE)
                comment['message'] = re.sub(r'□', '', comment['message'])
                del comment['messageEx']
                print(
                    f'upload({i + 1}/{len(comments)}): [{video_id}]{comment["id"]}')
                es.create(index=index_with_version,
                          id=comment['id'], body=comment)


def get_json(json_path):
    if not Path(json_path).exists():
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

        return data


if __name__ == '__main__':
    with open('.env.yaml', 'r') as f:
        env = yaml.safe_load(f)
        for k, v in env.items():
            if not isinstance(v, (list, dict)):
                os.environ[k] = str(v)
            else:
                os.environ[k] = json.dumps(v)

    main()
