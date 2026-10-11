"""Paragraph retrieval over hash-verified, explicitly approved sources only."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re


class CorpusError(RuntimeError):
    """The approved corpus cannot be safely loaded."""


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    section_id: str
    excerpt: str
    source_revision: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


STOP_WORDS = frozenset('a an the i my me you your our we where how what can do does to of for from in on it its is are with and or this that have want need please hi just help not no'.split())


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP_WORDS and len(word) > 1}


class CorpusRetriever:
    def __init__(self, root: Path) -> None:
        self.chunks: list[Evidence] = []
        try:
            manifest = json.loads((root / 'shared/contracts/evidence-sources.json').read_text())
            for source in manifest['sources']:
                path = (root / source['path']).resolve()
                if not path.is_relative_to((root / 'knowledge/sources').resolve()):
                    raise CorpusError('Source path is outside the approved knowledge directory.')
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != source['sha256']:
                    raise CorpusError('Approved source revision does not match its manifest.')
                section_id = source['section_ids'][0]
                index = 0
                for paragraph in raw.decode().split('\n\n'):
                    numbered = re.match(r'## ([1-4])\.', paragraph)
                    if numbered:
                        section_id = source['section_ids'][int(numbered.group(1)) - 1]
                    if not paragraph.strip() or paragraph.startswith('#') or paragraph.startswith('Source ID:'):
                        continue
                    index += 1
                    self.chunks.append(Evidence(f"{source['id']}:{index}", source['id'], section_id, paragraph.strip(), source['sha256']))
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, IndexError) as error:
            raise CorpusError('Cannot load the approved corpus.') from error

    def retrieve(self, query: str, section_id: str | None = None, limit: int = 3) -> list[Evidence]:
        """Rank paragraphs using query-token coverage; no baseline answer indexing."""
        query_tokens = tokens(query)
        ranked = []
        for chunk in self.chunks:
            if section_id and chunk.section_id != section_id:
                continue
            overlap = query_tokens & tokens(chunk.excerpt)
            if len(overlap) < 2:
                continue
            score = len(overlap) / max(1, len(query_tokens))
            ranked.append((score, chunk))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in ranked[:limit]]
