#!/usr/bin/env python
import multiprocessing

# ✅ Mac & Windows safe for multiprocessing
if __name__ == '__main__':
    multiprocessing.set_start_method("spawn", force=True)

    import os
    import sys

    def main():
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aadhar_masking_project.settings')
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH? Did you forget to activate a virtual environment?"
            ) from exc
        execute_from_command_line(sys.argv)

    main()
