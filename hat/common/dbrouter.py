class DbRouter:
    """This router is here to allow foreign key between the `default` db and the `worker` db which are the same"""

    def allow_relation(self, obj1, obj2, **hints):
        return True
