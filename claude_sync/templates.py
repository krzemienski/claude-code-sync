"""Template processing for machine-specific path translation

Converts machine-specific paths to portable variables and vice versa.
"""

from pathlib import Path
import os
import platform
import sys


def create_template(content: str) -> str:
    """Replace machine-specific values with portable variables

    Converts absolute paths and machine identifiers to template variables
    for cross-platform portability.

    Args:
        content: Original content with machine-specific values

    Returns:
        Templated content with variables like ${HOME}, ${USER}

    Example:
        Input (Mac):  "/Users/nick/projects"
        Output:       "${HOME}/projects"
    """
    replacements = {
        str(Path.home()): '${HOME}',
        os.environ.get('USER', 'user'): '${USER}',
        platform.node(): '${HOSTNAME}',
        # Platform-specific normalizations
        '/Users/${USER}': '${HOME}',  # Mac
        '/home/${USER}': '${HOME}',   # Linux
    }

    result = content
    for old, new in replacements.items():
        result = result.replace(old, new)

    return result


def expand_template(content: str, project_root: str = None) -> str:
    """Replace template variables with actual machine values

    Expands portable variables to actual paths for the current machine.

    Args:
        content: Templated content with variables
        project_root: Optional project root for ${PROJECT_ROOT} expansion

    Returns:
        Expanded content with actual paths

    Example:
        Input (template): "${HOME}/projects"
        Output (Linux):   "/home/nick/projects"
    """
    replacements = {
        '${HOME}': str(Path.home()),
        '${USER}': os.environ.get('USER', 'user'),
        '${HOSTNAME}': platform.node(),
        '${OS}': sys.platform,  # darwin, linux, win32
    }

    if project_root:
        replacements['${PROJECT_ROOT}'] = project_root

    result = content
    for var, value in replacements.items():
        result = result.replace(var, value)

    return result


def get_machine_vars() -> dict:
    """Get current machine variable values

    Returns:
        Dict of template variables and their current values
    """
    return {
        'HOME': str(Path.home()),
        'USER': os.environ.get('USER', 'user'),
        'HOSTNAME': platform.node(),
        'OS': sys.platform,
    }
