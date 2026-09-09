"""Three-publication email proof using caller-supplied profiles and simulated hosts."""

from zeo_creator.reference.email_program_suite import effect_family, publication_suite


def main() -> None:
    labels = {
        "publication-a": "Rasa",
        "publication-b": "Prof Rod",
        "publication-c": "Zero Employee",
    }
    for run in publication_suite():
        family = effect_family(run)
        print(
            f"{labels[run.publication.publication_id]} / {run.campaign.artifact_id}: {len(run.drafts)} messages, {len(family.proposals)} simulated effects; assessment {run.assessment.completeness}"
        )


if __name__ == "__main__":
    main()
