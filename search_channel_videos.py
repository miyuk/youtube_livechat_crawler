# -*- coding: utf-8 -*-

import os
from pathlib import Path
import json
import yaml
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def main():
    channels_file_path = os.environ.get('CHANNELS_FILE_PATH')
    api_key = os.environ.get('YOUTUBE_DATA_API_KEY')
    videos_dir_path = os.environ.get('VIDEOS_DIR_PATH')
    channels = get_json(channels_file_path)
    print(f'channel count: {len(channels)}')

    for channel in channels:
        channel_name = channel['name']
        channel_id = channel['channelId']
        output_path = f'{videos_dir_path}/{channel_id}.json'
        channel_videos = get_json(output_path)
        channel_videos = channel_videos if channel_videos else []
        print(f'start loading videos of "{channel_name}({channel_id})"')

        # ファイルがない場合は、すべて取得
        latest_published_at = None
        if channel_videos:
            latest_video = max(channel_videos, key=lambda x: x['publishedAt'])
            latest_published_at = datetime.strptime(
                latest_video['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')

        print(f'current video count: {len(channel_videos)}')
        print(
            f'get channel videos of "{channel_name}({channel_id})" after {latest_published_at}')
        new_videos = get_videos(channel_id, api_key, after=latest_published_at)
        print(f'new video count: {len(new_videos)}')

        channel_videos.extend(new_videos)
        channel_videos = list(
            {x['videoId']: x for x in channel_videos}.values())
        channel_videos.sort(key=lambda x: x['publishedAt'])
        print(f'total video count: {len(channel_videos)}')

        if len(new_videos) > 0:
            save_json(output_path, channel_videos)
            print(
                f'complete uploading videos of "{channel_name}({channel_id})"')
        else:
            print(
                f'new videos were not found of "{channel_name}({channel_id})"')


def get_json(json_path):
    if not Path(json_path).exists():
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

        return data


def get_videos(channel_id, api_key, after=None):
    youtube = build('youtube', 'v3', developerKey=api_key)
    after_str = None
    # 保管されている最新動画以降のデータを取得
    if after:
        after_str = datetime.strftime(
            after + timedelta(seconds=1), '%Y-%m-%dT%H:%M:%SZ')
    next_page_token = None
    has_next = True
    videos = []
    try:
        while has_next:
            print(f'loading count: {len(videos)}')
            search_result = youtube.search().list(
                part='id,snippet',
                channelId=channel_id,
                eventType='completed',
                type='video',
                maxResults=50,
                publishedAfter=after_str,
                pageToken=next_page_token
            ).execute()

            for search_item in search_result.get('items', []):
                kind = search_item['id']['kind']
                if kind != 'youtube#video':
                    continue

                video_item = {}
                video_item['videoId'] = search_item['id']['videoId']
                video_item['channelId'] = search_item['snippet']['channelId']
                video_item['channelTitle'] = search_item['snippet']['channelTitle']
                video_item['videoTitle'] = search_item['snippet']['title']
                video_item['publishedAt'] = search_item['snippet']['publishedAt']

                video_details_result = youtube.videos().list(
                    part='contentDetails',
                    id=video_item['videoId']
                ).execute()

                video_details_item = video_details_result.get('items', [])[0]
                video_item['duration'] = video_details_item['contentDetails']['duration']

                videos.append(video_item)

            if 'nextPageToken' in search_result.keys():
                next_page_token = search_result['nextPageToken']
                has_next = True
            else:
                next_page_token = None
                has_next = False
    except HttpError as e:
        if e.resp.status == 403:
            print('Youtube API Error')
            if json.loads(e.content)['error']['errors'][0]['reason'] == 'quotaExceeded':
                print('API access quota exceeded')
            raise

    return videos


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
