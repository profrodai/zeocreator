"""Discover the complete public capability surface."""

from zeo_creator.registry import capability_manifests


def main() -> None:
    for manifest in capability_manifests():
        effects = ", ".join(sorted(effect.value for effect in manifest.effects.kinds))
        services = ", ".join(sorted(manifest.requirements.services)) or "none"
        print(f"{manifest.id.canonical():45} effects={effects:28} services={services}")


if __name__ == "__main__":
    main()
