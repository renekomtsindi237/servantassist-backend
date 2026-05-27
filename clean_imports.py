#!/usr/bin/env python3
"""
Nettoyeur d'imports - Supprime les imports non utilisés
"""
import ast
import os
import re
import sys
from pathlib import Path
from typing import Set, Tuple

def detect_unused_imports(code: str) -> Set[Tuple[str, str]]:
    """Détecte les imports non utilisés dans le code Python.
    
    Returns:
        Set of (import_name, line_content) tuples
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    
    # Extraire tous les noms importés
    imported_names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names[alias.asname or alias.name] = (
                    node.lineno, 
                    alias.name
                )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names[alias.asname or alias.name] = (
                    node.lineno,
                    alias.name
                )
    
    # Extraire tous les noms utilisés
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Pour les attributs, on prend la partie principale
            obj = node.value
            while isinstance(obj, ast.Attribute):
                obj = obj.value
            if isinstance(obj, ast.Name):
                used_names.add(obj.id)
    
    # Noms spéciaux déjà définis
    builtin_names = {
        '__name__', '__doc__', '__package__', '__loader__',
        '__spec__', '__annotations__', '__builtins__',
        'True', 'False', 'None'
    }
    
    # Trouver les imports non utilisés
    unused = set()
    lines = code.split('\n')
    
    for name, (lineno, orig_name) in imported_names.items():
        if name not in used_names and name not in builtin_names:
            if lineno <= len(lines):
                unused.add((name, lines[lineno - 1].strip()))
    
    return unused


def remove_unused_imports_from_file(filepath: str) -> int:
    """Supprime les imports non utilisés d'un fichier.
    
    Returns:
        Nombre de lignes d'import supprimées
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    
    try:
        code = ''.join(lines)
        unused = detect_unused_imports(code)
    except Exception:
        return 0
    
    if not unused:
        return 0
    
    # Extraire les noms non utilisés
    unused_names = {name for name, _ in unused}
    
    # Supprimer les lignes d'import non utilisées
    new_lines = []
    for line in lines:
        # Vérifier si c'est une ligne d'import
        if re.match(r'^\s*(from\s+|import\s+)', line):
            # Extraire les noms importés de cette ligne
            match = re.match(r'^\s*(?:from\s+[\w.]+\s+)?import\s+(.+)', line)
            if match:
                imports = match.group(1)
                # Séparer les imports multiples
                items = [item.strip() for item in imports.split(',')]
                # Filtrer les imports non utilisés
                kept_items = []
                for item in items:
                    # Extraire le nom de l'import (avant 'as')
                    parts = item.split(' as ')
                    imported_name = parts[0].strip()
                    alias = parts[1].strip() if len(parts) > 1 else imported_name
                    
                    if alias not in unused_names and imported_name not in unused_names:
                        kept_items.append(item)
                
                if kept_items:
                    # Reconstruire la ligne d'import
                    new_line = line[:line.index('import') + 6] + ' ' + ', '.join(kept_items)
                    if not new_line.rstrip().endswith('\n'):
                        new_line += '\n'
                    new_lines.append(new_line)
                # Si aucun import n'est conservé, sauter la ligne
                continue
        
        new_lines.append(line)
    
    # Écrire le fichier modifié
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return original_count - len(new_lines)


def process_directory(directory: str):
    """Traite tous les fichiers Python d'un répertoire."""
    total_removed = 0
    
    for root, dirs, files in os.walk(directory):
        # Ignorer les répertoires venv et __pycache__
        dirs[:] = [d for d in dirs if d not in {'venv', '.venv', '__pycache__', '.git'}]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    removed = remove_unused_imports_from_file(filepath)
                    if removed > 0:
                        print(f"✓ {filepath}: {removed} lines removed")
                        total_removed += removed
                except Exception as e:
                    print(f"✗ {filepath}: {e}")
    
    return total_removed


if __name__ == '__main__':
    directories = sys.argv[1:] if len(sys.argv) > 1 else ['src', 'tests']
    
    print(f"Cleaning up unused imports in: {', '.join(directories)}")
    total = process_directory(directories[0])
    for d in directories[1:]:
        total += process_directory(d)
    
    print(f"\nTotal: {total} lines removed")
