"""Three-publication email proof using caller-supplied profiles and simulated hosts."""

from zeo_creator.reference.email_inputs import profile
from zeo_creator.reference.email_workflow import run_program


def main() -> None:
    # Deployment labels are supplied here; the public strategy contains no private brand facts.
    for label, publication, shape, campaign, sequence in (
        ("Rasa", "publication-a", "hubspot-shaped", "newsletter-and-nurture", "nurture"),
        ("Prof Rod", "publication-b", "kit-shaped", "membership", "lead-magnet-welcome"),
        ("Zero Employee", "publication-c", "kit-shaped", "product-interest", "orientation"),
    ):
        run = run_program(profile(publication), shape, campaign, sequence)  # type: ignore[arg-type]
        print(
            f"{label}: {len(run.drafts)} dual-format messages, {len(run.sequence.steps)} sequence steps, {len(run.proposals)} separate simulated proposals; assessment {run.assessment.completeness}"
        )


if __name__ == "__main__":
    main()
