from django.test import TestCase

from members.models import Group, Status
from participation.rules import summarize, validate_rule
from qualifications.models import QualificationType, SpecialTaskType


class RuleFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        from departments.models import Department

        cls.maschinist = QualificationType.objects.create(name="Maschinist")
        cls.gf = QualificationType.objects.create(name="Gruppenführer")
        cls.zf = QualificationType.objects.create(name="Zugführer")
        cls.task = SpecialTaskType.objects.create(name="Jugendsprecher")
        cls.group = Group.objects.create(name="Rot")
        cls.status = Status.objects.create(name="Aktiv")
        cls.department = Department.objects.create(name="Abt", code="abt")


def rule(*items, match="all"):
    return {"v": 1, "match": match, "rules": list(items)}


class ValidationTests(RuleFixtureMixin, TestCase):
    def test_valid_full_rule(self):
        r = rule(
            {"kind": "qualification", "op": "has_all", "values": [self.maschinist.pk]},
            {"kind": "special_task", "op": "has_none", "values": [self.task.pk]},
            {"kind": "gender", "op": "in", "values": ["female", "diverse"]},
            {"kind": "age", "op": "between", "min": 10, "max": 17},
            {"kind": "group", "op": "in", "values": [self.group.pk]},
            {"kind": "status", "op": "in", "values": [self.status.pk]},
            {"kind": "department", "op": "in", "values": [self.department.pk]},
            {"match": "any", "rules": [{"kind": "age", "op": "min", "min": 18}]},
        )
        self.assertEqual(validate_rule(r), {})

    def test_empty_top_level_is_valid(self):
        self.assertEqual(validate_rule(rule()), {})

    def test_min_greater_than_max_is_located(self):
        r = rule(
            {"kind": "gender", "op": "in", "values": ["male"]}, {"kind": "age", "op": "between", "min": 9, "max": 5}
        )
        self.assertEqual(validate_rule(r), {"rules[1].max": "Mindestalter größer als Höchstalter"})

    def test_structure_errors(self):
        cases = {
            "not an object": ([], ""),
            "bad version": ({"v": 2, "match": "all", "rules": []}, "v"),
            "bad match": ({"v": 1, "match": "some", "rules": []}, "match"),
            "unknown top key": ({"v": 1, "match": "all", "rules": [], "x": 1}, "x"),
            "rules not list": ({"v": 1, "match": "all", "rules": {}}, "rules"),
        }
        for label, (value, path) in cases.items():
            with self.subTest(label):
                self.assertIn(path, validate_rule(value))

    def test_condition_errors(self):
        pk = self.maschinist.pk
        cases = [
            ({"kind": "color", "op": "in", "values": [1]}, "rules[0].kind"),
            ({"kind": "qualification", "op": "in", "values": [pk]}, "rules[0].op"),
            ({"kind": "qualification", "op": "has_any", "values": []}, "rules[0].values"),
            ({"kind": "qualification", "op": "has_any", "values": [pk], "extra": 1}, "rules[0].extra"),
            ({"kind": "qualification", "op": "has_any", "values": ["a"]}, "rules[0].values"),
            ({"kind": "qualification", "op": "has_any", "values": [True]}, "rules[0].values"),
            ({"kind": "qualification", "op": "has_any", "values": [pk + 999]}, "rules[0].values"),
            ({"kind": "special_task", "op": "has_any", "values": [999999]}, "rules[0].values"),
            ({"kind": "group", "op": "in", "values": [999999]}, "rules[0].values"),
            ({"kind": "status", "op": "in", "values": [999999]}, "rules[0].values"),
            ({"kind": "department", "op": "in", "values": [999999]}, "rules[0].values"),
            ({"kind": "gender", "op": "in", "values": ["robot"]}, "rules[0].values"),
            ({"kind": "age", "op": "min"}, "rules[0].min"),
            ({"kind": "age", "op": "between", "min": 3}, "rules[0].max"),
            ({"kind": "age", "op": "min", "min": -1}, "rules[0].min"),
            ({"kind": "age", "op": "min", "min": 1.5}, "rules[0].min"),
            ({"kind": "age", "op": "min", "min": 5, "max": 9}, "rules[0].max"),
            ({"kind": "age", "op": "min", "min": 500}, "rules[0].min"),
        ]
        for cond, path in cases:
            with self.subTest(cond=cond):
                self.assertIn(path, validate_rule(rule(cond)))

    def test_group_errors(self):
        cond = {"kind": "age", "op": "min", "min": 5}
        cases = [
            (rule({"match": "any", "rules": []}), "rules[0].rules"),
            (rule({"match": "x", "rules": [cond]}), "rules[0].match"),
            (rule({"match": "any", "rules": [cond], "kind": "age"}), "rules[0]"),
            (rule({"match": "any", "rules": [cond], "foo": 1}), "rules[0].foo"),
            (rule({"match": "any", "rules": [{"match": "all", "rules": [cond]}]}), "rules[0].rules[0]"),
            (
                rule({"match": "any", "rules": [{"kind": "age", "op": "min", "min": 5, "max": 3}]}),
                "rules[0].rules[0].max",
            ),
        ]
        for r, path in cases:
            with self.subTest(path=path):
                self.assertIn(path, validate_rule(r))

    def test_too_many_conditions(self):
        r = rule(*[{"kind": "age", "op": "min", "min": 1}] * 51)
        self.assertIn("rules", validate_rule(r))
        self.assertEqual(validate_rule(rule(*[{"kind": "age", "op": "min", "min": 1}] * 50)), {})


class SummaryTests(RuleFixtureMixin, TestCase):
    def test_concept_example(self):
        r = rule(
            {"kind": "qualification", "op": "has_any", "values": [self.maschinist.pk]},
            {
                "match": "any",
                "rules": [
                    {"kind": "qualification", "op": "has_any", "values": [self.gf.pk]},
                    {"kind": "qualification", "op": "has_any", "values": [self.zf.pk]},
                ],
            },
            {"kind": "age", "op": "min", "min": 18},
        )
        self.assertEqual(summarize(r), "Maschinist und (Gruppenführer oder Zugführer) und Alter ab 18")

    def test_variants(self):
        self.assertEqual(summarize(rule()), "Keine besonderen Voraussetzungen")
        r = rule(
            {"kind": "qualification", "op": "has_all", "values": [self.gf.pk, self.zf.pk]},
            {"kind": "age", "op": "between", "min": 10, "max": 17},
            match="any",
        )
        self.assertEqual(summarize(r), "(Gruppenführer und Zugführer) oder Alter von 10 bis 17")
        r = rule({"kind": "qualification", "op": "has_none", "values": [self.gf.pk, self.zf.pk]})
        self.assertEqual(summarize(r), "weder Gruppenführer noch Zugführer")
        r = rule(
            {"kind": "gender", "op": "in", "values": ["female", "diverse"]},
            {"kind": "group", "op": "in", "values": [self.group.pk]},
        )
        self.assertEqual(summarize(r), "(Geschlecht weiblich oder divers) und Gruppe Rot")
        self.assertEqual(summarize(rule({"kind": "age", "op": "max", "max": 17})), "Alter bis 17")
