"""Regenerate protocol classes, preserving librespot's public module names.

Run with protoc 36.1 (Python gencode 7.36.1) or a reviewed compatible compiler.
The runtime must be at least as new as the generated code.
"""
import ast
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    """Compile the checked-in schemas and rewrite package-local imports."""
    root = Path(__file__).resolve().parents[1]
    compiler = subprocess.check_output(['protoc', '--version'], text=True).strip()
    if compiler != 'libprotoc 36.1':
        raise RuntimeError(f'Expected protoc 36.1 for reproducible generation, got {compiler}')
    source = root / 'proto'
    target = root / 'librespot' / 'proto'
    modules = {}
    for path in sorted(target.rglob('*_pb2.py')):
        match = re.search(r'^# source: (.+)$', path.read_text(), re.MULTILINE)
        if match is None:
            raise ValueError(f'Missing schema provenance: {path}')
        schema = Path(match[1])
        generated = schema.with_name(schema.stem.replace('-', '_') + '_pb2.py')
        module = '.'.join(generated.with_suffix('').parts)
        public = 'librespot.proto.' + '.'.join(path.relative_to(target).with_suffix('').parts)
        modules[module] = (schema, generated, path, public)

    with tempfile.TemporaryDirectory(prefix='librespot-protoc-') as temp:
        subprocess.run(['protoc', f'--proto_path={source}', f'--python_out={temp}',
                        *[str(entry[0]) for entry in modules.values()]],
                       cwd=source, check=True)
        for module, (_, generated, path, public) in modules.items():
            code = (Path(temp) / generated).read_text()
            lines = code.splitlines(keepends=True)
            for node in ast.parse(code).body:
                if isinstance(node, ast.Import):
                    alias = node.names[0]
                    if alias.name in modules:
                        lines[node.lineno - 1] = f'import {modules[alias.name][3]} as {alias.asname}\n'
                elif isinstance(node, ast.ImportFrom):
                    alias = node.names[0]
                    dependency = f'{node.module}.{alias.name}'
                    if dependency in modules:
                        lines[node.lineno - 1] = f'import {modules[dependency][3]} as {alias.asname}\n'
            code = ''.join(lines)
            code = code.replace(f"DESCRIPTOR, '{module}', _globals)",
                                f"DESCRIPTOR, '{public}', _globals)")
            path.write_text(code)
    print(f'Regenerated {len(modules)} protocol modules')


if __name__ == '__main__':
    main()
