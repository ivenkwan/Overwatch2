import json
from graphify.detect import detect
from pathlib import Path

result = detect(Path('.'))
Path('graphify-out/.graphify_detect.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Total files: {result["total_files"]}, Total words: {result["total_words"]}')
