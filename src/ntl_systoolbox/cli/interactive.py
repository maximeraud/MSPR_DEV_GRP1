from __future__ import annotations
from ntl_systoolbox.core.ui import choose, console

def run_interactive_menu() -> None:
    while True:
        main = choose(
            "Menu principal",
            [
                ("1", "Module 1 - Diagnostic (AD/DNS/MySQL/OS)"),
                ("2", "Module 2 - Sauvegarde WMS (dump SQL, export CSV)"),
                ("3", "Module 3 - Audit obsolescence réseau (scan + EOL)"),
                ("9", "Quitter"),
            ],
            allow_back=False,
        )

        if main == "9":
            console.print("\nAu revoir.\n")
            return

        if main == "1":
            _menu_module1()
        elif main == "2":
            _menu_module2()
        elif main == "3":
            _menu_module3()


def _menu_module1() -> None:
    from ntl_systoolbox.cli.module1_diag import (
        run
    )   

    while True:
        c = choose(
            "Module 1 - Diagnostic",
            [
                ("1", "Tester services AD/DNS (placeholder)"),
                ("2", "Tester accès MySQL (placeholder)"),
                ("3", "Infos ressources OS (placeholder)"),
                ("4", "Sortie JSON (placeholder)"),
            ],
        )
        if c is None:
            return
        # Placeholders : tu relieras aux vraies fonctions plus tard
        if c == "1":
            console.print("[yellow]TODO:[/yellow] implémenter test AD/DNS")
        elif c == "2":
            console.print("[yellow]TODO:[/yellow] implémenter test MySQL")
            run
        elif c == "3":
            console.print("[yellow]TODO:[/yellow] implémenter diagnostic OS")
        elif c == "4":
            console.print("[yellow]TODO:[/yellow] exporter JSON diagnostic")


def _menu_module2() -> None:
    from ntl_systoolbox.cli.module2_backup import (
        interactive_dump_sql,
        interactive_export_csv,
    )

    while True:
        c = choose(
            "Module 2 - Sauvegarde WMS",
            [
                ("1", "Sauvegarde BDD au format SQL (dump)"),
                ("2", "Export d'une table au format CSV"),
            ],
        )
        if c is None:
            return

        if c == "1":
            interactive_dump_sql()
        elif c == "2":
            interactive_export_csv()


def _menu_module3() -> None:
    while True:
        c = choose(
            "Module 3 - Audit obsolescence",
            [
                ("1", "Scanner un réseau (placeholder)"),
                ("2", "Générer rapport (placeholder)"),
                ("3", "Exporter JSON (placeholder)"),
            ],
        )
        if c is None:
            return
        if c == "1":
            console.print("[yellow]TODO:[/yellow] implémenter scan réseau")
        elif c == "2":
            console.print("[yellow]TODO:[/yellow] implémenter rapport audit")
        elif c == "3":
            console.print("[yellow]TODO:[/yellow] exporter JSON audit")