# Contribute

### Code formatting


We have adopted Black [](https://github.com/psf/black) as our code
formatting tool. Line length is 120.

The easiest way to use is is to install the pre-commit hook:
1. Install pre-commit: pip install pre-commit
2. Execute pre-commit install to install git hooks in your .git/ directory.

Another good way to have it working is to set it up in your code editor.
Pycharm, for example, has good support for this.

The pre-commit is not mandatory but Continuous Integration will check
if the formatting is respected!

### Tests and linting


For the Python backend, we use the Django builtin test framework. Tests can be executed with

``` {.sourceCode .bash}
docker compose exec iaso ./manage.py test
```

Translations
------------

We have automated the translation process using custom management commands. This process involves generating translation files, checking for missing translations, and compiling them for use in the application. The process also includes fetching translations from other Django apps, including those located in plugin folders.

### Steps for Managing Translations

1. **Generate and Check Translations:**

   Use the `make_translations` management command to generate translation files and check for any missing translations. This command will process `.txt`, `.py`, and `.html` files across the entire project, including any plugins, ensuring that all user-facing text is captured.

   ```bash
   python manage.py make_translations
   ```

   This command will update the `.po` files in the `hat/locale/`, `iaso/locale/`, and any other relevant directories. It will also report any missing translations that need to be addressed.

2. **Compile Translations:**

   After ensuring all translations are complete, use the `compile_translations` command to compile the translation files. This step is necessary to reflect the translations in the application interface.

   ```bash
   python manage.py compile_translations
   ```


### Important Notes

- The scripts are configured to ignore certain directories and include `.py` files, as translations are used in API error handling and choice lists.
- You do not need to add translations for English, as it is the default language. Currently, only French translations are required.
- If you encounter issues with locale paths, ensure that the `LOCALE_PATHS` setting in `settings.py` is correctly configured to include the necessary directories.

By following these steps, you can efficiently manage translations within the Iaso platform, including those from additional Django apps and plugins.


### Code reloading

In development the servers will reload when they detect a file
change, either in Python or Javascript. If you need reloading for the bluesquare-components code, see the "Live Bluesquare Components" section. 

### Troubleshooting

If you need to restart everything
``` {.sourceCode .shell}
docker compose stop && docker compose start
```

If you encounter problems, you can try to rebuild everything from
scratch.

``` {.sourceCode .shell}
# kill containers
docker compose kill
# remove `iaso` container
docker compose rm -f iaso
# build containers
docker compose build
# start-up containers
docker compose up
```

### Jupyter Notebook

To run a Jupyter Notebook, just copy the env variable from runaisasdev.sh, activate the virtualenv and run

``` {.sourceCode .bash}
python manage.py shell_plus --notebook
```

### Testing prod js assets in development

During local development, by default, the Javascript and CSS will be loaded from
a webpack server with live reloading of the code. To locally test the compiled
version as it is in production ( minified and with the same compilation option).
You can launch docker compose with the `TEST_PROD=true` environment variable
set.

e.g `TEST_PROD=true docker compose up`

This can be useful to reproduce production only bugs. Please also test with this
configuration whenever you modify webpack.prod.js to validate your changes.

Alternatively this can be done outside of docker by running:

1. `npm run webpack-prod` to do the build
2. Launching the django server with `TEST_PROD`
   e.g. `TEST_PROD=true python manage.py runserver`.
