import json


def sort_translation_file(path):
    data = None
    with open(path) as file:
        data = json.load(file)

    with open(path, "w") as file:
        json.dump(data, file, indent=4, sort_keys=True)


sort_translation_file("hat/assets/js/apps/Iaso/domains/app/translations/fr.json")
sort_translation_file("hat/assets/js/apps/Iaso/domains/app/translations/en.json")
