import argparse
import difflib
import json
import ctypes
import re
import unicodedata
from pathlib import Path

from faster_whisper import WhisperModel


CF = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
CF.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
CF.CFStringCreateWithCString.restype = ctypes.c_void_p
CF.CFStringCreateMutableCopy.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
CF.CFStringCreateMutableCopy.restype = ctypes.c_void_p
CF.CFStringTransform.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
CF.CFStringTransform.restype = ctypes.c_bool
CF.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
CF.CFStringGetCString.restype = ctypes.c_bool
CF.CFRelease.argtypes = [ctypes.c_void_p]
TO_LATIN = ctypes.c_void_p.in_dll(CF, 'kCFStringTransformToLatin')


def normalized_pinyin(text):
    source = CF.CFStringCreateWithCString(None, text.encode('utf-8'), 0x08000100)
    transformed = CF.CFStringCreateMutableCopy(None, 0, source)
    if not CF.CFStringTransform(transformed, None, TO_LATIN, False):
        raise RuntimeError(f'macOS could not transliterate: {text}')
    buffer = ctypes.create_string_buffer(max(1024, len(text.encode('utf-8')) * 4))
    if not CF.CFStringGetCString(transformed, buffer, len(buffer), 0x08000100):
        raise RuntimeError(f'Could not read transliteration: {text}')
    CF.CFRelease(transformed)
    CF.CFRelease(source)
    latin = unicodedata.normalize('NFKD', buffer.value.decode('utf-8')).encode('ascii', 'ignore')
    return re.sub('[^a-z0-9]', '', latin.decode().lower())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--only', nargs='+')
    args = parser.parse_args()
    root = Path(args.root)
    voice = root / 'final-film' / 'voice'
    script = json.loads((voice / 'script.json').read_text())
    model = WhisperModel(args.model, device='cpu', compute_type='int8')
    report_path = voice / 'asr-report.json'
    previous = json.loads(report_path.read_text()) if report_path.exists() else []
    report_by_id = {item['id']: item for item in previous}
    for item in script['entries']:
        if args.only and item['id'] not in args.only:
            continue
        path = voice / 'segments' / f"{item['id']}.wav"
        if not path.exists():
            raise FileNotFoundError(path)
        segments, _ = model.transcribe(
            str(path), language='zh', beam_size=5, vad_filter=True,
            initial_prompt='以下是简体中文历史纪录片旁白，涉及苏轼、苏辙、苏洵、汴京、凤翔、密州、黄州、惠州、儋州、常州。')
        heard = ''.join(segment.text for segment in segments).strip()
        ratio = difflib.SequenceMatcher(None, normalized_pinyin(item['text']), normalized_pinyin(heard)).ratio()
        report = {**item, 'heard': heard, 'pronunciation_similarity': round(ratio, 4),
                  'needs_review': ratio < .90}
        report_by_id[item['id']] = report
        print(f"{item['id']} {ratio:.3f} {heard}", flush=True)
    reports = [report_by_id[item['id']] for item in script['entries'] if item['id'] in report_by_id]
    (voice / 'asr-report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2))
    lines = ['# 旁白回转录检查', '', '相似度按拼音比较，避免“苏轼／苏氏”等同音字造成假错误。', '']
    for item in reports:
        lines.extend([f"## {item['id']}｜{item['pronunciation_similarity']:.3f}",
                      f"原稿：{item['text']}", f"回转录：{item['heard']}", ''])
    (voice / '回转录检查.md').write_text('\n'.join(lines))
    flagged = [item['id'] for item in reports if item['needs_review']]
    print(f'ASR COMPLETE: {len(reports)} segments; review={flagged}', flush=True)


if __name__ == '__main__':
    main()
