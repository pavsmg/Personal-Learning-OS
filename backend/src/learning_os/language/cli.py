from learning_os.language.importer import import_all_languages


def run() -> None:
    counts = import_all_languages()
    for language, count in counts.items():
        print(f"{language}: imported {count} new mistake(s)")


if __name__ == "__main__":
    run()
