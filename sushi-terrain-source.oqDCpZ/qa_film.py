import argparse
import json
import math
import statistics
from pathlib import Path


def inspect_projection(projection):
    frames = projection['frames']
    jumps = []
    trail_errors = []
    for frame in range(1, projection['total_frames'] + 1):
        item = frames[str(frame)]
        if item['moving']:
            if not item.get('trail'):
                trail_errors.append({'frame': frame, 'error': 'moving without trail'})
            else:
                error = math.dist(item['head'][:2], item['trail'][-1][:2])
                if error > .2:
                    trail_errors.append({'frame': frame, 'error': error})
        elif item.get('trail'):
            trail_errors.append({'frame': frame, 'error': 'stationary with trail'})
        if frame > 1:
            previous = frames[str(frame - 1)]
            if item['head'][2] > 0 and previous['head'][2] > 0:
                distance = math.dist(item['head'][:2], previous['head'][:2])
                jumps.append({'frame': frame, 'distance': round(distance, 3)})
    jumps.sort(key=lambda item: item['distance'], reverse=True)
    final = frames[str(projection['total_frames'])]
    final_sites = {name: final['labels'][name] for name in
                   ['眉山', '凤翔', '汴京', '登州', '密州', '徐州', '黄州', '杭州', '定州', '惠州', '儋州', '常州']}
    travel_motion = {}
    for chapter in projection['chapters']:
        if chapter['travel_frames'] < 4:
            continue
        destination = chapter['waypoints'][-1]
        points = []
        for frame in range(chapter['start_frame'] + 1, chapter['travel_end']):
            point = frames[str(frame)]['labels'][destination]
            if point[2] > 0:
                points.append((frame, point[0], point[1]))
        acceleration = []
        for previous, current, following in zip(points, points[1:], points[2:]):
            if following[0] - current[0] != 1 or current[0] - previous[0] != 1:
                continue
            dx = following[1] - 2 * current[1] + previous[1]
            dy = following[2] - 2 * current[2] + previous[2]
            acceleration.append(math.hypot(dx, dy))
        if acceleration:
            ordered = sorted(acceleration)
            travel_motion[chapter['id']] = {
                'median_second_difference_px': round(statistics.median(acceleration), 4),
                'p95_second_difference_px': round(ordered[min(len(ordered) - 1, round(len(ordered) * .95))], 4),
            }
    return {
        'total_frames': projection['total_frames'],
        'render_size': [projection.get('render_width', 1280), projection.get('render_height', 720)],
        'forbidden_stops': [name for name in ('汉中', '成都', '剑门关', '广元')
                            if name in projection['arrivals']],
        'bijing_travel_frames': projection['chapters'][0]['travel_frames'],
        'travel_label_motion': travel_motion,
        'max_head_screen_jump': jumps[0],
        'largest_head_screen_jumps': jumps[:20],
        'trail_errors': trail_errors[:50],
        'trail_error_count': len(trail_errors),
        'final_sites': final_sites,
        'final_sites_inside_frame': {name: 0 <= value[0] <= 1280 and 0 <= value[1] <= 720 and value[2] > 0
                                     for name, value in final_sites.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--projection-file', default='projection.json')
    parser.add_argument('--opening-dir', default='route-star')
    parser.add_argument('--report', default='qa-numeric.json')
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    projection = json.loads((out / args.projection_file).read_text())
    report = inspect_projection(projection)
    opening = json.loads((root / args.opening_dir / 'projection.json').read_text())
    report['opening_sites'] = sorted(opening['arrivals'])
    report['opening_forbidden_sites'] = [name for name in ('汉中', '成都', '剑门关', '广元')
                                         if name in opening['arrivals']]
    stationary_jumps = []
    for frame in range(54, 193):
        current = opening['frames'][str(frame)]['head']
        previous = opening['frames'][str(frame - 1)]['head']
        stationary_jumps.append({'frame': frame, 'distance': math.dist(current[:2], previous[:2])})
    stationary_jumps.sort(key=lambda item: item['distance'], reverse=True)
    report['opening_stationary_max_jump'] = stationary_jumps[0]
    schedule_path = out / 'voice' / 'schedule.json'
    if schedule_path.exists():
        schedule = json.loads(schedule_path.read_text())['entries']
        overlaps = []
        for previous, current in zip(schedule, schedule[1:]):
            if current['start'] < previous['end']:
                overlaps.append([previous['id'], current['id']])
        report['audio'] = {
            'segments': len(schedule),
            'overlaps': overlaps,
            'last_narration_end': schedule[-1]['end'],
            'max_subtitle_length': max(len(sub['text']) for item in schedule for sub in item['subtitles']),
        }
        final_chapter = projection['chapters'][-1]
        credits_frame = final_chapter['travel_end'] + round(final_chapter.get('credits_after_s', 999) * 24)
        credits_seconds = (projection['opening_frames'] + credits_frame - 1) / 24
        report['audio']['credits_start'] = credits_seconds
        report['audio']['credits_after_last_narration'] = credits_seconds - schedule[-1]['end']
    (out / args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
