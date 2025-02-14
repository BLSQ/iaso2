from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from scripts.translations.config import IGNORE_ARGS


class Command(BaseCommand):
    help = "Compile translations"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting compilation of translation files..."))

        try:
            # Run compilemessages once with all paths
            call_command("compilemessages", *IGNORE_ARGS)
            self.stdout.write(self.style.SUCCESS("Successfully compiled all translation files!"))
        except CommandError as e:
            self.stdout.write(self.style.ERROR(f"Error compiling translations: {str(e)}"))
            raise
