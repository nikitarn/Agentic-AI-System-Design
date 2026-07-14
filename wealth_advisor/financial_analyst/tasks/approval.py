from __future__ import annotations

from rich.console import Console
from rich.table import Table

from financial_analyst.tasks.planner import GoalPlan

console = Console()


def present_plan_for_approval(plan: GoalPlan) -> GoalPlan | None:
    """
    Render the plan as a Rich table and prompt the user to:
      [A] Approve — returns the plan as-is
      [M] Modify  — edit a step description in-place and re-render
      [R] Reject  — returns None so the caller can re-plan with feedback

    Loop continues until the user approves or rejects.
    """
    while True:
        _render_plan(plan)
        choice = input("\n[A]pprove / [M]odify step / [R]eject and re-plan: ").strip().upper()

        if choice == "A":
            return plan

        elif choice == "M":
            step_id = input("Enter step ID to modify: ").strip()
            step = next((s for s in plan.steps if s.id == step_id), None)
            if not step:
                console.print(f"[red]Step '{step_id}' not found.[/red]")
                continue
            console.print(f"\nCurrent description:\n{step.description}\n")
            new_desc = input("New description: ").strip()
            if new_desc:
                step.description = new_desc
            console.print("[green]Step updated.[/green]")

        elif choice == "R":
            return None

        else:
            console.print("[yellow]Please enter A, M, or R.[/yellow]")


def _render_plan(plan: GoalPlan) -> None:
    console.print(f"\n[bold blue]Goal Plan[/bold blue]")
    console.print(f"[dim]{plan.goal_summary}[/dim]")
    console.print(
        f"[dim]Target: {plan.target_type} = {plan.target_value} | "
        f"Horizon: {plan.horizon_months} months[/dim]\n"
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Action", width=16)
    table.add_column("Description", width=40)
    table.add_column("Target Month", width=12)
    table.add_column("Depends on", width=16)

    for step in plan.steps:
        table.add_row(
            step.id,
            step.action,
            step.description,
            str(step.target_month),
            ", ".join(step.depends_on) or "—",
        )

    console.print(table)

    if plan.risks:
        console.print("\n[yellow]Risks:[/yellow]")
        for r in plan.risks:
            console.print(f"  • {r}")

    if plan.assumptions:
        console.print("\n[cyan]Assumptions:[/cyan]")
        for a in plan.assumptions:
            console.print(f"  • {a}")
