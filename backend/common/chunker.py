"""Tree-sitter AST-based code-aware chunking.

Primary strategy: Parse source code with tree-sitter, extract meaningful
code units (functions, classes, methods, etc.) as individual chunks.

Fallback: If tree-sitter grammar is unavailable or parsing fails, use
bounded line-based chunking. A large file is NEVER turned into one
enormous chunk.
"""
from dataclasses import dataclass
from typing import List
import logging

from . import config
from .models import CodeChunk

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """Configuration for a supported language's tree-sitter parsing."""
    language: str
    module_name: str          # Python package name, e.g. 'tree_sitter_python'
    node_types: List[str]     # AST node types to extract as chunks


LANGUAGE_CONFIGS: dict[str, LanguageConfig] = {
    'python': LanguageConfig(
        'python', 'tree_sitter_python',
        ['function_definition', 'class_definition', 'decorated_definition'],
    ),
    'javascript': LanguageConfig(
        'javascript', 'tree_sitter_javascript',
        ['function_declaration', 'class_declaration', 'method_definition',
         'arrow_function', 'export_statement'],
    ),
    'typescript': LanguageConfig(
        'typescript', 'tree_sitter_typescript',
        ['function_declaration', 'class_declaration', 'method_definition',
         'arrow_function', 'export_statement', 'interface_declaration',
         'type_alias_declaration'],
    ),
    'java': LanguageConfig(
        'java', 'tree_sitter_java',
        ['method_declaration', 'class_declaration', 'interface_declaration',
         'constructor_declaration'],
    ),
    'c': LanguageConfig(
        'c', 'tree_sitter_c',
        ['function_definition', 'struct_specifier'],
    ),
    'cpp': LanguageConfig(
        'cpp', 'tree_sitter_cpp',
        ['function_definition', 'class_specifier', 'struct_specifier'],
    ),
    'go': LanguageConfig(
        'go', 'tree_sitter_go',
        ['function_declaration', 'method_declaration', 'type_declaration'],
    ),
    'rust': LanguageConfig(
        'rust', 'tree_sitter_rust',
        ['function_item', 'impl_item', 'struct_item', 'enum_item', 'trait_item'],
    ),
}


def _extract_symbol_name(node, source_bytes: bytes) -> str:
    """Extract the identifier name from an AST node."""
    # Look for a direct 'name' or 'identifier' child
    for child in node.children:
        if child.type in ('identifier', 'name', 'type_identifier'):
            return source_bytes[child.start_byte:child.end_byte].decode('utf-8', errors='replace')
        # For decorated definitions, look inside the inner definition
        if child.type in ('function_definition', 'class_definition'):
            return _extract_symbol_name(child, source_bytes)
    # Fallback: use node type + start line
    return f"{node.type}_{node.start_point[0] + 1}"


def chunk_file_fallback(
    content: str,
    file_path: str,
    language: str,
    repo: str,
    commit_sha: str,
) -> List[CodeChunk]:
    """Fallback chunking: split file into bounded line-based chunks."""
    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    chunks: List[CodeChunk] = []
    chunk_size = config.FALLBACK_CHUNK_MAX_LINES

    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i:i + chunk_size]
        chunk_content = ''.join(chunk_lines)
        start_line = i + 1
        end_line = i + len(chunk_lines)
        chunks.append(CodeChunk(
            repo=repo,
            commit_sha=commit_sha,
            file_path=file_path,
            language=language,
            symbol=f'chunk_{i // chunk_size}',
            symbol_type='fallback',
            start_line=start_line,
            end_line=end_line,
            content=chunk_content,
        ))
    return chunks


def chunk_file(
    content: str,
    file_path: str,
    language: str,
    repo: str,
    commit_sha: str,
) -> List[CodeChunk]:
    """Parse a source file with tree-sitter and extract code-aware chunks.

    Falls back to bounded line-based chunking if tree-sitter is unavailable
    or fails.
    """
    lang_cfg = LANGUAGE_CONFIGS.get(language)
    if not lang_cfg:
        logger.info(f"No tree-sitter config for language '{language}', using fallback for {file_path}")
        return chunk_file_fallback(content, file_path, language, repo, commit_sha)

    try:
        import importlib
        from tree_sitter import Language, Parser

        # Import the language module (e.g. tree_sitter_python)
        lang_module = importlib.import_module(lang_cfg.module_name)

        # tree-sitter >=0.23 API: Language(ptr) then Parser(language=...)
        ts_language = Language(lang_module.language())
        parser = Parser(ts_language)

        source_bytes = content.encode('utf-8')
        tree = parser.parse(source_bytes)

        chunks: List[CodeChunk] = []

        def _walk(node):
            if node.type in lang_cfg.node_types:
                start_line = node.start_point[0] + 1  # 1-based
                end_line = node.end_point[0] + 1
                symbol = _extract_symbol_name(node, source_bytes)
                node_content = source_bytes[node.start_byte:node.end_byte].decode(
                    'utf-8', errors='replace'
                )

                # Bound very large nodes via the fallback limit
                line_count = end_line - start_line + 1
                if line_count > config.FALLBACK_CHUNK_MAX_LINES * 3:
                    # Split oversized node into sub-chunks
                    sub_lines = node_content.splitlines(keepends=True)
                    for j in range(0, len(sub_lines), config.FALLBACK_CHUNK_MAX_LINES):
                        sub = sub_lines[j:j + config.FALLBACK_CHUNK_MAX_LINES]
                        chunks.append(CodeChunk(
                            repo=repo,
                            commit_sha=commit_sha,
                            file_path=file_path,
                            language=language,
                            symbol=f"{symbol}_part{j // config.FALLBACK_CHUNK_MAX_LINES}",
                            symbol_type=node.type,
                            start_line=start_line + j,
                            end_line=start_line + j + len(sub) - 1,
                            content=''.join(sub),
                        ))
                else:
                    chunks.append(CodeChunk(
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        language=language,
                        symbol=symbol,
                        symbol_type=node.type,
                        start_line=start_line,
                        end_line=end_line,
                        content=node_content,
                    ))
                return  # Don't recurse into already-captured nodes

            for child in node.children:
                _walk(child)

        _walk(tree.root_node)

        if not chunks:
            # No meaningful AST units found — treat as module-level
            return chunk_file_fallback(content, file_path, language, repo, commit_sha)

        return chunks

    except ImportError as e:
        logger.warning(f"tree-sitter not available for {language}: {e}")
        return chunk_file_fallback(content, file_path, language, repo, commit_sha)
    except Exception as e:
        logger.warning(f"tree-sitter parsing failed for {file_path}: {e}")
        return chunk_file_fallback(content, file_path, language, repo, commit_sha)
