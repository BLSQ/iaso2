import logging
import os
import re
import time
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from scripts.translations.check import check_po_file
from scripts.translations.config import IGNORE_ARGS


class Command(BaseCommand):
    help = "Make translations and check for missing translations"

    def handle(self, *args, **options):
        # Find existing .po files and their modification times before running makemessages
        project_root = Path.cwd()
        po_files_before = {po_file: po_file.stat().st_mtime for po_file in project_root.rglob("*.po")}

        cmd_args = [
            "--locale=fr",
            "--extension=txt",
            "--extension=py",
            "--extension=html",
            "--verbosity=0",  # Ensure detailed output
        ] + IGNORE_ARGS

        try:
            self.stdout.write(self.style.SUCCESS("Starting translation process..."))  # Log start
            call_command("makemessages", *cmd_args)
            self.stdout.write(self.style.SUCCESS("Translation process completed successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during translation process: {str(e)}"))  # Log error
            self.stdout.write("Continuing despite error...")

        # Check which .po files were modified
        po_files_after = {po_file: po_file.stat().st_mtime for po_file in project_root.rglob("*.po")}
        modified_files = [
            po_file
            for po_file in po_files_after
            if po_file not in po_files_before or po_files_after[po_file] > po_files_before[po_file]
        ]

        self.stdout.write("\nModified .po files:")
        has_missing_translations = False
        for po_file in modified_files:
            relative_path = po_file.relative_to(project_root)
            missing_translations = check_po_file(po_file)
            self.stdout.write(f"\n  {self.style.WARNING('!')} File: {self.style.WARNING(str(relative_path))}")
            if missing_translations:
                has_missing_translations = True
                self.stdout.write("    Missing translations:")
                for msg in missing_translations:
                    self.stdout.write(f"      - {msg}")
            else:
                self.stdout.write(f"  {self.style.SUCCESS('✓')} All translations complete!")

        if has_missing_translations:
            raise CommandError("Some translations are missing. Please add the missing translations before proceeding.")

        self.stdout.write(self.style.SUCCESS("\nAll fields are translated successfully!"))
