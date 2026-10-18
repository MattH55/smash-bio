import unittest

from harvester_cleanup import annotate_record_links, classify_relevance, collapse_families, family_key


class FamilyTests(unittest.TestCase):
    def test_figshare_concept_and_version_collapse(self):
        rows = [
            {"doi": "10.6084/m9.figshare.c.3748049", "title": "Optical trapping", "linked_records": []},
            {"doi": "10.6084/m9.figshare.c.3748049.v1", "title": "Optical trapping", "linked_records": []},
        ]
        families = collapse_families(rows)
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["family_id"], "10.6084/m9.figshare.c.3748049")
        self.assertEqual(families[0]["version_dois"], ["10.6084/m9.figshare.c.3748049.v1"])

    def test_mendeley_newest_version_is_selected(self):
        rows = [{"doi": "10.17632/gkpwngy65h.1", "title": "old", "year": 2020},
                {"doi": "10.17632/gkpwngy65h.3", "title": "new", "year": 2021}]
        family = collapse_families(rows)[0]
        self.assertEqual(family["title"], "new")
        self.assertEqual(family["canonical_doi"], "10.17632/gkpwngy65h.3")
        self.assertEqual(family["family_id"], "10.17632/gkpwngy65h.3")

    def test_repository_declared_family_precedes_suffix(self):
        row = {"doi": "10.5281/zenodo.2", "concept_doi": "10.5281/zenodo.1"}
        self.assertEqual(family_key(row), ("10.5281/zenodo.1", -1, "repository_declared"))


class RelevanceTests(unittest.TestCase):
    def test_linked_study_is_inherited_before_exclusion(self):
        label, evidence = classify_relevance({"title": "Cold atom calibration"}, ["in_scope"])
        self.assertEqual(label, "in_scope")
        self.assertEqual(evidence["rule"], "inherited_linked_study")

    def test_physics_only_deposit_is_excluded(self):
        label, evidence = classify_relevance({"title": "Rydberg cold atoms in an optical lattice"})
        self.assertEqual(label, "out_of_scope")
        self.assertEqual(evidence["rule"], "physics_exclusion")

    def test_pangaea_prior(self):
        label, evidence = classify_relevance({"doi": "10.1594/pangaea.988415", "repository": "PANGAEA",
                                              "title": "Ocean mooring observations", "techniques": ["optical_tweezers"]})
        self.assertEqual(label, "out_of_scope")
        self.assertEqual(evidence["rule"], "repository_prior_pangaea")

    def test_technique_and_biology_are_in_scope(self):
        label, evidence = classify_relevance({"title": "Optical tweezers data for DNA unfolding",
                                              "techniques": ["optical_tweezers"]})
        self.assertEqual(label, "in_scope")
        self.assertEqual(evidence["rule"], "technique_plus_biology")

    def test_excluded_only_link_does_not_leave_public_status(self):
        records = [{"curation": {"level": "auto_abstract"}, "data_availability": {
            "status": "public_repository", "statement": "", "datasets": [
                {"id": "10.1/out", "repository": "Figshare", "content": "raw_traces"}],
            "code": [], "supplementary_files": [], "fulltext_checked": False,
            "raw_traces_available": True}}]
        families = [{"canonical_doi": "10.1/out", "version_dois": [], "family_id": "10.1/out",
                     "relevance": "out_of_scope", "relevance_evidence": {"rule": "physics_exclusion"}}]
        annotate_record_links(records, families)
        availability = records[0]["data_availability"]
        self.assertEqual(availability["status"], "unknown_no_fulltext")
        self.assertFalse(availability["has_linked_dataset"])
        self.assertFalse(availability["raw_traces_available"])

    def test_curated_record_is_read_only(self):
        records = [{"curation": {"level": "curated"}, "data_availability": {
            "status": "public_repository", "datasets": [{"id": "10.1/out"}], "code": []}}]
        before = repr(records)
        annotate_record_links(records, [])
        self.assertEqual(repr(records), before)


if __name__ == "__main__":
    unittest.main()