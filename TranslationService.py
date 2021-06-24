import json
import os
import typing


class TranslationService:
    def get_text(language: str, key: str):
        translation_file_path = TranslationService.__get_translation_file_path(language)
        with open(translation_file_path) as json_file:
            translation = json.load(json_file)

            keys = key.split(".")
            for key in keys:
                translation = translation[key]

            return translation

    def __get_translation_file_path(language: str) -> str:
        translation_directory_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "translations"
        )

        default_translation_file_name = "taphome-texts"
        translation_file_extension = "json"

        language_translation_file_path = os.path.join(
            translation_directory_path,
            f"{default_translation_file_name}.{language}.{translation_file_extension}",
        )

        if os.path.isfile(language_translation_file_path):
            return language_translation_file_path
        else:
            return os.path.join(
                translation_directory_path,
                f"{default_translation_file_name}.{translation_file_extension}",
            )
