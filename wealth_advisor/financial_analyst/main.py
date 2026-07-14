import asyncio
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from financial_analyst.observability.logger import get_logger
from financial_analyst.agent.factory import build_agent
from financial_analyst.agent.orchestrator import handle_query
from financial_analyst.memory.short_term import get_checkpointer_db_path
from financial_analyst.memory.session import get_current_session
from financial_analyst.ingestion.parse_portfolio import load_portfolio
from financial_analyst.ingestion.parse_statement import load_statement
from financial_analyst.memory import profile_store, portfolio_store, goal_store, watchlist_store
from financial_analyst.tasks import planner, approval
from financial_analyst.analysis import weekly_review
from financial_analyst.knowledge_base.indexer import build_indexes, show_index
# Load .env before anything else — all modules read env vars after this
load_dotenv()
console = Console()
logger = get_logger(__name__)

CURRENT_USER = "default_user"


async def _run_async():
  logger.info("Starting Financial Analyst")
  console.print("\n[bold blue]Financial Analyst[/bold blue] — RAG-powered financial assistant")

  async with AsyncSqliteSaver.from_conn_string(get_checkpointer_db_path()) as checkpointer:
      console.print("[dim]Building knowledge base indexes and agent...[/dim]")
      agent = await build_agent(checkpointer, CURRENT_USER)
      session_id = get_current_session()
      console.print(f"[dim]Session: {session_id}[/dim]")
      console.print("Type [bold]'/exit'[/bold] to quit\n")

      while True:
          user_input = Prompt.ask("[bold green]>[/bold green]")
          if not user_input.strip():
              continue
          if user_input.lower() in ("/exit", "/quit"):
              logger.info("Shutting down")
              console.print("[dim]Goodbye![/dim]")
              break
          elif user_input.startswith("/ask "):
              question = user_input.removeprefix("/ask ").strip()
              logger.info(f"Ask command received: {question}")
              console.print(f"[dim]Thinking...[/dim]")
              answer = await handle_query(agent, question, session_id)
              console.print(f"\n[bold]{answer}[/bold]\n")
          elif user_input.startswith("/upload_portfolio "):
              path = user_input.removeprefix("/upload_portfolio ").strip()
              try:
                  holdings = load_portfolio(path)
              except FileNotFoundError:
                  console.print(f"[red]File not found: {path}[/red]")
                  continue
              portfolio_store.save_portfolio(CURRENT_USER, holdings)
              console.print(f"[green]Saved {len(holdings)} holdings.[/green]")
          elif user_input.startswith("/upload_statement "):
              path = user_input.removeprefix("/upload_statement ").strip()
              try:
                  rows = load_statement(path)
              except FileNotFoundError:
                  console.print(f"[red]File not found: {path}[/red]")
                  continue
              portfolio_store.save_statement(CURRENT_USER, rows)
              console.print(f"[green]Saved {len(rows)} transactions.[/green]")
          elif user_input == "/profile":
              profile = profile_store.get_profile(CURRENT_USER)
              console.print(profile if profile else "[yellow]No profile set yet. Use /set_profile.[/yellow]")
          elif user_input.startswith("/set_profile "):
              fields = user_input.removeprefix("/set_profile ").strip().split()
              updates = dict(field.split("=", 1) for field in fields)
              profile = {
                  "age": int(updates["age"]) if "age" in updates else None,
                  "monthly_income": float(updates["income"]) if "income" in updates else None,
                  "risk_tolerance": updates.get("risk"),
                  "dependents": int(updates["dependents"]) if "dependents" in updates else None,
              }
              profile_store.save_profile(CURRENT_USER, profile)
              console.print("[green]Profile updated.[/green]")
          elif user_input.startswith("/set_goal "):
              description = user_input.removeprefix("/set_goal ").strip()
              console.print("[dim]Drafting plan...[/dim]")
              plan = planner.create_plan(description)
              approved_plan = approval.present_plan_for_approval(plan)
              if approved_plan:
                  goal_id = goal_store.save_goal(
                      CURRENT_USER, description, approved_plan.target_type,
                      approved_plan.target_value, approved_plan.horizon_months,
                  )
                  goal_store.save_goal_plan(goal_id, approved_plan, approved=True)
                  console.print("[green]Goal plan approved and saved.[/green]")
              else:
                  console.print("[yellow]Goal plan rejected.[/yellow]")
          elif user_input == "/dashboard":
              console.print(f"[dim]Thinking...[/dim]")
              answer = await handle_query(
                  agent, "Show me my portfolio dashboard.", session_id
              )
              console.print(f"\n[bold]{answer}[/bold]\n")
          elif user_input == "/history":
              history = goal_store.get_goal_history(CURRENT_USER)
              if not history:
                  console.print("[yellow]No goals set yet.[/yellow]")
              for g in history:
                  status = "approved" if g["plan_approved"] else "no approved plan"
                  console.print(
                      f"[bold]{g['goal_id'][:8]}...[/bold] {g['description']} "
                      f"(target: {g['target_type']}={g['target_value']}, "
                      f"{g['horizon_months']}mo) — {status}"
                  )
          elif user_input.startswith("/watch "):
              symbol = user_input.removeprefix("/watch ").strip().upper()
              watchlist_store.add_to_watchlist(CURRENT_USER, symbol, source="manual")
              console.print(f"[green]Watching {symbol}.[/green]")
          elif user_input == "/digest":
              pending = watchlist_store.get_pending_recommendations(CURRENT_USER)
              if not pending:
                  console.print("[yellow]No review pending. Run /run_weekly_review to generate one.[/yellow]")
              for rec in pending:
                  console.print(
                      f"[bold]{rec['symbol']}[/bold] — {rec['action']} "
                      f"(confidence: {rec['confidence']}, week: {rec['week_of']})\n"
                      f"  {rec['rationale']}"
                  )
                  watchlist_store.mark_reviewed(rec["id"])
          elif user_input == "/run_weekly_review":
              console.print("[dim]Running weekly review (this may take a while — live quotes + news)...[/dim]")
              review = await weekly_review.run(CURRENT_USER)
              console.print(f"[green]Weekly review complete: {len(review.recommendations)} recommendations saved.[/green]")
              console.print(f"[dim]{review.overall_rebalancing_note}[/dim]")
              console.print("[dim]Use /digest to view them.[/dim]")
          elif user_input == "/show_index":
              collection, _, _ = build_indexes()
              show_index(collection)
          else:
              logger.warning(f"Unknown command received: {user_input}")
              console.print("[yellow]Unknown command. Try:[/yellow]")
              console.print("  [bold]/ask <question>[/bold]              — ask a question")
              console.print("  [bold]/upload_portfolio <path>[/bold]      — load holdings from CSV")
              console.print("  [bold]/upload_statement <path>[/bold]      — load bank statement from CSV")
              console.print("  [bold]/profile[/bold]                      — show saved profile")
              console.print("  [bold]/set_profile age=.. income=.. risk=..[/bold] — update profile")
              console.print("  [bold]/set_goal <description>[/bold]        — plan + approve a financial goal")
              console.print("  [bold]/dashboard[/bold]                    — portfolio dashboard")
              console.print("  [bold]/history[/bold]                      — show past goals and plans")
              console.print("  [bold]/watch <symbol>[/bold]               — add a symbol to your watchlist")
              console.print("  [bold]/digest[/bold]                       — show pending weekly recommendations")
              console.print("  [bold]/run_weekly_review[/bold]            — run the weekly review now")
              console.print("  [bold]/show_index[/bold]                   — dump the knowledge base index")
              console.print("  [bold]/exit[/bold]                         — quit")


def run():
  if "--weekly-review" in sys.argv:
      # Out-of-process path: run once and exit, for external cron/launchd
      # scheduling instead of an in-process background scheduler.
      logger.info("Running one-shot weekly review (--weekly-review flag)")
      from financial_analyst.scheduler import run_weekly_review_all_users
      run_weekly_review_all_users()
      return
  asyncio.run(_run_async())


if __name__ == "__main__":
  run()
