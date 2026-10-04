class LiteratureQueryBuilder:

    @staticmethod
    def disease_target_query(
        disease_name: str,
        target_symbol: str
    ) -> str:

        if not disease_name or not disease_name.strip():
            raise ValueError(
                "Disease name cannot be empty"
            )

        if not target_symbol or not target_symbol.strip():
            raise ValueError(
                "Target symbol cannot be empty"
            )

        disease_name = disease_name.strip()
        target_symbol = target_symbol.strip()

        return (
            f'"{disease_name}" AND {target_symbol}'
        )