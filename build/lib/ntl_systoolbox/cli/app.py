import typer
from ntl_systoolbox.cli.interactive import run_interactive_menu
from ntl_systoolbox.cli import module1_diag, module2_backup, module3_audit

app = typer.Typer(
    name="ntl-systoolbox",
    help="NTL-SysToolbox - Outil CLI (3 modules) + sorties JSON/console.",
    no_args_is_help=False,
)

# Sous-apps (commandes)
app.add_typer(module1_diag.app, name="diag", help="Module 1 - Diagnostic")
app.add_typer(module2_backup.app, name="backup", help="Module 2 - Sauvegarde WMS")
app.add_typer(module3_audit.app, name="audit", help="Module 3 - Audit obsolescence")


@app.command("menu")
def menu():
    """Lance le mode interactif (menus)."""
    run_interactive_menu()


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context):
    # Si l'utilisateur lance sans argument -> menu interactif
    if ctx.invoked_subcommand is None:
        run_interactive_menu()