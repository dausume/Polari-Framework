"""
Module Discovery

Scans the framework root for polari*Module directories and provides
utilities for converting between module IDs, package names, and directory names.
"""

import os
import re
import sys
import json
import importlib


def _pascal_to_snake(name):
    """Convert PascalCase to snake_case. E.g. 'MaterialsScience' -> 'materials_science'."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()


def _snake_to_pascal(name):
    """Convert snake_case to PascalCase. E.g. 'materials_science' -> 'MaterialsScience'."""
    return ''.join(word.capitalize() for word in name.split('_'))


def module_dir_to_id(dir_name):
    """Convert a module directory name to its module ID.

    E.g. 'polariMaterialsScienceModule' -> 'materials_science'
    """
    # Strip 'polari' prefix and 'Module' suffix
    inner = dir_name
    if inner.startswith('polari'):
        inner = inner[len('polari'):]
    if inner.endswith('Module'):
        inner = inner[:-len('Module')]
    return _pascal_to_snake(inner)


def module_id_to_package(module_id):
    """Convert a module ID to its Python package name.

    E.g. 'materials_science' -> 'polariMaterialsScienceModule'
    """
    return 'polari' + _snake_to_pascal(module_id) + 'Module'


def module_id_to_display_name(module_id):
    """Convert a module ID to a human-readable display name.

    E.g. 'materials_science' -> 'Materials Science'
    """
    return ' '.join(word.capitalize() for word in module_id.split('_'))


def _get_framework_root():
    """Get the framework root directory (parent of moduleService/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def discover_available_modules(framework_root=None):
    """Scan the framework root for polari*Module directories.

    Returns a dict of module_id -> module info:
        {
            'materials_science': {
                'package_name': 'polariMaterialsScienceModule',
                'display_name': 'Materials Science',
                'description': '...',
                'available': True,  # importable
                'user_created': False,
                'dir_path': '/path/to/polariMaterialsScienceModule'
            },
            ...
        }
    """
    if framework_root is None:
        framework_root = _get_framework_root()

    modules = {}

    for entry in os.listdir(framework_root):
        dir_path = os.path.join(framework_root, entry)
        # Must be a directory matching polari*Module pattern
        if not os.path.isdir(dir_path):
            continue
        if not entry.startswith('polari') or not entry.endswith('Module'):
            continue
        # Must have an __init__.py
        if not os.path.isfile(os.path.join(dir_path, '__init__.py')):
            continue

        module_id = module_dir_to_id(entry)
        package_name = entry

        # Check if importable and has initialize()
        available = False
        try:
            mod = importlib.import_module(package_name)
            available = hasattr(mod, 'initialize') and callable(mod.initialize)
        except Exception:
            pass

        # Check for user-created metadata
        user_created = False
        description = ''
        metadata_path = os.path.join(dir_path, '_module_metadata.json')
        if os.path.isfile(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                user_created = metadata.get('user_created', False)
                description = metadata.get('description', '')
            except Exception:
                pass

        if not description:
            # Try to get description from the module's docstring
            try:
                mod = importlib.import_module(package_name)
                if mod.__doc__:
                    # First non-empty line of docstring
                    for line in mod.__doc__.strip().split('\n'):
                        line = line.strip()
                        if line:
                            description = line
                            break
            except Exception:
                pass

        modules[module_id] = {
            'package_name': package_name,
            'display_name': module_id_to_display_name(module_id),
            'description': description,
            'available': available,
            'user_created': user_created,
            'dir_path': dir_path,
        }

    return modules


# ── Dependency Detection ──────────────────────────────────────────────────────

# Framework-internal import prefixes to exclude from Python dependency detection
_FRAMEWORK_PREFIXES = (
    'polari', 'objectTree', 'setOperators', 'config_loader',
    'moduleService', 'treeObject',
)

# Fallback stdlib set for Python < 3.10
_STDLIB_FALLBACK = frozenset({
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
    'asyncore', 'atexit', 'base64', 'bdb', 'binascii', 'binhex',
    'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb', 'chunk',
    'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections',
    'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib',
    'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal',
    'difflib', 'dis', 'distutils', 'doctest', 'email', 'encodings',
    'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput',
    'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
    'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip', 'hashlib',
    'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr',
    'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
    'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging',
    'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
    'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nis', 'nntplib',
    'numbers', 'operator', 'optparse', 'os', 'ossaudiodev', 'pathlib',
    'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
    'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile',
    'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc',
    'queue', 'quopri', 'random', 're', 'readline', 'reprlib',
    'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select',
    'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site',
    'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
    'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
    'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig',
    'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios',
    'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
    'token', 'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc',
    'tty', 'turtle', 'turtledemo', 'types', 'typing', 'unicodedata',
    'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave',
    'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
    'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
    '_thread', '__future__', 'antigravity', 'this',
})


def _get_stdlib_modules():
    """Get a set of standard library module names."""
    if hasattr(sys, 'stdlib_module_names'):
        return sys.stdlib_module_names
    return _STDLIB_FALLBACK


def scan_python_imports(dir_path):
    """Scan all .py files in a module directory for external Python imports.

    Returns a sorted list of external package names (top-level module names).
    Filters out stdlib, framework internals, and same-module imports.
    """
    stdlib = _get_stdlib_modules()

    # Build set of same-module file names (without .py) for filtering
    same_module_names = set()
    for f in os.listdir(dir_path):
        if f.endswith('.py'):
            same_module_names.add(f[:-3])

    import_re = re.compile(r'^\s*import\s+(\S+)')
    from_re = re.compile(r'^\s*from\s+(\S+)\s+import')

    external_packages = set()

    for root, _dirs, files in os.walk(dir_path):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            filepath = os.path.join(root, fname)
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        match = import_re.match(line) or from_re.match(line)
                        if not match:
                            continue

                        # Get the top-level package name
                        raw = match.group(1)
                        top_level = raw.split('.')[0]

                        # Filter
                        if top_level in stdlib:
                            continue
                        if top_level in same_module_names:
                            continue
                        if any(top_level.startswith(p) for p in _FRAMEWORK_PREFIXES):
                            continue
                        if top_level.startswith('_'):
                            continue

                        external_packages.add(top_level)
            except Exception:
                continue

    return sorted(external_packages)


def detect_cross_module_dependencies(module_id, module_classes, all_module_classes, manager):
    """Detect classes in this module that reference classes in other modules.

    Args:
        module_id: The module being inspected.
        module_classes: List of class names in this module.
        all_module_classes: Dict of {module_id: [class_names]} for all modules.
        manager: The object tree manager (for objectTypingDict access).

    Returns:
        List of {moduleId, moduleName, reasons: [str]}
    """
    # Build reverse lookup: className -> moduleId
    class_to_module = {}
    for mid, classes in all_module_classes.items():
        for cn in classes:
            class_to_module[cn] = mid

    this_module_set = set(module_classes)

    # {target_module_id: set of reason strings}
    deps = {}

    for class_name in module_classes:
        typing_obj = manager.objectTypingDict.get(class_name)
        if typing_obj is None:
            continue

        # Check inheritsFrom
        inherits = getattr(typing_obj, 'inheritsFrom', None)
        if inherits and isinstance(inherits, dict):
            for _var_name, parent_class in inherits.items():
                parent_name = parent_class if isinstance(parent_class, str) else getattr(parent_class, '__name__', str(parent_class))
                if parent_name in class_to_module and parent_name not in this_module_set:
                    target_mid = class_to_module[parent_name]
                    if target_mid != module_id:
                        deps.setdefault(target_mid, set()).add(
                            f'{class_name} inherits from {parent_name}'
                        )

        # Check polyTypedVarsDict for reference fields
        vars_dict = getattr(typing_obj, 'polyTypedVarsDict', {})
        for var_name, var_typing in vars_dict.items():
            # Check if this variable references another class (convention: ends with Id)
            if var_name.endswith('Id') and isinstance(var_name, str):
                ref_class = var_name[:-2]  # e.g. 'materialId' -> 'material'
                # Try PascalCase
                ref_pascal = ref_class[0].upper() + ref_class[1:] if ref_class else ''
                if ref_pascal in class_to_module and ref_pascal not in this_module_set:
                    target_mid = class_to_module[ref_pascal]
                    if target_mid != module_id:
                        deps.setdefault(target_mid, set()).add(
                            f'{class_name}.{var_name} references {ref_pascal}'
                        )

        # Check objectReferencesDict (which classes reference THIS class)
        # This is the reverse direction - skip for outbound deps

    # Format results
    results = []
    for target_mid, reasons in sorted(deps.items()):
        results.append({
            'moduleId': target_mid,
            'moduleName': module_id_to_display_name(target_mid),
            'reasons': sorted(reasons),
        })

    return results
