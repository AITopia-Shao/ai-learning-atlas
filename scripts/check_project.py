"""Validate portable links and the generated curriculum, using only stdlib."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parent.parent
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


documents = sorted(ROOT.glob('*.md')) + sorted((ROOT / 'graph').glob('*.md'))
link_count = 0
for document in documents:
    body = document.read_text(encoding='utf-8-sig')
    for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', body):
        if target.startswith(('https://', 'http://', 'mailto:', '#')):
            continue
        check(not re.match(r'^(?:[A-Za-z]:|/|file:)', target),
              f'{document.name}: nonportable link {target}')
        destination = document.parent / unquote(urlsplit(target).path)
        check(destination.is_file(), f'{document.name}: missing link {target}')
        link_count += 1

data = json.loads((ROOT / 'graph/curriculum.json').read_text(encoding='utf-8'))
nodes = {node['id']: node for node in data['nodes']}
check(len(nodes) == len(data['nodes']), 'Duplicate node IDs')
for node in nodes.values():
    if node.get('parent'):
        check(node['parent'] in nodes, f"Missing parent: {node['id']}")
    if node.get('trackable'):
        hours = node.get('estimatedHours')
        check(node['type'] == 'topic' and not node['referenceOnly'],
              f"Invalid learning unit: {node['id']}")
        check(isinstance(hours, (int, float)) and math.isfinite(hours) and hours > 0,
              f"Invalid hour weight: {node['id']}")
for edge in data['edges']:
    check(edge['source'] in nodes and edge['target'] in nodes, f'Missing edge endpoint: {edge}')

source_urls = set()
for filename, digest in data['meta']['sourceHashes'].items():
    source = (ROOT / filename).read_text(encoding='utf-8-sig')
    check(hashlib.sha256(source.encode()).hexdigest() == digest,
          f'Stale source hash: {filename}; run the build')
    source_urls.update(re.findall(r'\[[^\]]+\]\((https?://[^\s)]+)\)', source))
resource_urls = {node['url'] for node in nodes.values() if node['type'] == 'resource'}
check(source_urls <= resource_urls, f'Missing curriculum URLs: {sorted(source_urls - resource_urls)}')

html = (ROOT / 'AI学习图谱.html').read_text(encoding='utf-8')
embedded = re.search(r'<script[^>]*id="curriculum-data"[^>]*>(.*?)</script>', html, re.S)
check(embedded is not None, 'Missing embedded curriculum')
if embedded:
    check(json.loads(embedded.group(1)) == data, 'HTML and curriculum.json differ')
check(not re.search(r'/\*__(?:DATA|APP|STYLE|LAYOUT|PROGRESS)__\*/', html),
      'Unresolved build marker in HTML')
check(not re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://', html),
      'HTML requires a remote script or stylesheet')

if errors:
    raise SystemExit('\n'.join(errors))
print(json.dumps({'local_links': link_count, 'nodes': len(nodes),
                  'learning_chapters': sum(bool(n.get('trackable')) for n in nodes.values()),
                  'source_urls_preserved': len(source_urls), 'status': 'passed'}, ensure_ascii=False))
