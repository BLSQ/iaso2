from datetime import datetime

from iaso.models import OrgUnit, MatchingAlgorithm, Link, AlgorithmRun


def remove_words(dest, words):
    d = dest
    for word in words:
        d = d.replace(word, "")
    return d


class Algorithm:
    description = "Name and parent similarity"

    words_to_strip = ["aire de santé", "poste de santé", "centre de santé", "centre de sante"]

    def normalize_name(self, name):
        return remove_words(name.strip().lower(), self.words_to_strip)

    def add_item(self, names, item, alternative_name=None):
        if alternative_name:
            name = alternative_name
        else:
            name = item.name
        normalized_name = self.normalize_name(name)
        if normalized_name:
            array = names.get(normalized_name, [])
            array.append(item)
            names[normalized_name] = array
            # if len(array) > 1:
            #   print("found multiple times", name, array)

    def match_level(self, level_1, level_2, run):
        links = []
        names_1 = {}
        for item in level_1:
            self.add_item(names_1, item)
            normalized_name = self.normalize_name(item.name)
            if item.aliases:
                for alias in item.aliases:
                    normalized_alias = self.normalize_name(alias)
                    if normalized_name != normalized_alias:
                        self.add_item(names_1, item, normalized_alias)

        names_2 = {remove_words(item.name.strip().lower(), self.words_to_strip): item for item in level_2}
        for name_1 in names_1.keys():
            item_2 = names_2.get(name_1, None)

            if item_2:
                items = names_1[name_1]
                # if (item_1.aliases and name_2 in map(lambda x: x.strip().lower(), item_1.aliases)):
                for item in items:
                    proceed = not item.parent
                    if not proceed:
                        linked_to_parent = item.parent.source_set.filter(algorithm_run=run).values_list(
                            "source_id", flat=True
                        )
                        if item_2.parent_id in linked_to_parent:
                            proceed = True

                    if item.org_unit_type_id == item_2.org_unit_type_id and proceed:
                        link = Link()
                        link.destination = item
                        link.source = item_2
                        link.algorithm_run = run
                        link.similarity_score = 100 // len(items)
                        link.save()
                        links.append(link)

        return links

    def match(self, version_1, version_2, user=None):
        algo, created = MatchingAlgorithm.objects.get_or_create(
            name=__name__, defaults={"description": self.description}
        )
        run = AlgorithmRun()
        run.algorithm = algo
        run.version_1 = version_1
        run.version_2 = version_2
        if user:
            run.launcher = user
        run.save()
        print(run)
        result = {}
        parent_1 = OrgUnit.objects.filter(version_id=version_1, parent=None)
        parent_2 = OrgUnit.objects.filter(version=version_2, parent=None)

        links = self.match_level(parent_1, parent_2, run)
        result["Top Level Links Count"] = len(links)

        index = 1
        children_1 = list(
            OrgUnit.objects.filter(parent__in=parent_1).prefetch_related("source_set__source__source_set__source")
        )
        children_2 = list(OrgUnit.objects.filter(parent__in=parent_2))
        while children_1 and children_2:
            print(result)
            links = self.match_level(children_1, children_2, run)
            result["Level %d Links Count" % index] = len(links)
            children_2 = list(OrgUnit.objects.filter(parent__in=children_2))

            children_1 = list(
                OrgUnit.objects.filter(parent__in=children_1).prefetch_related("source_set__source__source_set__source")
            )

            index = index + 1
        run.ended_at = datetime.now()
        run.result = result
        run.finished = True
        run.save()
        print(result)
