#!/usr/bin/env python
"""Utilitário de linha de comando do Django para tarefas administrativas."""
import os
import sys


def main():
    """Executar tarefas administrativas."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xadras.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Tem a certeza de que está "
            "instalado e disponível na sua variável de ambiente PYTHONPATH? "
            "Esqueceu-se de ativar um ambiente virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
