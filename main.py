# main.py
import argparse
import os
import sys
import traceback
import time
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel  # used to detect Pydantic models
from agent.graph import agent


def call_agent(agent_obj: Any, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Try multiple invocation styles to be compatible with different agent exports.
    """
    config = config or {}

    # .invoke(...)
    if hasattr(agent_obj, "invoke") and callable(getattr(agent_obj, "invoke")):
        try:
            return agent_obj.invoke(payload, config=config)
        except TypeError:
            try:
                return agent_obj.invoke(payload, config)
            except TypeError:
                pass
        except Exception:
            raise

    # callable(agent_obj)(...)
    if callable(agent_obj):
        # try with keyword config
        try:
            return agent_obj(payload, config=config)
        except TypeError:
            pass
        except Exception:
            raise

        # try with positional config
        try:
            return agent_obj(payload, config)
        except TypeError:
            pass
        except Exception:
            raise

        # try with only payload
        try:
            return agent_obj(payload)
        except TypeError:
            pass
        except Exception:
            raise

        # try no args
        try:
            return agent_obj()
        except TypeError:
            pass
        except Exception:
            raise

    raise TypeError(
        "agent is not invokable. Expected an object with .invoke(...) or a callable. "
        "Check agent.graph export."
    )


def list_recent_files(base_dir: str, since_seconds: int = 300, max_files: int = 50) -> List[Dict[str, str]]:
    cutoff = time.time() - since_seconds
    found: List[tuple[float, str]] = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime >= cutoff:
                found.append((mtime, path))
    found.sort(reverse=True, key=lambda x: x[0])
    return [{"path": p, "mtime": time.ctime(m)} for m, p in found[:max_files]]


def build_final_state_from_side_effects(base_dir: str, minutes: int = 5) -> Dict[str, Any]:
    recent = list_recent_files(base_dir, since_seconds=minutes * 60)
    return {
        "status": "done",
        "returned_value": None,
        "recent_files_count": len(recent),
        "recent_files": recent,
        "message": f"Agent returned None — likely performed side-effects (files written/logs). "
                   f"Showing files modified in the last {minutes} minute(s)."
    }


def to_serializable(obj: Any) -> Any:
    """
    Recursively convert objects into JSON-serializable forms.
    - Pydantic BaseModel -> dict via .model_dump()
    - dict/list/tuple -> recursively convert contents
    - other -> returned as-is (json.dumps may still fail on unknown types)
    """
    # Pydantic models
    if isinstance(obj, BaseModel):
        return to_serializable(obj.model_dump())

    # dictionaries
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}

    # lists / tuples
    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]

    # primitive types or already serializable
    return obj


def main():
    parser = argparse.ArgumentParser(description="Run engineering project planner")
    parser.add_argument("--prompt", "-p", type=str, default=None, help="Project prompt (or set PROJECT_PROMPT env var)")
    parser.add_argument("--recursion-limit", "-r", type=int, default=100, help="Recursion limit")
    parser.add_argument("--list-since-minutes", type=int, default=5, help="Show files modified in the last N minutes")
    args = parser.parse_args()

    prompt = args.prompt or os.getenv("PROJECT_PROMPT")
    if not prompt:
        try:
            prompt = input("Enter your project prompt: ").strip() or None
        except (EOFError, KeyboardInterrupt):
            prompt = None

    if not prompt:
        print('No prompt supplied. Use --prompt "your prompt" or set PROJECT_PROMPT env var.')
        sys.exit(2)

    payload = {"user_prompt": prompt}
    config = {"recursion_limit": args.recursion_limit}

    try:
        result = call_agent(agent, payload, config=config)

        # If agent returned None, craft a useful final_state summarising side-effects
        if result is None:
            base_dir = os.getcwd()
            final_state = build_final_state_from_side_effects(base_dir, minutes=args.list_since_minutes)
        else:
            final_state = {"status": "done", "returned_value": result}

        # Convert final_state into JSON-serializable structure before printing
        final_state_serializable = to_serializable(final_state)

        print("\n=== FINAL STATE ===")
        print(json.dumps(final_state_serializable, indent=2, ensure_ascii=False))

    except Exception:
        print("\nAgent call failed — traceback below:\n", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
